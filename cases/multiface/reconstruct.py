"""Calibrated, CPU-only multiview head reconstruction. No pretrained models."""
import argparse
import json
import os
from pathlib import Path
import time
from collections import deque
import numpy as np

ROOT = Path(__file__).resolve().parent

def cameras(path):
    cs = json.load(open(path))['cameras']
    for c in cs:
        c['K'] = np.array(c['K'], dtype=np.float64)
        c['K'][0] *= 668/1334
        c['K'][1] *= .5
        c['R'] = np.array(c['world_to_camera'])[:,:3]
        c['t'] = np.array(c['world_to_camera'])[:,3]
        c['C'] = -c['R'].T @ c['t']
    return cs

def project(p,c):
    q = p @ c['R'].T + c['t']
    uv = q @ c['K'].T
    return uv[...,:2]/uv[...,2:3]

def sample(im, uv):
    h,w = im.shape[:2]
    u = np.clip(uv[...,0],0,w-1.001)
    v = np.clip(uv[...,1],0,h-1.001)
    x=u.astype(np.int32); y=v.astype(np.int32)
    a=u-x; b=v-y
    if im.ndim==3: a=a[...,None]; b=b[...,None]
    return (im[y,x]*(1-a)+im[y,x+1]*a)*(1-b)+(im[y+1,x]*(1-a)+im[y+1,x+1]*a)*b

