"""Calibrated surface reconstruction, in the I2 camera coordinate frame (mm)."""

import os, sys, json, ctypes as ct

from pathlib import Path

import numpy as np

from scipy import ndimage as ndi

from PIL import Image

S=Path(os.environ['MF_WORK'])

D=Path(os.environ['MF_INPUT'])

OUT=Path(os.environ['MF_ASSETS'])

cs=json.loads((D/'cameras.json').read_text())['cameras']

P=np.array([np.array(c['K'])@np.array(c['world_to_camera']) for c in cs],np.float32)

C=np.array([-np.array(c['world_to_camera'])[:,:3].T@np.array(c['world_to_camera'])[:,3] for c in cs],np.float32)

op=ct.CDLL(str(S/'ops.so')); op.threads(2)

def ptr(a): return a.ctypes.data_as(ct.c_void_p)

def remap(a,xy,border=1):
    a=np.ascontiguousarray(a);xy=np.ascontiguousarray(xy,dtype='f');h,w=xy.shape[:2]
    if a.dtype!=np.uint8:a=a.astype('f',copy=False)
    o=np.empty((h,w)+a.shape[2:],a.dtype)
    op.remap1(ptr(a),*a.shape[:2],a.shape[2] if a.ndim==3 else 1,int(a.dtype==np.uint8),ptr(xy),h,w,ptr(o),border)
    return o

def resize(a,h,w,mode=1):
    a=np.ascontiguousarray(a)
    if a.dtype!=np.uint8:a=a.astype('f',copy=False)
    o=np.empty((h,w)+a.shape[2:],a.dtype)
    op.resize1(ptr(a),*a.shape[:2],a.shape[2] if a.ndim==3 else 1,int(a.dtype==np.uint8),h,w,ptr(o),mode)
    return o

def flow(a,b,fine=1):
    a=np.ascontiguousarray(a,np.uint8); b=np.ascontiguousarray(b,np.uint8)
    o=np.empty((*a.shape,2),'f')
    op.flow1(ptr(a),ptr(b),*a.shape,ptr(o),fine)
    return o

def image(i,n):
    return np.asarray(Image.open(D/'views'/cs[i]['view_id']/'frames'/cs[i]['frames'][n]['file']).convert('RGB'))

def mask(im,i):
    a=resize(im,1024,667,3).astype(np.int16)
    x,y=np.meshgrid(np.arange(667)/2,np.arange(1024)/2)
    # Avoid practical bulbs at the profile edge. Skin is olive, chair neutral.
    m=(a[:,:,1]>12)&(a[:,:,0]-a[:,:,2]>4)&(a[:,:,1]-a[:,:,2]>3)
    if i!=1:m&=~((a.min(2)>100)&(a.max(2)-a.min(2)<62))
    m=ndi.binary_opening(np.pad(m,4,mode='edge'),iterations=3)[4:-4,4:-4]
    m=ndi.binary_closing(np.pad(m,5,mode='edge'),iterations=4)[5:-5,5:-5]
    lab,N=ndi.label(m);cnt=np.bincount(lab.ravel());cnt[0]=0;m=lab==cnt.argmax()
    m=ndi.binary_fill_holes(np.pad(m,1))[1:-1,1:-1]
    return m

def signed(m):
    return (ndi.distance_transform_edt(m)-ndi.distance_transform_edt(~m)).astype('f')

def proj(x,i):
    v=x@P[i,:,:3].T+P[i,:,3]; return v[...,:2]/v[...,2:]

def saveim(path,a):Image.fromarray(np.uint8(np.clip(a,0,255))).save(path)

H,W=312,512

ys=np.linspace(-147,164,H,dtype='f')

th=np.linspace(-np.pi,np.pi,W,endpoint=False,dtype='f')

tt,yy=np.meshgrid(th,ys)

def curve(y,yp,rp):
    return np.interp(y,yp,rp).astype('f')

def basis(t,y):
    c=np.stack([0*y+3,y,curve(y,[-147,-68,35,85,165],[1069,1067,1062,1066,1070])],-1)
    d=np.stack([.84*np.sin(t),np.zeros_like(y),-np.cos(t)],-1)
    return c,d

