"""Blind, candidate-only SFX localization from the sealed final mix.

No project, solver output, former review, or score is read. Residuals are analysis
signals only: judge media always retain the original final mix.
"""
from __future__ import annotations
import argparse, hashlib, json, math, subprocess, sys
from pathlib import Path

import numpy as np
from scipy import signal, ndimage
from scipy.io import wavfile

OUT = None
FFMPEG = 'ffmpeg'
FFPROBE = 'ffprobe'
SR = 12000
METHOD = {
    'version': 'sfx-candidate-localizer-v3.0',
    'input_boundary': 'sealed_submission/showcase.mp4; agent-input/audio/*.wav; private/audio-events.json source SFX duration/effective interval/onset/peak/anchor and BGM duration only',
    'analysis_rate_hz': SR,
    'music_alignment': {'query_seconds': 2.5, 'query_hop_seconds': 1.0,
        'query_peak_ncc_floor': .45, 'query_peaks_max': 4, 'query_peak_separation_seconds': .20,
        'offset_cluster_tolerance_seconds': .035, 'minimum_query_support': 2,
        'selection': 'highest positive global overlap NCC squared times overlap fraction; retain all supported offset aliases',
        'gain': 'per-channel-independent mono LS; local 0.8s LS, 0.6s median, 0.15s Gaussian smoothing, clipped 0..4*global positive gain'},
    'sfx_retrieval': {'views': ['original_mix', 'bgm_residual'],
        'template': 'annotated source effective interval; unchanged rate and positive waveform correlation',
        'ncc_floor': .16, 'peak_separation_seconds': .20,
        'same_source_dedup_seconds': .30, 'max_candidates_per_source': 8,
        'fallback': 'if no retrieved peak, retain best two nonadjacent peaks as below-threshold hypotheses',
        'ranking': 'residual NCC * sqrt(max(incremental mix variance explained,0)) + 0.05*raw NCC',
        'high_confidence': 'residual NCC>=0.50 and incremental mix variance explained>=0.010',
        'medium_confidence': 'residual NCC>=0.25 and incremental mix variance explained>=0.002',
        'meaning': 'confidence describes waveform identity evidence only, never semantic fit, audibility or confirmed use count'},
    'review_media': {'padding_seconds': 1.0, 'frame_rate': 24,
        'frame_start': 'floor((effective onset-1s)*24), clamped at zero',
        'frame_end': 'ceil((effective end+1s)*24), clamped at final video frame count',
        'merge_gap_seconds': .20, 'video_size_max': [960, 540],
        'video_codec': 'libx264 CRF21; original mix AAC192k; no audio gain, remix or residual',
        'exact_audio_sidecar': 'FLAC derived from decoded original stereo PCM48k, exact sample trim'},
    'controls': 'pure BGM and a separate synthetic mixture of the 3 supplied SFX inserted at fixed arbitrary times; same retrieval and gain subtraction; controls are not engineering truth',
    'interpretation': 'All results are search hypotheses. Missed or capped matches are uncertainty, not absence. Full final video remains fallback judge input.'
}

def dump(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False)+'\n', encoding='utf-8')

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def run(args):
    p = subprocess.run([str(x) for x in args], capture_output=True, text=True, encoding='utf-8', errors='replace')
    if p.returncode:
        raise RuntimeError(p.stderr[-5000:])
    return p.stdout

def freeze():
    OUT.mkdir(parents=True, exist_ok=True)
    m = OUT / 'METHOD.frozen.json'
    if m.exists():
        if json.loads(m.read_text(encoding='utf-8')) != METHOD:
            raise RuntimeError('Frozen method differs; create a new version instead of tuning this run.')
    else:
        dump(m, METHOD)
    (OUT/'METHOD.sha256').write_text(sha(m)+'  METHOD.frozen.json\n', encoding='utf-8')
    return sha(m)

