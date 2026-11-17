"""Post-hoc standard image/video metrics; never edits solver files or old scores."""
import argparse
import csv
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
DATA = ROOT/'outputs/multiface-reconstruction-data-v1'
RUN = ROOT/'outputs/multiface-agent-pilot-v1/runs/sol-xhigh-02'
SUB = RUN/'sealed_submission'
FF = ROOT/'work/plnba-runtime/shotcut/Shotcut/ffmpeg.exe'
W,H,N = 668,1024,104
SCRATCH = Path('D:/OmniALE-metrics/multiface-standard-metrics-v1')
SCRATCH.mkdir(parents=True,exist_ok=True)
WEIGHTS = SCRATCH/'model-cache'
os.environ['TORCH_HOME'] = str(WEIGHTS)


def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        while b:=f.read(1024*1024): h.update(b)
    return h.hexdigest()


def dump(path, obj):
    path.write_text(json.dumps(obj,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf8')


def prepare():
    import numpy as np
    from PIL import Image,ImageDraw
    cameras=json.loads((DATA/'public/cameras.json').read_text(encoding='utf8'))['cameras']
    protocol={
        'label':'post_hoc_standard_metrics_v1_not_a_reproduction_of_any_paper',
        'source_run':'sol-xhigh-02','model':'gpt-6.1-sol','effort':'xhigh',
        'resolution':[W,H],'frames_per_view':N,'fps':30,
        'temporary_array_directory':str(SCRATCH),'model_cache_directory':str(WEIGHTS),
        'time_alignment':'sorted original PNG index i paired with submitted decoded frame i; no offset search, registration, crop, stabilization or color fitting',
        'reference_resize':'original lossless RGB PNG, Pillow BICUBIC to 668x1024; no aspect-preserving letterboxing',
        'primary_region':'entire RGB frame including original background',
        'primary_PSNR':'skimage.metrics.peak_signal_noise_ratio(data_range=255), arithmetic mean of frame dB values',
        'primary_SSIM':'skimage.metrics.structural_similarity, RGB channel_axis=2, Gaussian weights sigma=1.5, use_sample_covariance=False, data_range=255',
        'primary_LPIPS':'official lpips 0.1.4, AlexNet, v0.1 learned weights, spatial=False, normalize=True for [0,1] inputs',
        'supplementary_region':'union of rasterized projected reference mesh triangles, not convex hull; 5px erosion for local SSIM; not semantic matting, not a co-visibility mask',
        'supplementary_LPIPS':'same AlexNet v0.1 spatial map, black outside fixed GT surface mask, mask-weighted map average; not directly comparable with primary LPIPS',
        'JOD':'official pyfvvdp 1.2.2, CPU, display standard_fhd, non-foveated, FHWC uint8 input, 30fps, replicate temporal padding, full frame, no heatmap',
        'aggregation':'per-view frame means; equal arithmetic mean of the two views; JOD computed on whole 104-frame sequence per view',
        'sanity_checks':'identical image PSNR infinite, SSIM 1, LPIPS 0; identical 8-frame video JOD 10; black image control for image metrics',
        'no_combined_score':True,
        'limitations':['Post-hoc evaluation of an existing sealed submission; not a preregistered benchmark.',
                      'Different dataset, resolution, mask, cameras and hardware from published papers; no direct leaderboard comparison.',
                      'These metrics do not certify 3D geometry, semantic lip sync, or new speech generation.'],
        'sources':{'lpips':'https://github.com/richzhang/PerceptualSimilarity',
                   'jod':'https://github.com/gfxdisp/FovVideoVDP',
                   'ssim':'https://scikit-image.org/docs/0.25.x/api/skimage.metrics.html#skimage.metrics.structural_similarity',
                   'related_protocol':'https://github.com/tobias-kirschstein/nersemble#32-evaluation'},
        'script_sha256':sha(Path(__file__)),'views':{}
    }
    seal=json.loads((RUN/'submission_seal.json').read_text(encoding='utf8'))['files']
    for name in ['T1','T2']:
        folder=DATA/'private/held_out'/name/'frames'
        frames=sorted(folder.glob('*.png'));assert len(frames)==N
        camera=next(c for c in cameras if c['view_id']==name)
        e=np.array(camera['world_to_camera']);k=np.array(camera['K'])
        refs=np.lib.format.open_memmap(SCRATCH/(name+'_reference.npy'),mode='w+',dtype='uint8',shape=(N,H,W,3))
        masks=np.lib.format.open_memmap(SCRATCH/(name+'_surface_mask.npy'),mode='w+',dtype='uint8',shape=(N,H,W))
        ref_hashes={};mesh_hashes={}
        for i,f in enumerate(frames):
            refs[i]=np.asarray(Image.open(f).convert('RGB').resize((W,H),Image.Resampling.BICUBIC))
            mesh=DATA/'private/geometry'/(f.stem+'.obj')
            verts=[];faces=[]
            for line in mesh.read_text().splitlines():
                if line.startswith('v '):verts.append([float(x) for x in line.split()[1:4]])
                elif line.startswith('f '):faces.append([int(x.split('/')[0])-1 for x in line.split()[1:]])
            xyz=np.array(verts)@e[:,:3].T+e[:,3]
            uv=xyz@k.T;uv=uv[:,:2]/uv[:,2:3]*np.array([W/camera['width'],H/camera['height']])
            mask=Image.new('L',(W,H));draw=ImageDraw.Draw(mask)
            for face in faces:
                if (xyz[face,2]>0).all(): draw.polygon([tuple(x) for x in uv[face]],fill=1)
            masks[i]=np.asarray(mask)
            ref_hashes[f.name]=sha(f);mesh_hashes[mesh.name]=sha(mesh)
        refs.flush();masks.flush()
        video=SUB/(name+'.mp4');digest=sha(video)
        assert digest==seal[name+'.mp4']
        raw=SCRATCH/(name+'_submitted.rgb')
        with raw.open('wb') as stream:
            subprocess.run([str(FF),'-v','error','-i',str(video),'-an','-fps_mode','passthrough','-f','rawvideo','-pix_fmt','rgb24','-'],stdout=stream,check=True)
        assert raw.stat().st_size==N*H*W*3
        protocol['views'][name]={'submitted_sha256':digest,'reference_png_sha256':ref_hashes,'reference_mesh_sha256':mesh_hashes,
                                 'reference_array_sha256':sha(SCRATCH/(name+'_reference.npy')),
                                 'surface_mask_sha256':sha(SCRATCH/(name+'_surface_mask.npy')),
                                 'surface_coverage':float(masks.mean())}
        print('PREPARED',name,'mask coverage',float(masks.mean()),flush=True)
    dump(OUT/'protocol.json',protocol)
    print('PROTOCOL_FROZEN',sha(OUT/'protocol.json'),flush=True)


def evaluate():
    import numpy as np
    import torch
    import lpips
    import pyfvvdp
    from scipy.ndimage import binary_erosion
    from skimage.metrics import peak_signal_noise_ratio,structural_similarity
    torch.set_num_threads(4)
    protocol=json.loads((OUT/'protocol.json').read_text(encoding='utf8'))
    assert protocol['script_sha256']==sha(Path(__file__)),'Evaluator changed after protocol was written'
    model=lpips.LPIPS(net='alex',version='0.1',spatial=False,verbose=False).eval()
    video_metric=pyfvvdp.fvvdp(display_name='standard_fhd',heatmap=None,device=torch.device('cpu'),temp_padding='replicate')
    def tensor(im):
        return torch.from_numpy(np.ascontiguousarray(im.transpose(2,0,1))).unsqueeze(0).float()/255
    def ssim(a,b,full=False):
        return structural_similarity(a,b,data_range=255,channel_axis=2,gaussian_weights=True,sigma=1.5,use_sample_covariance=False,full=full)
    result={'protocol_sha256':sha(OUT/'protocol.json'),'protocol_label':protocol['label'],
            'versions':{x:importlib.metadata.version(x) for x in ['torch','torchvision','numpy','Pillow','scipy','scikit-image','lpips','pyfvvdp']},
            'views':{},'no_combined_score':True,'jod_display_description':str(video_metric.get_info_string())}
    ref0=np.load(SCRATCH/'T1_reference.npy',mmap_mode='r');a=np.array(ref0[0]);t=tensor(a)
    with torch.inference_mode():
        same_lpips=float(model(t,t,normalize=True).item())
        black_lpips=float(model(torch.zeros_like(t),t,normalize=True).item())
        identity_jod,_=video_metric.predict(np.array(ref0[:8]),np.array(ref0[:8]),dim_order='FHWC',frames_per_second=30)
    identity_ssim=float(ssim(a,a));same_jod=float(identity_jod.item())
    assert abs(identity_ssim-1)<1e-8 and abs(same_lpips)<1e-6 and abs(same_jod-10)<1e-4
    result['sanity_checks']={'identical_PSNR_dB':'infinity','identical_SSIM':identity_ssim,'identical_LPIPS':same_lpips,
                             'identical_8_frame_JOD':same_jod,'black_PSNR_dB':float(peak_signal_noise_ratio(a,np.zeros_like(a),data_range=255)),
                             'black_SSIM':float(ssim(a,np.zeros_like(a))),'black_LPIPS':black_lpips}
    dump(OUT/'sanity_checks.json',result['sanity_checks'])
    print('SANITY_CHECKS',result['sanity_checks'],flush=True)
    for name in ['T1','T2']:
        assert sha(SUB/(name+'.mp4'))==protocol['views'][name]['submitted_sha256']
        references=np.load(SCRATCH/(name+'_reference.npy'),mmap_mode='r')
        masks=np.load(SCRATCH/(name+'_surface_mask.npy'),mmap_mode='r')
        videos=np.memmap(SCRATCH/(name+'_submitted.rgb'),mode='r',dtype='uint8',shape=(N,H,W,3))
        rows=[];started=time.monotonic()
        with torch.inference_mode():
            for i in range(N):
                a=np.asarray(videos[i]);b=np.asarray(references[i]);mask=np.asarray(masks[i],dtype=bool)
                psnr=float(peak_signal_noise_ratio(b,a,data_range=255));ssim_score,ssim_map=ssim(b,a,True)
                mse=float(np.mean((a.astype(np.float64)-b)[mask]**2))
                inner=binary_erosion(mask,iterations=5)
                aa=tensor(a);bb=tensor(b)
                model.spatial=False
                lp=float(model(aa,bb,normalize=True).item())
                tm=torch.from_numpy(mask.copy()).unsqueeze(0).unsqueeze(0).float()
                model.spatial=True
                lpmap=model(aa*tm,bb*tm,normalize=True)
                mlp=float((lpmap*tm).sum().item()/tm.sum().item())
                row={'view':name,'frame_zero_based':i,'time_s':i/30,'PSNR_dB':psnr,'SSIM':float(ssim_score),'LPIPS_alex':lp,
                     'surface_PSNR_dB':float(10*np.log10(255**2/mse)),
                     'surface_SSIM_map_mean':float(ssim_map.mean(axis=2)[inner].mean()),'surface_LPIPS_alex_map_mean':mlp}
                rows.append(row)
                if i%10==0 or i==N-1:
                    print('IMAGE_METRICS',name,i+1,'/',N,'elapsed',round(time.monotonic()-started,1),flush=True)
                    dump(OUT/'progress.json',{'phase':'image_metrics','view':name,'completed_frames':i+1,'total_frames':N})
        with (OUT/(name+'_per_frame.csv')).open('w',encoding='utf8',newline='') as f:
            writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
        summary={key:float(np.mean([r[key] for r in rows])) for key in rows[0] if key not in ['view','frame_zero_based','time_s']}
        result['views'][name]=summary
        dump(OUT/'partial_result.json',result)
        print('JOD_STARTED',name,flush=True);dump(OUT/'progress.json',{'phase':'JOD','view':name,'frames':N})
        with torch.inference_mode():
            quality,_=video_metric.predict(videos,references,dim_order='FHWC',frames_per_second=30)
        summary['JOD']=float(quality.item())
        print('VIEW_DONE',name,json.dumps(summary),flush=True);dump(OUT/'partial_result.json',result)
    result['mean']={key:float(np.mean([result['views'][name][key] for name in ['T1','T2']])) for key in result['views']['T1']}
    result['submitted_videos_unchanged']=all(sha(SUB/(name+'.mp4'))==protocol['views'][name]['submitted_sha256'] for name in ['T1','T2'])
    result['model_weights_sha256']={str(p.relative_to(WEIGHTS)):sha(p) for p in WEIGHTS.rglob('*') if p.is_file()}
    dump(OUT/'result.json',result)
    dump(OUT/'progress.json',{'phase':'completed'})
    print('ALL_DONE',json.dumps(result['mean']),flush=True)


if __name__=='__main__':
    sys.stdout.reconfigure(encoding='utf8')
    parser=argparse.ArgumentParser();parser.add_argument('--prepare',action='store_true');args=parser.parse_args()
    if args.prepare:prepare()
    else:evaluate()