cc,dd=basis(tt,yy)

def xyz(r):return cc+dd*r[...,None]

def hull(ms):
    # A loose cranial cap and trunk bound only constrain regions beyond the plates.
    box=curve(yy,[-147,-146,-141,-132,-124,-110,-85,40,70,98,118,140,164],[4,17,38,61,76,97,121,119,117,120,183,242,258])
    box*=1+np.maximum(-np.cos(tt),0)*.02
    # Shoulders broaden laterally outside the bottom of the portrait.
    shoulder=curve(yy,[85,105,121,150],[0,0,55,125])
    box-=shoulder*(1-abs(np.sin(tt))**4)*.85
    lo=np.zeros_like(box);hi=box.copy()
    for it in range(10):
        rr=(lo+hi)/2;v=xyz(rr)
        ok=np.ones(rr.shape,bool)
        for i,m in enumerate(ms):
            uv=proj(v,i)*.5
            # A clipped portrait is an open boundary, never a black mask.
            dis=remap(m,uv)
            outside=np.maximum.reduce([-uv[:,:,0],uv[:,:,0]-666,-uv[:,:,1],uv[:,:,1]-1023])
            ok&=np.maximum(dis,outside*.85)>-.1
        lo=np.where(ok,rr,lo);hi=np.where(ok,hi,rr)
    return (lo+hi)/2

def normals(v):
    n=np.cross(np.roll(v,-1,axis=1)-np.roll(v,1,axis=1),np.gradient(v,axis=0))
    n/=np.linalg.norm(n,axis=-1,keepdims=True)+1e-8
    return -n

def gg(a,s):return ndi.gaussian_filter(a,s,mode=('nearest','wrap'))

def vis(v,i):
    n=normals(v);tow=C[i]-v
    return np.clip((n*tow).sum(2)/(np.linalg.norm(tow,axis=2)+1e-7),0,1)

def smoothfit(data,weight,base,rad=8,its=5):
    # Multi-scale normalized convolution, interpolating only supported detail.
    v=base.copy()
    for s in [rad*2,rad,rad*.5,max(1.,rad*.24),1.0][:its]:
        w=gg(weight,s)
        corr=gg((data-v)*weight,s)/(w+.002)
        v+=corr
    return v

def stereo(ims,ms,h,base,span,step,patch,limit,robust=False):
    # A local radial sweep; patches are reprojected with the current surface
    # tangent, rather than compared in their native, foreshortened coordinates.
    gray=[resize(im,1024,667,3).astype('f')@np.array([.4,.5,.1],'f') for im in ims]
    normed=[]
    for g in gray:
        blur=ndi.gaussian_filter(g,4);dev=g-blur
        normed.append((dev/(ndi.gaussian_filter(dev**2,5)+2.2**2)**.5).astype('f'))
    toffs=np.arange(-span,span+.01,step,dtype='f')
    costs=[[],[]];patch=float(patch)
    for off in toffs:
        r=base+off
        v=xyz(r);uvs=[proj(v,i)*.5 for i in range(3)]
        pics=[remap(im,uv) for im,uv in zip(normed,uvs)]
        raw=[remap(im,uv) for im,uv in zip(gray,uvs)]
        for k,i in enumerate([0,2]):
            a,b=pics[i],pics[1]
            # ZNCC on high-pass detail plus bounded low-frequency mismatch.
            mean=lambda x:gg(x,patch)
            corr=mean(a*b)/np.sqrt(mean(a*a)*mean(b*b)+.003)
            color=mean(np.minimum(abs(raw[i]-raw[1]),25))*.007
            cost=1-corr+color
            for j in [1,i]:
                u=uvs[j]; dist=np.minimum.reduce([u[:,:,0],666-u[:,:,0],u[:,:,1],1023-u[:,:,1],remap(ms[j],u)])
                cost+=np.clip((1-dist)*.17,0,2)
            costs[k].append(cost)
    ds=[];ws=[]
    v=xyz(base)
    for k,i in enumerate([0,2]):
        cost=np.array(costs[k]); orient=(tt>-.07) if i==0 else (tt<.27)
        prior=(abs(toffs)[:,None,None]/limit)**1.5*.18
        adj=cost+prior+np.maximum(0,(base-h)[None]+toffs[:,None,None]-.5)*.14
        idx=np.argmin(adj,axis=0); pc=np.take_along_axis(cost,idx[None],axis=0)[0]
        offs=toffs[idx]
        # Reject ambiguous matches (second basin comparable to first).
        amb=np.min(np.where(abs(toffs[:,None,None]-offs)>max(2,step*2),adj,10),axis=0)-adj.min(axis=0)
        weight=np.clip(((.60 if robust else .86)-pc)*3,0,1)**2*np.clip(amb*8,0,1)*orient
        weight*=np.clip((np.minimum(vis(v,i),vis(v,1))+.12)*4,0,1)
        weight*=np.abs(tt)<1.58
        ds.append(offs*weight);ws.append(weight)
    w=sum(ws);d=sum(ds)/(w+1e-9)
    # Remove isolated false matches before extending the reliable offsets.
    wd=gg(w,4);local=gg(d*w,4)/(wd+.0001)
    w*=1/(1+(abs(d-local)/max(step*2.2,2.0))**3)
    if robust:
        return d,w
    out=smoothfit(base+d,w,base,7,4)
    return np.minimum(gg(out,.85),h+.5),w

