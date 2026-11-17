"""Estimate surface motion from image-space observations and save portable assets."""
import argparse
import json
import shutil
import time
from pathlib import Path
import numpy as np
from PIL import Image, ImageFilter
from reconstruct import cameras,project,sample,visibility,smooth,edges_from_faces

ROOT=Path(__file__).resolve().parent

def box(a,r):
    p=np.pad(a,((r,r),(r,r)),mode='edge')
    s=np.pad(p,((1,0),(1,0))).cumsum(0).cumsum(1)
    k=2*r+1
    return (s[k:,k:]-s[:-k,k:]-s[k:,:-k]+s[:-k,:-k])/(k*k)

def pyramid(a):
    im=Image.fromarray(a.astype(np.float32),mode='F')
    return [np.asarray(im.resize((w,h),Image.Resampling.BILINEAR)) for w,h in [(84,128),(167,256),(334,512)]]

def resize_flow(flow,shape):
    h,w=shape;oldh,oldw=flow.shape[:2]
    return np.stack([np.asarray(Image.fromarray(flow[:,:,0],mode='F').resize((w,h),Image.Resampling.BILINEAR))*w/oldw,np.asarray(Image.fromarray(flow[:,:,1],mode='F').resize((w,h),Image.Resampling.BILINEAR))*h/oldh],-1)

def flow_pair(refs,targets,initial=None):
    flow=None
    for level,(ref,cur) in enumerate(zip(refs,targets)):
        h,w=ref.shape;yy,xx=np.mgrid[:h,:w];xy=np.stack([xx,yy],-1)
        if flow is None:
            flow=np.zeros((h,w,2),np.float32) if initial is None else resize_flow(initial,ref.shape)
        else:flow=resize_flow(flow,ref.shape)
        gy,gx=np.gradient(ref)
        radius=4 if level==2 else 3
        aa=box(gx*gx,radius)+.000015;bb=box(gx*gy,radius);cc=box(gy*gy,radius)+.000015
        det=np.maximum(aa*cc-bb*bb,1e-12)
        for iteration in range(7):
            warped=sample(cur,xy+flow);err=ref-warped
            dx=box(gx*err,radius);dy=box(gy*err,radius)
            du=(cc*dx-bb*dy)/det;dv=(aa*dy-bb*dx)/det
            inc=np.stack([np.clip(du,-1.5,1.5),np.clip(dv,-1.5,1.5)],-1)
            flow+=inc*.8
            flow[:,:,0]=box(flow[:,:,0],1);flow[:,:,1]=box(flow[:,:,1],1)
    return flow

def adjacency(f):
    e=np.concatenate([f[:,[j,(j+1)%f.shape[1]]] for j in range(f.shape[1])])
    return np.unique(np.sort(e,axis=1),axis=0)

def vertex_normals(v,f):
    n=np.zeros_like(v);fn=np.cross(v[f[:,1]]-v[f[:,0]],v[f[:,2]]-v[f[:,0]])
    for j in range(f.shape[1]):np.add.at(n,f[:,j],fn)
    return n/np.maximum(np.linalg.norm(n,axis=1,keepdims=True),1e-8)

