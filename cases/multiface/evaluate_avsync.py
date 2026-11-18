"""SyncNet v2, short-clip preprocessing, reference and time-shift controls."""
import argparse
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[2]
OUT=Path(__file__).resolve().parent
TMP=Path('D:/OmniALE-metrics/multiface-avsync-v1')
STANDARD_TMP=Path('D:/OmniALE-metrics/multiface-standard-metrics-v1')
RUN=ROOT/'outputs/multiface-agent-pilot-v1/runs/sol-xhigh-02'
FF=ROOT/'work/media-runtime/shotcut/Shotcut/ffmpeg.exe'
sys.path.insert(0,str(TMP/'python-libs'))
sys.path.insert(0,str(TMP/'official'))
W,H,N=668,1024,104


def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        while b:=f.read(1024*1024):h.update(b)
    return h.hexdigest()


def dump(p,d):p.write_text(json.dumps(d,indent=2,ensure_ascii=False,allow_nan=False)+'\n',encoding='utf8')


def audio(path):
    import numpy as np
    r=subprocess.run([str(FF),'-v','error','-i',str(path),'-vn','-ac','1','-ar','16000','-f','s16le','-'],capture_output=True,check=True)
    return np.frombuffer(r.stdout,dtype='<i2').copy()


def prepare():
    import cv2
    import numpy as np
    import torch
    from scipy import signal
    from detectors import s3fd
    torch.set_num_threads(4)
    s3fd.PATH_WEIGHT=str(TMP/'mirrored-weights/sfd_face.pth')
    detector=s3fd.S3FD(device='cpu')
    standard=json.loads((ROOT/'outputs/multiface-standard-metrics-v1/protocol.json').read_text(encoding='utf8'))
    sources=json.loads((OUT/'official_sources.json').read_text(encoding='utf8'))
    protocol={'label':'post_hoc_SyncNet_v2_short_clip_CPU','source_run':'sol-xhigh-02',
              'implementation_commit':sources['commit'],'script_sha256':sha(Path(__file__)),
              'weights':json.loads((OUT/'weights_provenance.json').read_text(encoding='utf8')),
              'input_fps':30,'syncnet_fps':25,'sample_rate':16000,'search_range_frames':15,'offset_resolution_ms':40,
              'time_resampling':'FFmpeg fps=25 from original 30fps timeline; not metadata-only speed change',
              'face_detection':'official S3FD, RGB input, conf_th=0.9, scales=[0.25], largest face; fill missing boxes by linear interpolation only inside detections',
              'short_track_adaptation':'No default >100-frame track filter; single actor one continuous clip; require >=50 contiguous frames and >=80% detected frames, report all failures',
              'crop':'official run_pipeline.py crop_scale=.40, 13-frame median-smoothed face bbox center/size, padding110, cv2.INTER_LINEAR resize224x224; no mirroring or face frontalization',
              'inference':'official S model and pretrained syncnet_v2.model; BGR values 0..255; 5 consecutive video frames and 20 MFCC hops; default python_speech_features MFCC at16kHz; official lastframe=min_length-5',
              'scores':'official calc_pdist(vshift=15); LSE-D=min mean distance; LSE-C=median mean distance-LSE-D; offset_frames=15-argmin; zero-lag distance is extra diagnostic',
              'controls':'original audio shifted -400,-200,+200,+400ms with zero padding/truncation; reference visual features unchanged; static-mouth and reversed-audio controls; no submitted video adjusted',
              'offset_sign':'SyncNet original convention; report positive as audio earlier than matching visual in controlled checks; validate sign with artificial delays',
              'eligibility':'shift checks pass if predicted offset changes match -audio_delay_ms within one25fps frame for all4 controls; no universal LSE-C threshold imposed',
              'limitations':['Only3.466s and oblique views; match confidence and controls required.',
                             'Standard LSE-D uses best offset and is not sufficient without offset.',
                             'Cannot convert these raw results into a calibrated 0..100 score.'],
              'clips':{}}
    montage=[]
    for name in ['T1','T2']:
        for kind in ['reference','submitted']:
            label=name+'_'+kind;started=time.monotonic()
            if kind=='reference':
                a=np.load(STANDARD_TMP/(name+'_reference.npy'),mmap_mode='r')
                assert sha(STANDARD_TMP/(name+'_reference.npy'))==standard['views'][name]['reference_array_sha256']
                apath=ROOT/'outputs/multiface-agent-pilot-v1/candidate/speech.wav'
            else:
                a=np.memmap(STANDARD_TMP/(name+'_submitted.rgb'),dtype='uint8',mode='r',shape=(N,H,W,3))
                apath=RUN/'sealed_submission'/(name+'.mp4')
                assert sha(apath)==standard['views'][name]['submitted_sha256']
            raw=TMP/(label+'_25fps.rgb')
            with raw.open('wb') as stream:
                subprocess.run([str(FF),'-v','error','-f','rawvideo','-pixel_format','rgb24','-video_size',f'{W}x{H}',
                                '-framerate','30','-i','-','-vf','fps=25','-f','rawvideo','-pix_fmt','rgb24','-'],input=a.tobytes(),stdout=stream,check=True)
            count=raw.stat().st_size//(W*H*3)
            frames=np.memmap(raw,dtype='uint8',mode='r',shape=(count,H,W,3))
            boxes=np.full((count,4),np.nan);conf=np.zeros(count)
            for i,im in enumerate(frames):
                dets=detector.detect_faces(np.array(im),conf_th=.9,scales=[.25])
                if len(dets):
                    det=max(dets,key=lambda b:(b[2]-b[0])*(b[3]-b[1]))
                    boxes[i]=det[:4];conf[i]=det[4]
                if i%20==0:print('DETECTION',label,i+1,'/',count,flush=True)
            valid=np.isfinite(boxes).all(axis=1);ids=np.flatnonzero(valid)
            row={'resampled_video_frames':count,'detected_frames':int(valid.sum()),'detection_coverage':float(valid.mean()),
                 'mean_detection_confidence':float(conf[valid].mean()) if valid.any() else None}
            if len(ids)<50 or valid.mean()<.8:
                row.update(usable=False,reason='face_track_coverage_insufficient');protocol['clips'][label]=row
                dump(OUT/'preprocessing_progress.json',protocol);continue
            first,last=int(ids[0]),int(ids[-1]);indices=np.arange(first,last+1)
            interp=np.stack([np.interp(indices,ids,boxes[ids,j]) for j in range(4)],axis=1)
            size=np.maximum(interp[:,3]-interp[:,1],interp[:,2]-interp[:,0])/2
            sy=signal.medfilt((interp[:,1]+interp[:,3])/2,kernel_size=13)
            sx=signal.medfilt((interp[:,0]+interp[:,2])/2,kernel_size=13)
            bs=signal.medfilt(size,kernel_size=13)
            crops=np.empty((len(indices),224,224,3),dtype='uint8')
            for j,i in enumerate(indices):
                b=float(bs[j]);pad=int(b*1.8)
                im=cv2.cvtColor(np.array(frames[i]),cv2.COLOR_RGB2BGR)
                padded=np.pad(im,((pad,pad),(pad,pad),(0,0)),constant_values=110)
                my=sy[j]+pad;mx=sx[j]+pad
                crop=padded[int(my-b):int(my+b*1.8),int(mx-b*1.4):int(mx+b*1.4)]
                crops[j]=cv2.resize(crop,(224,224))
            wav=audio(apath);start=int(first/25*16000);end=min(len(wav),int((last+1)/25*16000));wav=wav[start:end]
            np.save(TMP/(label+'_crops.npy'),crops);np.save(TMP/(label+'_audio.npy'),wav)
            np.savez(TMP/(label+'_detections.npz'),boxes=boxes,confidence=conf,smoothed_size=bs,smoothed_x=sx,smoothed_y=sy)
            row.update(usable=True,track_first_frame=first,track_last_frame=last,track_frames=len(indices),audio_samples=len(wav),
                       crop_array_sha256=sha(TMP/(label+'_crops.npy')),audio_array_sha256=sha(TMP/(label+'_audio.npy')),
                       submitted_mp4_sha256=sha(apath) if kind=='submitted' else None)
            protocol['clips'][label]=row
            from PIL import Image,ImageDraw
            sheet=Image.new('RGB',(224*5,254),'white');draw=ImageDraw.Draw(sheet)
            draw.text((8,8),label,fill='black')
            for j,idx in enumerate(np.linspace(0,len(crops)-1,5).round().astype(int)):
                sheet.paste(Image.fromarray(cv2.cvtColor(crops[idx],cv2.COLOR_BGR2RGB)),(j*224,30))
            montage.append(sheet)
            print('TRACK_DONE',label,row,'seconds',round(time.monotonic()-started,1),flush=True)
            dump(OUT/'preprocessing_progress.json',protocol)
    if montage:
        from PIL import Image
        image=Image.new('RGB',(1120,254*len(montage)),'white')
        for i,s in enumerate(montage):image.paste(s,(0,i*254))
        image.save(OUT/'crop_checks.jpg',quality=90)
    dump(OUT/'protocol.json',protocol);print('PREPROCESSING_COMPLETE',flush=True)