def raster(v,i,height=1024,width=667):
    vd=v@P[i,:,:3].T+P[i,:,3]
    vd[:,:,:2]/=vd[:,:,2:]
    vd[:,:,0]*=width/1334; vd[:,:,1]*=height/2048
    vd=np.ascontiguousarray(vd,'f');depth=np.full((height,width),1e5,'f')
    uv=np.zeros((height,width,2),'f')
    op.raster(ptr(vd),*v.shape[:2],height,width,ptr(depth),ptr(uv))
    return depth,uv

def weights(v,ms):
    ws=[]
    for i in range(3):
        uv=proj(v,i)*.5
        depth,_=raster(v,i)
        z=v@P[i,2,:3]+P[i,2,3]
        err=z-remap(depth,uv)
        support=np.minimum.reduce([uv[:,:,0],666-uv[:,:,0],uv[:,:,1],1023-uv[:,:,1]])
        incidence=gg(vis(v,i),2.5)
        w=np.clip(incidence,.001,1)**2.6
        w*=np.clip((2.2-err)/1.8,0,1)*np.clip(support/5,0,1)*np.clip((remap(ms[i],uv)-.2)/5,0,1)
        if i==1:
            # Reserve front eye, nostril and lip interiors to the frontal plate.
            center=np.exp(-((tt-.13)/.76)**8)
            w*=1+3.5*center
        else:
            w*=np.clip((tt+.06)*5 if i==0 else (.33-tt)*5,0,1)
        ws.append(w)
    ws=np.stack(ws,axis=2)
    return ws

