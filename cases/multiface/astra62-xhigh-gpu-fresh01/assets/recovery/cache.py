from reconstruct import *
import multiprocessing as mp

def oral(v,im):
    a=resize(im,1024,667,3).astype('f')
    y,x=np.ogrid[:1024,:667];box=((x-374)/107)**2+((y-560)/41)**2<1
    cavity=((a[:,:,1]>a[:,:,0]+1.3)&(a[:,:,1]>29))|(a[:,:,1]<15)
    depth=ndi.gaussian_filter(ndi.binary_closing(cavity&box,iterations=2).astype('f'),2)
    aperture=ndi.distance_transform_edt(depth>.45)
    q=proj(v,1)*.5
    recession=remap(np.clip((aperture-1.5)*.8,0,4.1),q)
    recession*=np.exp(-((tt-.16)/.46)**8)
    return v*(1+recession[:,:,None]/v[:,:,2,None])

def lengthen(v):
    last=v[-1];r0=np.hypot((last[:,0]-3)/.84,last[:,2]-1070)
    rows=[]
    for dy in np.arange(3,103,3):
        rx=205;rz=119
        r1=1/np.sqrt((.84*np.sin(th)/rx)**2+(np.cos(th)/rz)**2)
        r=r0+(r1-r0)*(1-np.exp(-dy/20))
        rows.append(np.stack([3+.84*r*np.sin(th),last[:,1]+dy,1070-r*np.cos(th)],-1))
    return np.concatenate([v,np.array(rows,'f')])

def bake_full(v,ims,ms,scale=6):
    h=v.shape[0]
    w=weights(v[:H],ms)
    w=np.concatenate([w,np.zeros((h-H,W,3),'f')])
    s=w.sum(2); rel=np.clip(s/.07,0,1)
    w/=np.maximum(s[:,:,None],1e-7)
    uvs=[proj(v,i) for i in range(3)]
    low=sum(remap(ims[i],uvs[i]).astype('f')*w[:,:,i,None] for i in range(3))
    # Harmonic-looking, low-frequency extension across crops. For chest and
    # fabric beyond the plates, replace stretched boundary texels with samples
    # from a measured patch instead of continuing the last row of the camera.
    near=ndi.distance_transform_edt(s<.045,return_distances=False,return_indices=True)
    fallback=ndi.gaussian_filter(low[near[0],near[1]],(4,4,0))
    y=v[:,:,1];x=v[:,:,0];z=v[:,:,2]
    collar=150+15*np.cos(tt[0]) - .25*np.abs(x)
    cloth=np.clip((y-collar)/2+.5,0,1)
    skin=np.array([61.,62.,36.]);cotton=np.array([66.,83.,67.])
    falloff=np.clip((y-109)/24,0,1)[:,:,None]
    fallback=fallback*(1-falloff)+falloff*(skin+(cotton-skin)*cloth[:,:,None])
    # Reuse measured pore / weave variation, tiled with reflected edges.
    sample=ims[2][1730:1900,440:620].astype('f')
    sample-=ndi.gaussian_filter(sample,(10,10,0))
    atlas=np.empty((h*scale,W*scale,3),np.uint8)
    for sl in range(0,h*scale,144):
        en=min(sl+144,h*scale)
        bx,by=np.meshgrid((np.arange(W*scale)+.5)/scale,(np.arange(sl,en)+.5)/scale)
        uv=np.stack([bx,by],-1).astype('f')
        whi=remap(w,uv);col=np.zeros(whi.shape,'f')
        for i in range(3):
            p=remap(uvs[i],uv)
            col+=remap(ims[i],p)*whi[:,:,i,None]
        rh=remap(rel,uv)[:,:,None]
        tex=sample[(169-np.abs((by*5.8).astype(int)%338-169)),(179-np.abs((bx*5.3).astype(int)%358-179))]
        at=col*rh+(remap(fallback,uv)+tex*.76)*(1-rh)
        atlas[sl:en]=np.uint8(np.clip(at+.5,0,255))
    return atlas

def one(n):
    ims=[image(i,n) for i in range(3)]
    ms=[signed(mask(a,i)) for i,a in enumerate(ims)]
    v=tracked(v0,gs0,ims,ms) if n else v0.copy()
    v=lengthen(oral(v,ims[1]))
    atlas=bake_full(v,ims,ms)
    Image.fromarray(atlas).save(OUT/'radiance'/f'capture_{n+1:04d}.jpg',quality=96,subsampling=0)
    ids=np.unique(np.r_[np.arange(0,len(v),2),len(v)-1])
    np.save(S/f'key{n:03}.npy',v[ids,::2])
    if n in [0,24,56,79,103]:
        pair=[]
        for i in [3,4]:
            dep,xy=raster(v,i)
            col=remap(atlas,xy*6-.5);col[dep>99999-1]=[4,3,6];pair.append(col)
        saveim(S/f'cache{n}.jpg',np.concatenate(pair,1))
    return n

if __name__=='__main__':
    if sys.argv[1]=='consolidate':
        vs=np.stack([np.load(S/f'key{n:03}.npy') for n in range(104)])
        deltas=np.rint((vs-vs[:1])*100).astype(np.int16)
        np.savez_compressed(OUT/'performance.npz',basis=vs[0],delta=deltas,
            rows=np.unique(np.r_[np.arange(0,H+34,2),H+33]),atlas_rows=H+34)
    else:
        (OUT/'radiance').mkdir(parents=True,exist_ok=True)
        im0=[image(i,0) for i in range(3)];gs0=[flowgray(a) for a in im0]
        v0=finalbase(im0,[signed(mask(a,i)) for i,a in enumerate(im0)])
        with mp.Pool(5) as pool:
            for n in pool.imap_unordered(one,[int(v) for v in sys.argv[1:]] if sys.argv[1]!='all' else range(104)):
                print(n+1,flush=True)