def audio(path):
    rate, x = wavfile.read(path)
    if np.issubdtype(x.dtype, np.integer):
        x = x.astype(np.float64) / max(abs(np.iinfo(x.dtype).min), np.iinfo(x.dtype).max)
    else:
        x = x.astype(np.float64)
    if x.ndim == 2:
        x = x.mean(axis=1)
    gcd = math.gcd(int(rate), SR)
    if rate != SR:
        x = signal.resample_poly(x, SR//gcd, int(rate)//gcd)
    return x

def ncc(x, q):
    q = q - q.mean()
    if len(q) > len(x):
        return np.empty(0)
    corr = signal.correlate(x, q, mode='valid', method='fft')
    cs = np.r_[0., np.cumsum(x)]
    cs2 = np.r_[0., np.cumsum(x*x)]
    n = len(q)
    v = np.maximum(cs2[n:]-cs2[:-n]-(cs[n:]-cs[:-n])**2/n, 0)
    d = np.sqrt(v * np.dot(q, q))
    return np.clip(np.divide(corr, d, out=np.zeros_like(corr), where=d>1e-10), -1, 1)

def peaks(curve, floor=.16, max_count=None, separation=.20):
    ix, _ = signal.find_peaks(curve, height=floor, distance=round(separation*SR))
    if len(curve):
        ends = [i for i in (0, len(curve)-1) if curve[i]>=floor and (len(curve)==1 or curve[i]>=curve[1 if i==0 else -2])]
        ix = np.unique(np.r_[ix, ends]).astype(int)
    ix = sorted(ix, key=lambda i: float(curve[i]), reverse=True)
    return ix if max_count is None else ix[:max_count]

def model_at_offset(music, length, offset):
    z = np.zeros(length, dtype=np.float64)
    shift = int(round(offset*SR))
    lo, hi = max(0, shift), min(length, shift+len(music))
    if hi>lo:
        z[lo:hi] = music[lo-shift:hi-shift]
    return z, lo, hi

def align_music(x, music):
    width = round(2.5*SR)
    matches = []
    for s in np.arange(0, len(music)/SR-2.5+1e-8, 1.):
        q = music[round(s*SR):round(s*SR)+width]
        curve = ncc(x, q)
        for i in peaks(curve, .45, 4, .20):
            matches.append({'source_start_seconds': float(s), 'video_start_seconds': i/SR,
                'offset_seconds': i/SR-float(s), 'ncc': float(curve[i])})
    clusters = []
    for item in sorted(matches, key=lambda r:r['offset_seconds']):
        if clusters and abs(item['offset_seconds']-np.median([r['offset_seconds'] for r in clusters[-1]]))<=.035:
            clusters[-1].append(item)
        else:
            clusters.append([item])
    hypotheses = []
    for group in clusters:
        support = len(set(r['source_start_seconds'] for r in group))
        if support<2:
            continue
        offset = float(np.median([r['offset_seconds'] for r in group]))
        model, lo, hi = model_at_offset(music, len(x), offset)
        a, b = x[lo:hi], model[lo:hi]
        den = np.linalg.norm(a)*np.linalg.norm(b)
        c = float(np.dot(a, b)/den) if den else 0.
        gain = max(0., float(np.dot(a,b)/(np.dot(b,b)+1e-20)))
        hypotheses.append({'offset_seconds': offset, 'source_time_equals_video_time_minus_offset': True,
            'query_support': support, 'median_query_ncc': float(np.median([r['ncc'] for r in group])),
            'global_overlap_ncc': c, 'overlap_seconds': (hi-lo)/SR,
            'global_positive_gain': gain, 'selection_score': max(c,0)**2*(hi-lo)/len(x),
            'supporting_queries': group})
    hypotheses.sort(key=lambda r:r['selection_score'], reverse=True)
    if not hypotheses:
        raise RuntimeError('No supported BGM alignment; do not silently subtract an assumed BGM offset.')
    best = hypotheses[0]
    model, lo, hi = model_at_offset(music, len(x), best['offset_seconds'])
    return best, hypotheses, matches, model

def subtract_music(x, model):
    den = np.dot(model,model)
    scalar = max(0., float(np.dot(x,model)/(den+1e-20)))
    width = round(.8*SR)
    numerator = ndimage.uniform_filter1d(x*model, width, mode='nearest')
    denominator = ndimage.uniform_filter1d(model*model, width, mode='nearest')
    gain = np.divide(numerator, denominator, out=np.zeros_like(x), where=denominator>1e-10)
    gain = np.clip(gain, 0, max(4*scalar, .001))
    # scipy median_filter on 7201 samples is needlessly costly; sample the slow gain at 100Hz.
    stride = SR//100
    small = signal.medfilt(gain[::stride], 61)
    small = ndimage.gaussian_filter1d(small, 15, mode='nearest')
    gain = np.interp(np.arange(len(x)), np.arange(len(small))*stride, small)
    residual = x - gain*model
    return residual, gain, scalar

def candidate_metrics(x, residual, q, i, raw_curve, res_curve):
    a, r = x[i:i+len(q)], residual[i:i+len(q)]
    q = q-q.mean()
    gain = max(0., float(np.dot(r,q)/(np.dot(q,q)+1e-20)))
    mix_energy, res_energy = float(np.dot(a,a)), float(np.dot(r,r))
    improvement = max(0., res_energy-float(np.dot(r-gain*q,r-gain*q)))
    contribution = improvement/(mix_energy+1e-20)
    rn, on = float(res_curve[i]), float(raw_curve[i])
    confidence = 'high' if rn>=.50 and contribution>=.010 else 'medium' if rn>=.25 and contribution>=.002 else 'low'
    return {'original_mix_ncc': on, 'bgm_residual_ncc': rn,
        'positive_template_gain_in_residual': gain,
        'incremental_mix_variance_explained': contribution,
        'residual_energy_fraction_of_mix': res_energy/(mix_energy+1e-20),
        'residual_variance_explained': improvement/(res_energy+1e-20),
        'waveform_confidence': confidence,
        'ranking_score': max(rn,0)*math.sqrt(contribution)+.05*max(on,0)}

def detect(x, residual, templates, annotations):
    all_candidates, summaries = [], {}
    for name, template in templates.items():
        ann = annotations[name]
        lo, hi = ann['effective_interval_seconds']
        q = template[round(lo*SR):round(hi*SR)]
        curves = {'original_mix': ncc(x,q), 'bgm_residual': ncc(residual,q)}
        origins = {}
        for view, curve in curves.items():
            for i in peaks(curve, .16):
                origins.setdefault(i, []).append(view)
        below = False
        if not origins:
            below = True
            for view, curve in curves.items():
                for i in peaks(curve, -1., 2, .30):
                    origins.setdefault(i, []).append(view)
        rows = []
        for i, views in origins.items():
            if i/SR-lo < -.05:
                continue
            metrics = candidate_metrics(x,residual,q,i,curves['original_mix'],curves['bgm_residual'])
            start = i/SR-lo
            rows.append({'possible_type': name.removesuffix('.wav'), 'source_asset': name,
                'hypothesis_only': True, 'retrieval_views': views, 'below_threshold_fallback': below,
                'template_source_interval_seconds': [lo,hi], 'estimated_asset_start_seconds': start,
                'effective_interval_seconds': [i/SR,start+hi],
                'onset_seconds': start+ann['onset_seconds'],
                'energy_peak_seconds': start+ann['peak_seconds'],
                'alignment_anchor_seconds': start+ann['alignment_anchor_seconds'],
                'asset_duration_seconds': ann['duration_seconds'], 'metrics': metrics})
        rows.sort(key=lambda r:r['metrics']['ranking_score'],reverse=True)
        selected=[]
        suppressed=0
        for row in rows:
            if any(abs(row['estimated_asset_start_seconds']-z['estimated_asset_start_seconds'])<.30 for z in selected):
                suppressed+=1
                continue
            selected.append(row)
        available=len(selected)
        selected=selected[:8]
        summaries[name]={'raw_retrieved_peaks':len(origins),'same_source_near_duplicates_suppressed':suppressed,
            'candidates_before_cap':available,'candidates_emitted':len(selected),'capped':available>8,
            'max_original_mix_ncc':float(np.max(curves['original_mix'])),
            'max_residual_ncc':float(np.max(curves['bgm_residual'])),
            'absence_conclusion_allowed':False}
        all_candidates+=selected
    all_candidates.sort(key=lambda r:(r['effective_interval_seconds'][0],r['possible_type']))
    for i,c in enumerate(all_candidates,1):
        c['candidate_id']=f'candidate-{i:02d}'
        c['hypothesized_type']=c['possible_type']
        c['file_start']=c['estimated_asset_start_seconds']
        c['anchor']=c['alignment_anchor_seconds']
        c['confidence']=c['metrics']['waveform_confidence']
        c['correlation']={'original_mix':c['metrics']['original_mix_ncc'],'bgm_residual':c['metrics']['bgm_residual_ncc']}
        c['cautions']=['Waveform search hypothesis; not a confirmed use or audible semantic match.']
        if c['metrics']['waveform_confidence']=='low':
            c['cautions'].append('Weak or music-confounded support; inspect original mix and full video.')
        if c['possible_type']=='hit':
            c['cautions'].append('Percussive BGM can create false hit matches; residual contribution is supporting evidence only.')
    return all_candidates,summaries

def make_windows(candidates, duration, frame_count):
    windows=[]
    for c in candidates:
        a,b=c['effective_interval_seconds']
        fa=max(0,math.floor((a-1)*24))
        fb=min(frame_count,math.ceil((b+1)*24))
        if windows and fa/24<=windows[-1]['end_frame_exclusive']/24+.20:
            windows[-1]['end_frame_exclusive']=max(windows[-1]['end_frame_exclusive'],fb)
            windows[-1]['candidate_ids'].append(c['candidate_id'])
        else:
            windows.append({'start_frame_inclusive':fa,'end_frame_exclusive':fb,'candidate_ids':[c['candidate_id']]})
    for i,w in enumerate(windows,1):
        w.update({'window_id':f'window-{i:02d}','source_start_seconds':w['start_frame_inclusive']/24,
            'source_end_seconds':w['end_frame_exclusive']/24,
            'mapping':'source_seconds = source_start_seconds + clip_seconds; source_frame = start_frame_inclusive + clip_frame',
            'audio':'original final mix; no gain changes; residual not included'})
        w['candidate_hypotheses']=[]
        for c in candidates:
            if c['candidate_id'] in w['candidate_ids']:
                c['window_id']=w['window_id']
                c['clip_effective_interval_seconds']=[v-w['source_start_seconds'] for v in c['effective_interval_seconds']]
                c['clip_onset_seconds']=c['onset_seconds']-w['source_start_seconds']
                c['clip_energy_peak_seconds']=c['energy_peak_seconds']-w['source_start_seconds']
                c['clip_alignment_anchor_seconds']=c['alignment_anchor_seconds']-w['source_start_seconds']
                w['candidate_hypotheses'].append({k:c[k] for k in ['candidate_id','possible_type','hypothesis_only','clip_effective_interval_seconds','clip_onset_seconds','clip_energy_peak_seconds','clip_alignment_anchor_seconds']})
    return windows

def controls(music,templates,annotations):
    base=music[:15*SR]*.35
    residual,gain,scalar=subtract_music(base,base/.35)
    pure,ps=detect(base,residual,templates,annotations)
    mix=base.copy()
    known=[]
    for name,start in zip(['whoosh.wav','hit.wav','drop.wav'],[2.13,6.37,10.61]):
        q=templates[name]
        i=round(start*SR)
        mix[i:i+len(q)]+=.22*q
        known.append({'source':name,'inserted_asset_start_seconds':start,'gain':.22})
    res,g,s=subtract_music(mix,base/.35)
    found,fs=detect(mix,res,templates,annotations)
    recover=[]
    for k in known:
        same=[c for c in found if c['source_asset']==k['source']]
        best=min(same,key=lambda c:abs(c['estimated_asset_start_seconds']-k['inserted_asset_start_seconds'])) if same else None
        recover.append({**k,'nearest_candidate_start_seconds':None if best is None else best['estimated_asset_start_seconds'],
            'absolute_error_seconds':None if best is None else abs(best['estimated_asset_start_seconds']-k['inserted_asset_start_seconds']),
            'metrics':None if best is None else best['metrics']})
    return {'scope':'controlled arbitrary audio-only insertions, unrelated to final project positions',
        'insert_recovery':recover,'pure_bgm_candidates':pure,'pure_bgm_summary':ps,
        'pure_bgm_high_or_medium_candidates':sum(c['metrics']['waveform_confidence']!='low' for c in pure),
        'note':'Low confidence raw-BGM retrievals are reported as false candidate controls; thresholds not retuned after controls.'}

def validate_media(windows,pcm):
    checks=[]
    for w in windows:
        p=json.loads(run([FFPROBE,'-v','error','-show_streams','-of','json',OUT/w['video_path']]))
        v=next(s for s in p['streams'] if s['codec_type']=='video')
        af=f"atrim=start_sample={w['audio_start_sample_48k']}:end_sample={w['audio_end_sample_exclusive_48k']}"
        original_hash=run([FFMPEG,'-v','error','-i',pcm,'-af',af,'-c:a','pcm_s24le','-f','hash','-hash','sha256','-']).strip()
        flac_hash=run([FFMPEG,'-v','error','-i',OUT/w['lossless_audio_path'],'-c:a','pcm_s24le','-f','hash','-hash','sha256','-']).strip()
        n=w['end_frame_exclusive']-w['start_frame_inclusive']
        check={'window_id':w['window_id'],'expected_frames':n,'encoded_frames':int(v['nb_frames']),
            'frame_rate':v['r_frame_rate'],'expected_duration_seconds':n/24,'encoded_duration_seconds':float(v['duration']),
            'original_trim_pcm_sha256':original_hash,'flac_decoded_pcm_sha256':flac_hash,
            'lossless_audio_sample_identity':original_hash==flac_hash,
            'frame_count_identity':int(v['nb_frames'])==n}
        if not check['lossless_audio_sample_identity'] or not check['frame_count_identity']:
            raise RuntimeError(f"Media validation failed: {check}")
        checks.append(check)
    return {'all_checks_pass':True,'checks':checks,
        'note':'FLAC decoded PCM24 is SHA256-identical to the exact sample slice of the original final mix. MP4 audio is AAC192k encoding of that same slice.'}

def main():
    global OUT, FFMPEG, FFPROBE
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--video',type=Path,help='Submitted video with its original final mix; frozen v3 mapping requires 24 fps.')
    ap.add_argument('--bgm',type=Path,help='Original industrial_pulse.wav source.')
    ap.add_argument('--sfx-dir',type=Path,help='Directory containing whoosh.wav, hit.wav and drop.wav.')
    ap.add_argument('--annotations',type=Path,default=Path(__file__).resolve().parents[1]/'config/sfx-source-annotations.json',help='Source-template annotations only, not placement truth.')
    ap.add_argument('--ffmpeg',default='ffmpeg')
    ap.add_argument('--ffprobe',default='ffprobe')
    ap.add_argument('--output',type=Path,required=True)
    ap.add_argument('--freeze-only',action='store_true')
    ap.add_argument('--skip-media',action='store_true')
    args=ap.parse_args()
    OUT=args.output.resolve()
    FFMPEG=args.ffmpeg
    FFPROBE=args.ffprobe
    if not args.freeze_only and any(v is None for v in (args.video,args.bgm,args.sfx_dir)):
        ap.error('--video, --bgm and --sfx-dir are required unless --freeze-only is used')
    method_sha=freeze()
    if args.freeze_only:
        print(json.dumps({'method_sha256':method_sha,'output':str(OUT)},ensure_ascii=False))
        return
    video=args.video.resolve()
    assets=args.sfx_dir.resolve()
    annotation_path=args.annotations
    # Narrow projection: never use music beat positions, sections or project strip truth.
    annotation=json.loads(annotation_path.read_text(encoding='utf-8'))
    annotations=annotation
    required={'whoosh.wav','hit.wav','drop.wav'}
    if set(annotations)!=required:
        raise ValueError('Annotations must describe exactly the three source SFX; no placement truth is accepted.')
    dump(OUT/'source-sfx-annotations.used.json',annotations)
    probe=json.loads(run([FFPROBE,'-v','error','-show_streams','-show_format','-of','json',video]))
    v=next(s for s in probe['streams'] if s['codec_type']=='video')
    duration=float(v.get('duration',probe['format']['duration']))
    fps_num,fps_den=map(int,v['avg_frame_rate'].split('/'))
    if fps_num/fps_den!=24:
        raise RuntimeError('Exact source-frame grid mapping requires 24 fps source; inspect before proceeding.')
    frame_count=int(v.get('nb_frames',round(duration*24)))
    pcm=OUT/'finalmix-original-stereo-48k.wav'
    run([FFMPEG,'-y','-v','error','-i',video,'-map','0:a:0','-ar','48000','-c:a','pcm_s24le',pcm])
    x=audio(pcm)
    music=audio(args.bgm)
    templates={n:audio(assets/n) for n in annotations}
    best,aliases,matches,model=align_music(x,music)
    residual,gain,scalar=subtract_music(x,model)
    alignment={'method_sha256':method_sha,'offset_definition':'video_time = music_source_time + offset_seconds',
        'primary_offset':best,'retained_offset_aliases':aliases,'all_query_peak_matches':matches,
        'gain_summary':{'global_gain':scalar,'local_gain_percentiles':np.percentile(gain,[0,5,50,95,100]).tolist()},
        'residual_rms_ratio':float(np.linalg.norm(residual)/(np.linalg.norm(x)+1e-20)),
        'warning':'Residual is a search aid, not an audible-quality judgment track.'}
    dump(OUT/'bgm-alignment.json',alignment)
    np.savez_compressed(OUT/'analysis-arrays.npz',sample_rate=SR,mix_mono=x,bgm_model=model,bgm_gain=gain,residual_mono=residual)
    candidates,summaries=detect(x,residual,templates,annotations)
    windows=make_windows(candidates,duration,frame_count)
    media=OUT/'judge-media'
    media.mkdir(exist_ok=True)
    for w in windows:
        w['video_path']='judge-media/'+w['window_id']+'.mp4'
        w['lossless_audio_path']='judge-media/'+w['window_id']+'.flac'
        w['audio_flac_path']=w['lossless_audio_path']
        w['source_start_s']=w['source_start_seconds']
        w['source_end_s']=w['source_end_seconds']
        w['duration_seconds']=w['source_end_seconds']-w['source_start_seconds']
        w['audio_start_sample_48k']=w['start_frame_inclusive']*2000
        w['audio_end_sample_exclusive_48k']=w['end_frame_exclusive']*2000
        if not args.skip_media:
            vf=f"trim=start_frame={w['start_frame_inclusive']}:end_frame={w['end_frame_exclusive']},setpts=PTS-STARTPTS,scale=960:540:force_original_aspect_ratio=decrease:force_divisible_by=2"
            af=f"atrim=start_sample={w['audio_start_sample_48k']}:end_sample={w['audio_end_sample_exclusive_48k']},asetpts=PTS-STARTPTS"
            run([FFMPEG,'-y','-v','error','-i',video,'-i',pcm,'-filter_complex',f'[0:v:0]{vf}[v];[1:a:0]{af}[a]',
                '-map','[v]','-map','[a]','-c:v','libx264','-preset','fast','-crf','21','-r','24','-c:a','aac','-b:a','192k','-movflags','+faststart',OUT/w['video_path']])
            run([FFMPEG,'-y','-v','error','-i',pcm,'-af',af,'-c:a','flac',OUT/w['lossless_audio_path']])
    if not args.skip_media:
        dump(OUT/'media-validation.json',validate_media(windows,pcm))
    control=controls(music,templates,annotations)
    dump(OUT/'controls.json',control)
    by_conf={k:sum(c['metrics']['waveform_confidence']==k for c in candidates) for k in ['high','medium','low']}
    supported=[]
    for c in candidates:
        if c['metrics']['waveform_confidence']=='low':
            continue
        a,b=c['effective_interval_seconds']
        supported.append([max(0.,a),min(duration,b)])
    merged=[]
    for a,b in sorted(supported):
        if merged and a<=merged[-1][1]:
            merged[-1][1]=max(merged[-1][1],b)
        else:
            merged.append([a,b])
    uncertain=[]
    cursor=0.
    for a,b in merged:
        if a>cursor:
            uncertain.append([cursor,a])
        cursor=max(cursor,b)
    if cursor<duration:
        uncertain.append([cursor,duration])
    result={'schema_version':3,'method_sha256':method_sha,'script_sha256':sha(__file__),
        'sealed_video':video.name,'sealed_video_sha256':sha(video),'source_duration_seconds':duration,
        'input_hashes':{'industrial_pulse.wav':sha(args.bgm),**{n:sha(assets/n) for n in templates}},
        'warning':'Candidate hypotheses only: not standard answers, confirmed use counts, semantic verdicts or audibility verdicts.',
        'candidate_count':len(candidates),'confidence_counts':by_conf,'source_summaries':summaries,'candidates':candidates,
        'unmatched_or_uncertain':{'entire_video_remains_eligible_for_review':True,'full_video_path':video.name,
            'intervals_without_medium_or_high_waveform_support_seconds':uncertain,
            'interval_note':'These are unlocalized or weak-evidence spans, not evidence that effects are absent. All other spans also require original-mix semantic review.',
            'reason':'Search covers unmodified source waveforms only, candidate caps may omit weak peaks, processing or overlapping music can mask SFX; absence conclusions forbidden.'}}
    dump(OUT/'candidates.json',result)
    dump(OUT/'judge-windows.json',{'schema_version':3,'method_sha256':method_sha,
        'warning':result['warning'],'full_video_fallback':video.name,'windows':windows})
    lines=['# SFX candidate localization v3','',result['warning'],'',
        f'- Frozen method SHA256: `{method_sha}`',
        f'- Source: sealed `showcase.mp4`, {duration:.6f}s, 24fps, {frame_count} frames.',
        f"- Data-selected primary BGM offset: {best['offset_seconds']:.6f}s (video = music source + offset); global NCC {best['global_overlap_ncc']:.5f}; {best['query_support']} supported queries. All {len(aliases)} supported aliases retained in bgm-alignment.json.",
        f'- {len(candidates)} emitted hypotheses: {by_conf}; {len(windows)} merged original-mix review windows.',
        '- Mono 12kHz residual is only a localization aid. Judge MP4s and FLACs contain the original stereo mix, without gain changes or subtraction.',
        '- Each clip starts on an original 24fps frame boundary. Exact mapping and 48kHz audio sample trims are recorded in judge-windows.json.',
        '', '| Candidate | Possible source | Effective interval (source sec) | Anchor | Mix NCC | Residual NCC | Mix variance explained | Evidence confidence |',
        '|---|---|---:|---:|---:|---:|---:|---|']
    for c in candidates:
        m=c['metrics']; a,b=c['effective_interval_seconds']
        lines.append(f"| {c['candidate_id']} | {c['possible_type']} | {a:.4f}–{b:.4f} | {c['alignment_anchor_seconds']:.4f} | {m['original_mix_ncc']:.3f} | {m['bgm_residual_ncc']:.3f} | {m['incremental_mix_variance_explained']:.4f} | {m['waveform_confidence']} |")
    lines+=['','## Control validation','',f"Pure BGM returned {len(control['pure_bgm_candidates'])} deliberately retained search hypotheses, with {control['pure_bgm_high_or_medium_candidates']} medium/high-confidence candidates. These are false-candidate controls, not target truth."]
    for c in control['insert_recovery']:
        lines.append(f"- Synthetic {c['source']} at {c['inserted_asset_start_seconds']:.3f}s: nearest recovery error {c['absolute_error_seconds']}s.")
    lines+=['','## Limits','',
        'No engineer strip positions, solver logs, former review, scores or video-production code were read. Source annotations were projected to SFX source duration/effective interval/onset/peak/anchor only. BGM source beats and sections are not used.',
        'Fixed thresholds prioritize useful search windows; they are not calibrated probabilities. Repeated BGM phrases yield alignment aliases. Local gain fitting can remove correlated portions of an effect; unchanged-rate waveform matching can miss retimed, pitch-shifted, reversed, heavily filtered or very quiet sources. Mono analysis may lose stereo-only cues. Percussive BGM can resemble hit.wav. Caps and deduplication can merge or omit closely spaced real repeats.',
        'Onset/energy peak/anchor are propagated source-template annotations, conditional on the candidate identity and alignment being correct. They are not independently observed acoustic event boundaries. Only the judge may determine semantic fit and audibility from original-mix media. No use counts or absence penalties follow from these hypotheses.',
        '', 'Full original final video remains the fallback for every unmatched or uncertain interval.']
    (OUT/'REPORT.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps({'output':str(OUT),'candidate_count':len(candidates),'confidence_counts':by_conf,'window_count':len(windows),
        'primary_bgm_offset_seconds':best['offset_seconds'],'method_sha256':method_sha},ensure_ascii=False))

if __name__=='__main__':
    main()