def sculpt(h):
    from scipy.interpolate import PchipInterpolator
    # Cross sections in polar head space; center profile is separately fitted
    # to the measured nose/lip/chin silhouettes.
    a=np.abs(np.rad2deg(np.arctan2(np.sin(tt-.165),np.cos(tt-.165))))
    angles=[0,7,14,23,37,54,70,90,115,145,180]
    table=np.array([
    [-87, 71,71,71,71,71,74,78,87,99,108,112],
    [-75, 78,78,78,78,78,78,80,90,102,112,116],
    [-68, 77,77,79,80,80,78,82,92,104,112,117],
    [-61, 75,74,75,79,82,78,82,92,103,113,116],
    [-51, 87,76,68,71,77,78,83,95,103,111,115],
    [-44, 98,80,67,69,76,77,83,95,104,111,115],
    [-36,105,86,71,72,79,82,85,94,105,111,115],
    [-27,109,94,76,75,83,86,87,94,102,110,114],
    [-20,111,102,78,77,84,87,89,95,101,110,114],
    [-15,109,105,84,76,84,88,90,96,102,110,114],
    [-12,104,101,88,78,84,88,90,96,102,110,114],
    [-8,94,93,88,79,84,88,90,97,102,109,113],
    [-3,92,89,84,81,85,88,91,97,102,109,113],
    [7,94,91,86,82,85,87,91,96,102,108,112],
    [13,95,92,87,83,85,87,91,96,102,108,112],
    [20,90,88,84,81,84,87,90,95,100,107,110],
    [27,94,91,85,80,83,86,88,93,100,106,110],
    [39,86,85,83,81,83,83,84,90,98,104,108],
    [54,95,92,88,82,81,79,78,84,93,100,104],
    [65,94,91,87,82,78,76,74,82,92,98,102],
    [76,83,81,80,77,72,70,70,79,90,97,100],
    [92,70,68,65,62,59,61,67,77,88,94,98],
    [108,51,49,48,48,50,55,66,77,87,93,96],
    [119,48,47,46,47,51,57,65,78,88,94,96],
    [130,62,59,57,57,60,65,75,92,101,105,104],
    [142,73,70,69,68,70,78,96,145,134,116,110],
    [164,87,86,84,83,89,101,137,225,169,137,123]
    ],float)
    col=PchipInterpolator(table[:,0],table[:,1:],axis=0)(np.maximum(ys,table[0,0]))
    r=np.array([PchipInterpolator(angles,row)(a[j]) for j,row in enumerate(col)],'f')
    # Smooth ellipsoidal cranial vault (the very crown is cropped in all views).
    f=np.maximum(.0008,1-((yy+54)/94)**2)
    ex,ez=82*np.sqrt(f),112*np.sqrt(f)
    sx=-7*np.minimum(1,np.sqrt(f)*2);sz=26*np.minimum(1,np.sqrt(f)*2)
    dx=dd[:,:,0];dz=dd[:,:,2]
    A=(dx/ex)**2+(dz/ez)**2;B=dx*sx/ex**2+dz*sz/ez**2
    ec=(B+np.sqrt(np.maximum(.000005,B*B+A*(1-(sx/ex)**2-(sz/ez)**2))))/A
    t=np.clip((-yy-83)/16,0,1);t=t*t*(3-2*t)
    r=r*(1-t)+ec*t
    # Blend into centerline depth from the profile envelope.
    hc=ndi.median_filter(h[:,269:273].mean(1),3)
    front=np.exp(-((a)/np.where((yy>-55)&(yy<-8),6,13))**2)
    front*=np.clip((yy+103)/15,0,1)*np.clip((135-yy)/15,0,1)
    r+=front*(hc[:,None]-r[:,270,None])
    return r

def fitprime(ims,ms):
    h=hull(ms); prior=sculpt(h)
    base=prior.copy()
    for it,(span,step,pat,g1,g2,mx) in enumerate([(19,1.,2.5,7,4,15),(8,.55,2,5,2.5,6),(3.8,.35,1.6,3.3,1.5,3.5)]):
        d,w=stereo(ims,ms,h,base,span,step,pat,span,True)
        # Robust kernel regression. Reject outliers before smoothing into low
        # texture areas. The empirical section is a weak observation everywhere.
        local=gg(w*d,g1)/(gg(w,g1)+.016)
        w1=w/(1+((d-local)/(4.3 if it==0 else 2.5))**4)
        local=gg(w1*d,g1)/(gg(w1,g1)+.008)
        fine=gg(w1*(d-local),g2)/(gg(w1,g2)+.013)
        base+=np.clip(local+fine,-mx,mx)
        base=gg(base,[1.35,1.2])
        # Clip only where the observed hull is meaningful, filtering spurious
        # segments caused by tiny practical lights touching the silhouette.
        hm=ndi.median_filter(h,size=(7,7))
        reliable=(abs(tt)<1.6)&(yy>-122)&(yy<125)
        base=np.where(reliable,np.minimum(base,.65*h+.35*hm+1.0),base)
        base=gg(base,.85)
    return base