def mask_image(im):
    from PIL import Image, ImageFilter
    a=np.asarray(im).astype(np.float32)
    m=(a.mean(2)>19).astype(np.uint8)*255
    m=np.array(Image.fromarray(m).filter(ImageFilter.MaxFilter(5)).filter(ImageFilter.MinFilter(5)))>0
    h,w=m.shape
    # Preserve the head-connected foreground, excluding isolated capture lights.
    seen=np.zeros_like(m); q=deque([(w//2,100)]); seen[100,w//2]=1
    while q:
        x,y=q.popleft()
        for xx,yy in ((x-1,y),(x+1,y),(x,y-1),(x,y+1)):
            if 0<=xx<w and 0<=yy<h and m[yy,xx] and not seen[yy,xx]:
                seen[yy,xx]=1; q.append((xx,yy))
    # Fill enclosed dark facial features with a background flood fill.
    bg=np.zeros_like(m);q=deque()
    for x in range(w):
        for y in (0,h-1):
            if not seen[y,x]:bg[y,x]=1;q.append((x,y))
    for y in range(h):
        for x in (0,w-1):
            if not seen[y,x] and not bg[y,x]:bg[y,x]=1;q.append((x,y))
    while q:
        x,y=q.popleft()
        for xx,yy in ((x-1,y),(x+1,y),(x,y-1),(x,y+1)):
            if 0<=xx<w and 0<=yy<h and not seen[yy,xx] and not bg[yy,xx]:
                bg[yy,xx]=1;q.append((xx,yy))
    return ~bg

def triangulate(uvs,cs):
    aa=[];bb=[]
    for uv,c in zip(uvs,cs):
        ray=np.linalg.inv(c['K'])@[*uv,1]
        ray=c['R'].T@ray; ray/=np.linalg.norm(ray)
        a=np.eye(3)-ray[:,None]*ray[None,:]
        aa.append(a);bb.append(a@c['C'])
    return np.linalg.lstsq(np.concatenate(aa),np.concatenate(bb),rcond=None)[0]

def hull(cs, masks, step=2.3):
    # World units and axes are kept identical to the supplied calibration.
    xs=np.arange(-135,136,step,dtype=np.float32)
    ys=np.arange(-175,190,step,dtype=np.float32)
    zs=np.arange(910,1190,step,dtype=np.float32)
    occ=np.ones((len(xs),len(ys),len(zs)),bool)
    yy,zz=np.meshgrid(ys,zs,indexing='ij')
    for i,x in enumerate(xs):
        p=np.stack([np.full_like(yy,x),yy,zz],-1)
        valid=((x/133)**2+((zz-1050)/160)**2<1)
        for c,m in zip(cs,masks):
            uv=project(p,c)
            # Beyond the sensor edge the object is unobserved, not empty.
            inside=(uv[...,0]>=0)&(uv[...,0]<668)&(uv[...,1]>=0)&(uv[...,1]<1024)
            u=np.clip(uv[...,0].astype(int),0,667); v=np.clip(uv[...,1].astype(int),0,1023)
            valid &= m[v,u]
        occ[i]=valid
    occ[[0,-1],:,:]=False;occ[:,[0,-1],:]=False;occ[:,:,[0,-1]]=False
    # Surface nets: one vertex per boundary cell, joined around grid edges.
    corners=[occ[a:len(xs)-1+a,b:len(ys)-1+b,c:len(zs)-1+c] for a,b,c in ((0,0,0),(1,0,0),(0,1,0),(1,1,0),(0,0,1),(1,0,1),(0,1,1),(1,1,1))]
    count=sum(c.astype(np.uint8) for c in corners)
    boundary=(count>0)&(count<8)
    inds=np.argwhere(boundary)
    ids=np.full(boundary.shape,-1,np.int32);ids[tuple(inds.T)]=np.arange(len(inds))
    verts=np.zeros((len(inds),3),np.float32); weights=np.zeros(len(inds),np.float32)
    cc=np.array([(0,0,0),(1,0,0),(0,1,0),(1,1,0),(0,0,1),(1,0,1),(0,1,1),(1,1,1)])
    for a,b in [(0,1),(2,3),(4,5),(6,7),(0,2),(1,3),(4,6),(5,7),(0,4),(1,5),(2,6),(3,7)]:
        cross=corners[a][tuple(inds.T)] != corners[b][tuple(inds.T)]
        verts[cross] += inds[cross]+(cc[a]+cc[b])/2
        weights[cross]+=1
    verts/=weights[:,None]
    verts=verts*step+np.array([xs[0],ys[0],zs[0]])
    faces=[]
    for axis in range(3):
        sl0=[slice(None)]*3;sl1=[slice(None)]*3
        sl0[axis]=slice(None,-1);sl1[axis]=slice(1,None)
        edges=np.argwhere(occ[tuple(sl0)]!=occ[tuple(sl1)])
        other=[i for i in range(3) if i!=axis]
        for e in edges:
            cells=[]
            for a,b in [(0,0),(-1,0),(-1,-1),(0,-1)]:
                v=e.copy();v[other[0]]+=a;v[other[1]]+=b
                if np.any(v<0) or np.any(v>=ids.shape):break
                cells.append(ids[tuple(v)])
            if len(cells)==4 and min(cells)>=0:
                p=verts[cells]
                n=np.cross(p[1]-p[0],p[2]-p[0])
                outward=1 if occ[tuple(e)] else -1
                if n[axis]*outward<0:cells=cells[::-1]
                faces.append(cells)
    faces=np.array(faces,np.int32)
    return verts,faces

def edges_from_faces(f):
    return np.unique(np.sort(np.concatenate([f[:,[0,1]],f[:,[1,2]],f[:,[2,3]],f[:,[3,0]]]),axis=1),axis=0)

def smooth(v,edges,iterations=10,amount=.4):
    n=len(v);a,b=edges.T
    counts=np.bincount(edges.ravel(),minlength=n)
    for _ in range(iterations):
        avg=np.zeros_like(v)
        np.add.at(avg,a,v[b]);np.add.at(avg,b,v[a])
        v=v*(1-amount)+avg/np.maximum(counts[:,None],1)*amount
    return v

def normals(v,f):
    n=np.zeros_like(v)
    fn=np.cross(v[f[:,1]]-v[f[:,0]],v[f[:,2]]-v[f[:,0]])
    for k in range(4):np.add.at(n,f[:,k],fn)
    return n/np.maximum(np.linalg.norm(n,axis=1,keepdims=True),1e-8)

def visibility(v,n,cs):
    weights=[]
    for c in cs:
        d=c['C']-v;d/=np.linalg.norm(d,axis=1,keepdims=True)
        w=np.maximum((n*d).sum(1),0)
        uv=project(v,c)
        w*=((uv[:,0]>2)&(uv[:,0]<666)&(uv[:,1]>2)&(uv[:,1]<1022))
        weights.append(w)
    return np.array(weights).T

def photo_refine(v,f,cs,images,edges):
    # Tangent-plane normalized patch matching between the calibrated cameras.
    # Broad baselines require a geometry-aware patch warp, not pixel blocks.
    gray=[np.asarray(im).astype(np.float32).mean(2)/255 for im in images]
    for iteration,(radius,maxdepth,delta) in enumerate([(3.4,18,2),(2.2,7,1),(1.3,3,.5)]):
        n=normals(v,f);vis=visibility(v,n,cs)
        tangent=np.cross(n,np.array([0,1,0]));tangent/=np.maximum(np.linalg.norm(tangent,axis=1,keepdims=True),1e-8)
        bitangent=np.cross(n,tangent)
        shifts=np.array([(a,b) for a in [-1,-.5,0,.5,1] for b in [-1,-.5,0,.5,1]])*radius
        patch=tangent[:,None,:]*shifts[None,:,0:1]+bitangent[:,None,:]*shifts[None,:,1:2]
        best=np.full(len(v),1e10); disp=np.zeros(len(v));quality=np.zeros(len(v))
        for depth in np.arange(-maxdepth,maxdepth+.01,delta):
            pp=v[:,None,:]+patch+n[:,None,:]*depth
            samples=[]
            for c,im in zip(cs,gray):
                s=sample(im,project(pp,c));s-=s.mean(1,keepdims=True)
                s/=np.sqrt((s*s).mean(1,keepdims=True)+.00003)
                samples.append(s)
            cost=np.zeros(len(v));wt=np.zeros(len(v))
            for a,b in [(0,1),(1,2),(0,2)]:
                w=(vis[:,a]*vis[:,b])**2
                w*=((vis[:,a]>.18)&(vis[:,b]>.18))
                err=((samples[a]-samples[b])**2).mean(1)
                cost+=w*err;wt+=w
            cost/=np.maximum(wt,1e-8)
            cost+=.035*(depth/maxdepth)**2
            good=(wt>.006)&(cost<best)
            best[good]=cost[good];disp[good]=depth;quality[good]=wt[good]
        dd=np.repeat(disp[:,None],3,axis=1)
        dd=smooth(dd,edges,5,.65)[:,0]
        # Background/back-of-head and unseen strips retain silhouette geometry.
        dd*=np.clip(quality/.025,0,1)
        v+=n*dd[:,None]*.85
        v=smooth(v,edges,2,.15)
        print('photo level',iteration,'median error',float(np.median(best[best<1e5])),flush=True)
    return v

def main():
    from PIL import Image
    ap=argparse.ArgumentParser();ap.add_argument('--source',default='../candidate');ap.add_argument('--work',default='../scratch');ap.add_argument('--stage',default='base');args=ap.parse_args()
    src=Path(args.source).resolve();work=Path(args.work).resolve();work.mkdir(exist_ok=True)
    cs=cameras(src/'cameras.json')[:3]
    ims=[Image.open(src/'views'/c['view_id']/'frames'/c['frames'][0]['file']).convert('RGB').resize((668,1024),Image.Resampling.LANCZOS) for c in cs]
    if args.stage=='base':
        for c,im in zip(cs,ims):
            m=mask_image(im);Image.fromarray(m.astype(np.uint8)*255).save(work/(c['view_id']+'_mask.png'))
        masks=[np.array(Image.open(work/(c['view_id']+'_mask.png')))>0 for c in cs]
        print('nose estimate',triangulate([(80,442),(370,400),(651,435)],cs),flush=True)
        v,f=hull(cs,masks)
        print('hull',v.shape,f.shape,'bounds',v.min(0),v.max(0),flush=True)
        e=edges_from_faces(f);v=smooth(v,e,18,.45)
        np.savez_compressed(work/'hull.npz',verts=v,faces=f)
        v=photo_refine(v,f,cs,ims,e)
        np.savez_compressed(work/'base.npz',verts=v.astype(np.float32),faces=f)
        print('base completed',flush=True)

if __name__=='__main__':main()