def evaluate():
    import numpy as np
    import torch
    import python_speech_features
    from SyncNetModel import S
    from SyncNetInstance import calc_pdist
    torch.set_num_threads(4)
    p=json.loads((OUT/'protocol.json').read_text(encoding='utf8'))
    assert p['script_sha256']==sha(Path(__file__))
    model=S().eval();model.load_state_dict(torch.load(TMP/'mirrored-weights/syncnet_v2.model',map_location='cpu',weights_only=True),strict=True)
    def aud_feats(wav,n):
        m=python_speech_features.mfcc(wav,16000).T.astype('float32')
        c=torch.from_numpy(m).unsqueeze(0).unsqueeze(0)
        features=[]
        for i in range(0,n,8):
            batch=torch.cat([c[:,:,:,j*4:j*4+20] for j in range(i,min(n,i+8))],0)
            features.append(model.forward_aud(batch))
        return torch.cat(features,0)
    def vis_feats(crops,n,freeze=False):
        features=[]
        for i in range(0,n,8):
            batch=[]
            for j in range(i,min(n,i+8)):
                a=np.repeat(crops[:1],5,axis=0) if freeze else crops[j:j+5]
                batch.append(torch.from_numpy(np.ascontiguousarray(a.transpose(3,0,1,2))).unsqueeze(0).float())
            features.append(model.forward_lip(torch.cat(batch,0)))
        return torch.cat(features,0)
    def scores(v,a):
        distances=calc_pdist(v,a,vshift=15);curve=torch.mean(torch.stack(distances,1),1)
        val,idx=curve.min(0);offset=15-int(idx)
        return {'offset_frames':offset,'offset_ms':offset*40,'LSE_D':float(val),'LSE_C':float(curve.median()-val),
                'zero_lag_distance':float(curve[15]),'offset_on_search_boundary':abs(offset)==15,
                'feature_windows':len(v),'curve':[{'offset_ms':(15-j)*40,'distance':float(d)} for j,d in enumerate(curve)]}
    result={'implementation_commit':p['implementation_commit'],'protocol_sha256':sha(OUT/'protocol.json'),
            'versions':{x:importlib.metadata.version(x) for x in ['torch','numpy','opencv-python-headless','python-speech-features']},
            'clips':{},'controls':{},'interpretation':{}}
    with torch.inference_mode():
        for label,row in p['clips'].items():
            if not row['usable']:
                result['clips'][label]={'status':'not_evaluable','reason':row['reason']};continue
            crops=np.load(TMP/(label+'_crops.npy'));wav=np.load(TMP/(label+'_audio.npy'))
            assert sha(TMP/(label+'_crops.npy'))==row['crop_array_sha256']
            assert sha(TMP/(label+'_audio.npy'))==row['audio_array_sha256']
            n=min(len(crops),len(wav)//640)-5
            started=time.monotonic();vf=vis_feats(crops,n);af=aud_feats(wav,n)
            r=scores(vf,af);r.update(status='measured',detection_coverage=row['detection_coverage'])
            result['clips'][label]=r
            np.savez(TMP/(label+'_features.npz'),visual=vf.numpy(),audio=af.numpy())
            print('MEASURED',label,{k:v for k,v in r.items() if k!='curve'},'seconds',round(time.monotonic()-started,1),flush=True)
            if label.endswith('reference'):
                ctrls=[]
                for ms in [-400,-200,200,400]:
                    samples=abs(ms)*16;shifted=np.zeros_like(wav)
                    if ms>0:shifted[samples:]=wav[:-samples]
                    else:shifted[:-samples]=wav[samples:]
                    a=aud_feats(shifted,n);c=scores(vf,a)
                    measured_delta=c['offset_ms']-r['offset_ms'];expected=-ms
                    c.update(audio_delay_ms=ms,expected_offset_change_ms=expected,measured_offset_change_ms=measured_delta,
                             offset_change_error_ms=abs(measured_delta-expected),passed=abs(measured_delta-expected)<=40)
                    ctrls.append(c)
                    print('SHIFT_CONTROL',label,ms,{k:v for k,v in c.items() if k!='curve'},flush=True)
                static=scores(vis_feats(crops,n,True),af)
                reverse=scores(vf,aud_feats(wav[::-1].copy(),n))
                result['controls'][label]={'shift_controls':ctrls,'all_shift_controls_passed':all(x['passed'] for x in ctrls),
                                          'frozen_visual':static,'reversed_audio':reverse}
            dump(OUT/'partial_result.json',result)
        for name in ['T1','T2']:
            ref=result['clips'].get(name+'_reference',{});pred=result['clips'].get(name+'_submitted',{})
            control=result['controls'].get(name+'_reference',{})
            if ref.get('status')!='measured' or pred.get('status')!='measured':
                result['interpretation'][name]={'status':'not_evaluable'};continue
            credible=control.get('all_shift_controls_passed',False) and not ref['offset_on_search_boundary']
            result['interpretation'][name]={'reference_shift_controls_passed':credible,
                'offset_difference_from_reference_ms':pred['offset_ms']-ref['offset_ms'],
                'LSE_D_difference_from_reference':pred['LSE_D']-ref['LSE_D'],
                'LSE_C_difference_from_reference':pred['LSE_C']-ref['LSE_C'],
                'status':'reference_calibrated_raw_measurement' if credible else 'raw_measurement_unreliable_for_pass_fail',
                'no_calibrated_pass_threshold':True}
    seal=json.loads((RUN/'submission_seal.json').read_text(encoding='utf8'))['files']
    result['submitted_videos_unchanged']=all(sha(RUN/'sealed_submission'/(n+'.mp4'))==seal[n+'.mp4'] for n in ['T1','T2'])
    dump(OUT/'result.json',result);print('EVALUATION_COMPLETE',flush=True)


if __name__=='__main__':
    sys.stdout.reconfigure(encoding='utf8')
    a=argparse.ArgumentParser();a.add_argument('--prepare',action='store_true');args=a.parse_args()
    if args.prepare:prepare()
    else:evaluate()
