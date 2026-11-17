"""Finish reconstruction boundaries and clean isolated capture-light spill."""
from pathlib import Path
import numpy as np
from PIL import Image,ImageFilter
from reconstruct import cameras,project
from animate import weights_for

ROOT=Path(__file__).resolve().parent

def main():
    assets=ROOT/'assets';d=np.load(assets/'reconstruction.npz')
    v=d['verts'];f=d['faces'];ani=d['animation'];cs=cameras(assets/'cameras.json')[:3]
    uv=project(v,cs[1]);mouth=np.exp(-(((uv[:,0]-367)/115)**2+((uv[:,1]-580)/125)**2)/2)
    delta=ani-v[None]
    print('motion quantiles',np.quantile(np.linalg.norm(delta,axis=2),[.5,.9,.99,1]),flush=True)
    # Conservative spatial bounds prevent aperture-ambiguous background patches
    # from driving the scalp and nape. Observed speech can move the jaw further.
    limit=2.5+mouth*7
    length=np.linalg.norm(delta,axis=2)
    delta*=np.minimum(1,limit[None]/np.maximum(length,1e-5))[:,:,None]
    ani=v[None]+delta
    weights=weights_for(v,f,cs)
    edges=np.sort(np.concatenate([f[:,[0,1]],f[:,[1,2]],f[:,[2,0]]]),axis=1)
    # Find original front/rear join edges at the sensor's upper/lower boundary.
    n=len(v)//2;front=f[(f<n).all(1)]
    ee=np.sort(np.concatenate([front[:,[0,1]],front[:,[1,2]],front[:,[2,0]]]),axis=1)
    ed,counts=np.unique(ee,axis=0,return_counts=True);edge=ed[counts==1]
    groups=[]
    for top in [True,False]:
        uvv=uv[edge]
        select=(uvv[:,:,1].max(1)<8) if top else (uvv[:,:,1].min(1)>1014)
        e=edge[select]
        if len(e)==0:continue
        ids=np.unique(e);both=np.r_[ids,ids+n]
        nv=v[both].copy();nv[:,1]+=(-55 if top else 95)
        nv[:,2]+=(30 if top else 8)
        if not top:nv[:,0]*=1.35
        na=ani[:,both].copy()+(nv-v[both])[None]
        remap={int(old):len(v)+j for j,old in enumerate(both)}
        newfaces=[]
        for a,b in e:
            for off in [0,n]:
                aa=int(a+off);bb=int(b+off);newfaces.extend([(aa,bb,remap[bb]),(aa,remap[bb],remap[aa])])
        f=np.concatenate([f,np.array(newfaces,np.int32)])
        v=np.concatenate([v,nv]);ani=np.concatenate([ani,na],1);weights=np.concatenate([weights,weights[both]])
    np.savez_compressed(assets/'reconstruction.npz',verts=v,faces=f,weights=weights.astype(np.float32),animation=ani.astype(np.float32))
    # White studio lamps touching the source silhouette are not skin radiance.
    for cam in ['I1','I2','I3']:
        for file in sorted((assets/cam).glob('*.png')):
            im=Image.open(file).convert('RGB');a=np.asarray(im).astype(np.float32)
            hot=(a.min(2)>150)
            # Preserve small ocular catchlights; clean only the edge-connected LEDs.
            yy,xx=np.mgrid[:1024,:668]
            hot &= ((yy>600)|(xx<200)|(xx>565))
            if not hot.any():continue
            hole=np.asarray(Image.fromarray(hot.astype(np.uint8)*255).filter(ImageFilter.MaxFilter(9)))>0
            good=(~hole).astype(np.float32)
            denom=np.asarray(Image.fromarray(good,mode='F').filter(ImageFilter.BoxBlur(18))) if False else None
            # Pillow's Gaussian RGB blur on masked numerator and confidence.
            mask=Image.fromarray((good*255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(22))
            den=np.maximum(np.asarray(mask).astype(np.float32)/255,.001)
            num=np.asarray(Image.fromarray((a*good[:,:,None]).astype(np.uint8)).filter(ImageFilter.GaussianBlur(22))).astype(np.float32)
            fill=num/den[:,:,None]
            a[hole]=fill[hole]
            Image.fromarray(np.clip(a,0,255).astype(np.uint8)).save(file,compress_level=2)
    print('final assets',v.shape,f.shape,flush=True)

if __name__=='__main__':main()