def weights_for(v,f,cs):
    n=vertex_normals(v,f);w=visibility(v,n,cs)
    for j,c in enumerate(cs):
        uv=project(v,c);q=v@c['R'].T+c['t'];z=q[:,2]
        maskpath=ROOT.parent/'scratch'/(c['view_id']+'_mask.png')
        if maskpath.exists():
            m=np.asarray(Image.open(maskpath)).astype(np.float32)/255
            w[:,j]*=np.clip((sample(m,uv)-.2)/.8,0,1)
        xy=np.rint(uv/2).astype(int);xy[:,0]=np.clip(xy[:,0],0,333);xy[:,1]=np.clip(xy[:,1],0,511)
        zb=np.full((512,334),1e6,np.float32)
        np.minimum.at(zb,(xy[:,1],xy[:,0]),z)
        for _ in range(2):
            zb=np.minimum.reduce([zb,np.roll(zb,1,0),np.roll(zb,-1,0),np.roll(zb,1,1),np.roll(zb,-1,1)])
        w[:,j]*=np.clip((10-(z-zb[xy[:,1],xy[:,0]]))/7,0,1)
    w=w**6
    bad=w.sum(1)<1e-8
    # Unobserved nape is present in 3D, but never used as a second face.
    w[bad,0]=(v[bad,0]>=0).astype(float)
    w[bad,1]=0
    w[bad,2]=(v[bad,0]<0).astype(float)
    w/=np.maximum(w.sum(1,keepdims=True),1e-8)
    return w

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--source',default='../candidate');ap.add_argument('--work',default='../scratch');args=ap.parse_args()
    src=Path(args.source).resolve();work=Path(args.work).resolve();assets=ROOT/'assets';assets.mkdir(exist_ok=True)
    shutil.copy2(src/'cameras.json',assets/'cameras.json');shutil.copy2(src/'speech.wav',assets/'speech.wav')
    d=np.load(work/'compact.npz');v=d['verts'];f=d['faces'];cs=cameras(src/'cameras.json')[:3]
    e=adjacency(f);n=vertex_normals(v,f);weights=weights_for(v,f,cs)
    # The texture weights and geometric solve are independent of T1/T2.
    refs=[];prev=[None]*3;uvs=[];jac=[]
    for c in cs:
        im=Image.open(src/'views'/c['view_id']/'frames'/c['frames'][0]['file']).convert('RGB').resize((334,512),Image.Resampling.BILINEAR)
        refs.append(pyramid(np.asarray(im).astype(np.float32).mean(2)/255))
        uvs.append(project(v,c)/2)
        q=v@c['R'].T+c['t'];k=c['K'];z=q[:,2]
        J=np.stack([(k[0,0]/z)[:,None]*(c['R'][0]-q[:,0:1]/z[:,None]*c['R'][2]),(k[1,1]/z)[:,None]*(c['R'][1]-q[:,1:2]/z[:,None]*c['R'][2])],1)
        jac.append(J)
        (assets/c['view_id']).mkdir(exist_ok=True)
    animation=[];t0=time.time()
    lhs=np.repeat(np.eye(3)[None],len(v),0)*.6
    for j,J in enumerate(jac):lhs+=np.einsum('nki,nkj->nij',J,J)*weights[:,j,None,None]
    inv=np.linalg.inv(lhs)
    for i in range(104):
        rhs=np.zeros_like(v)
        for j,c in enumerate(cs):
            im=Image.open(src/'views'/c['view_id']/'frames'/c['frames'][i]['file']).convert('RGB')
            out=im.resize((668,1024),Image.Resampling.LANCZOS);out.save(assets/c['view_id']/('%04d.png'%(i+1)),compress_level=2)
            if i:
                small=np.asarray(im.resize((334,512),Image.Resampling.BILINEAR)).astype(np.float32).mean(2)/255
                flow=flow_pair(refs[j],pyramid(small),prev[j]);prev[j]=flow
                shift=sample(flow,uvs[j])*2
                rhs+=np.einsum('nki,nk->ni',jac[j],shift)*weights[:,j,None]
        delta=np.einsum('nij,nj->ni',inv,rhs)
        delta=np.clip(delta,-16,16)
        delta=smooth(delta,e,5,.5)
        animation.append(v+delta)
        if i%10==0:print('animation',i+1,'/',104,'seconds',round(time.time()-t0,1),'max motion',float(abs(delta).max()),flush=True)
    ani=np.array(animation,np.float32)
    # A mild temporal filter removes patch-matching jitter, without shifting time.
    for _ in range(1):ani[1:-1]=.15*ani[:-2]+.7*ani[1:-1]+.15*ani[2:]
    np.savez_compressed(assets/'reconstruction.npz',verts=v,faces=f,weights=weights.astype(np.float32),animation=ani)
    print('assets complete',ani.shape,flush=True)

if __name__=='__main__':main()