def contour(v,ms,iterations=4,spread=4.4):
    v=v.copy()
    for it in range(iterations):
        ds=np.zeros((H,W),'f');ws=ds.copy()
        for i in range(3):
            z,xy=raster(v,i);region=z<99999
            edge=region & ~ndi.binary_erosion(region)
            edge[:4]=edge[-4:]=edge[:,:4]=edge[:,-4:]=False
            y,x=np.nonzero(edge); b,a=np.rint(xy[y,x]).astype(int).T
            a=a.clip(0,H-1);b%=W
            obs=ms[i][y,x];v0=v[a,b]
            move=(proj(v0+dd[a,b],i)-proj(v0,i))*.5
            gm=np.gradient(ms[i]);grad=gm[1][y,x]*move[:,0]+gm[0][y,x]*move[:,1]
            ok=(grad<-.4)&(a<H-3)&(a>0)
            # Indexing at the last row of the plate is cropping, not skin.
            ok&=(abs(obs)<100)
            adj=np.clip(-obs/np.minimum(grad,-.4),-9,9)
            np.add.at(ws,(a[ok],b[ok]),1.)
            np.add.at(ds,(a[ok],b[ok]),adj[ok])
        corr=gg(ds,spread)/(gg(ws,spread)+.05)
        v+=dd*np.clip(corr,-5,5)[:,:,None]*.78
    return v

def finalbase(ims,ms):
    r=np.load(S/'base.npy')
    # Smooth the transition from measured scalp into the unobserved crown.
    r+=np.clip((-yy-109)/14,0,1)*(gg(r,5)-r)
    # Ear cartilage: the profile plates localize helix, bowl and projecting tragus.
    for i,cx,cy,sx,sy in [(2,58,261,49,53),(0,329,257,49,55)]:
        uv=proj(xyz(r),i)/4;x=(uv[:,:,0]-cx)/sx;y=(uv[:,:,1]-cy)/sy
        x+=(.36 if i==2 else -.36)*(-y)
        rad=np.sqrt(x*x+y*y)
        relief=3*np.exp(-((rad-.82)/.17)**2)-4.4*np.exp(-(rad/.63)**4)
        r+=relief*(tt<-.9 if i==2 else tt>1.05)
    return contour(xyz(r),ms,7,5.0)

def flowgray(im):
    a=resize(im,1024,667,3).astype('f')@np.array([.34,.55,.11],'f')
    return np.uint8(np.clip(a*2.1+(a-ndi.gaussian_filter(a,5))*2.1,0,255))

def support(v,i):
    uv=proj(v,i)/2;depth,_=raster(v,i)
    diff=(v@P[i,2,:3]+P[i,2,3])-remap(depth,uv)
    support=np.minimum.reduce([uv[:,:,0],666-uv[:,:,0],uv[:,:,1],1023-uv[:,:,1]])
    return (np.clip((2.3-diff)/2.2,0,1)*np.clip(support/5,0,1)*np.clip((gg(vis(v,i),1.2)+.06)*2,0,1))

def tracked(v,gs0,ims,ms):
    AtA=np.zeros((H,W,3,3),'f');AtB=np.zeros((H,W,3),'f')
    for i in range(3):
        a,b=gs0[i],flowgray(ims[i])
        f=flow(a,b,0);uv=proj(v,i)/2
        d=remap(f,uv);dv=v@P[i,:,:3].T+P[i,:,3]
        J=(P[i,:2,:3]*.5-uv[:,:,:,None]*P[i,2,:3])/dv[:,:,2,None,None]
        w=support(v,i)
        # Brightness and forward/back checks downweight occluded teeth/lids.
        fb=flow(b,a,1)
        cycle=np.linalg.norm(d+remap(fb,uv+d),axis=2)
        w/=1+(cycle/2.5)**2
        wt=J.swapaxes(-1,-2)*w[:,:,None,None]
        AtA+=wt@J;AtB+=(wt@d[:,:,:,None])[:,:,:,0]
    eye=np.eye(3,dtype='f')
    def solve(lam,prior):
        return np.linalg.solve(AtA+eye*lam,(AtB+prior*lam)[:,:,:,None])[:,:,:,0]
    d=solve(.17,0)
    for sigma in [8,3]:
        prior=ndi.gaussian_filter(d,(sigma,sigma,0))
        d=solve(.55,prior)
    d=ndi.gaussian_filter(d,(1.15,1.15,0))
    return contour(v+d,ms,2,3.7)
