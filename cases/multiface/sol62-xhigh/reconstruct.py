"""Calibrated multi-view reconstruction from the supplied Multiface clip."""
import argparse, concurrent.futures, json, os, shutil, subprocess
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

SIZE = (500, 768)
ROOT = Path(__file__).resolve().parent

# Image coordinates in the 500 x 768 working images, ordered I1, I2, I3.
# Markers are used as stereo constraints, not painted into the render.
LANDMARKS = {
    'brow_R': ((180,194),(341,155),None),
    'brow_L': (None,(160,163),(312,210)),
    'eye_out_R': ((257,263),(401,226),None),
    'eye_in_R': ((201,247),(320,222),None),
    'eye_out_L': (None,(126,228),(309,275)),
    'eye_in_L': (None,(224,214),(356,250)),
    'iris_R': ((211,255),(366,215),None),
    'iris_L': (None,(178,216),(347,264)),
    'wing_R': ((152,342),(329,316),None),
    'wing_L': (None,(225,315),(397,348)),
    'nostril_R': ((130,360),(309,314),None),
    'nostril_L': (None,(260,320),(415,369)),
    'mouth_R': ((171,451),(358,430),None),
    'mouth_L': (None,(209,433),(400,443)),
    'ear_R': ((418,451),(467,437),None),
    'ear_L': (None,(36,449),(151,463)),
    'temple_R': ((391,275),(439,252),None),
    'temple_L': (None,(40,256),(179,266)),
    'cheek_R': ((243,324),(392,290),None),
    'cheek_L': (None,(117,302),(266,329)),
    'jaw_R': ((261,554),(392,535),None),
    'jaw_L': (None,(102,534),(224,571)),
}

# Approximate tracing bands bound the silhouette search away from set lights.
BANDS = (
    ([(0,287),(40,216),(90,178),(125,158),(160,136),(190,129),
      (221,136),(244,117),(272,88),(310,61),(332,55),(354,66),
      (371,104),(409,104),(435,115),(452,108),(471,116),(493,125),
      (525,114),(551,121),(577,154),(606,176),(641,220),(670,245),
      (688,165),(720,124),(768,91)], None),
    ([(0,122),(25,90),(65,56),(110,28),(153,20),(195,20),(230,19),
      (285,26),(330,13),(374,12),(414,15),(449,26),(475,44),(521,49),
      (590,62),(653,68),(694,67),(720,43),(751,0),(768,0)],
     [(0,337),(35,378),(75,408),(115,427),(155,440),(200,447),(255,451),
      (300,453),(342,463),(377,470),(421,474),(447,464),(474,445),
      (520,433),(590,423),(662,422),(697,426),(724,463),(749,500),(768,500)]),
    (None,
     [(0,243),(21,286),(53,326),(100,357),(145,387),(171,408),(190,410),
      (217,405),(242,436),(268,466),(295,481),(321,491),(339,485),
      (355,454),(376,446),(411,441),(439,437),(455,426),(473,424),
      (490,424),(520,436),(545,432),(574,403),(612,364),(644,317),
      (660,298),(686,341),(720,385),(768,436)])
)


def cameras(path):
    cams = json.loads(path.read_text())['cameras']
    for c in cams:
        c['P'] = np.array(c['K']) @ np.array(c['world_to_camera'])
        c['P'][:2] *= (np.array(SIZE)/[c['width'], c['height']])[:,None]
        r = np.array(c['world_to_camera'])
        c['C'] = -r[:,:3].T @ r[:,3]
    return cams


def project(p, xyz):
    q = xyz @ p[:,:3].T + p[:,3]
    return q[...,:2] / q[...,2:3]


def triangulate(ps, coords):
    ar = []
    for p,(x,y) in zip(ps,coords):
        for row,t in zip(p,(x,y)):
            a = row - t*p[2]
            ar.append(a/np.linalg.norm(a[:3]))
    a = np.array(ar)
    return np.linalg.lstsq(a[:,:3],-a[:,3],rcond=None)[0]


def smooth(a, sig, axis=0):
    if sig <= 0:
        return a.copy()
    r = int(np.ceil(3*sig))
    a0 = np.moveaxis(a,axis,0)
    pad = np.pad(a0,[(r,r)]+[(0,0)]*(a0.ndim-1),mode='edge')
    w = np.exp(-.5*(np.arange(-r,r+1)/sig)**2)
    w /= w.sum()
    out = sum(v*pad[i:i+len(a0)] for i,v in enumerate(w))
    return np.moveaxis(out,0,axis)


def outlines(im, index, motion=0):
    ar = np.asarray(im).astype(np.int16)
    # Chromatic foreground criterion rejects neutral sources and lens ghosts.
    r,g,b = ar.transpose(2,0,1)
    good = ((g>15)&(g-b>4)&(g<160)) | ((g>18)&(g-b>2)&(g>=r-6)&(g<220))
    # The light patches sit in front of the silhouette in I1; isolate them
    # by local saturation and by the narrow hand-traced search band.
    good = (np.cumsum(np.pad(good,((0,0),(3,3))),axis=1)[:,6:]-
            np.cumsum(np.pad(good,((0,0),(3,3))),axis=1)[:,:-6]) >= 4
    H,W = good.shape
    out = []
    for side,band in zip((1,-1),BANDS[index]):
        if band is None:
            out.append(np.full(H, -1000 if side==1 else 1500.))
            continue
        base = np.interp(np.arange(H),*np.array(band).T)
        edge = base.copy()
        for y in range(H):
            m = 23
            if index==0 and (205<y<246 or 463<y<505 or 625<y<686): m=8
            if index==2 and (600<y<700): m=15
            if index==1 and 320<y<470: m=14
            if motion: m += min(motion,9)
            lo=max(0,int(base[y]-m))
            hi=min(W,int(base[y]+m+1))
            valid = np.flatnonzero(good[y,lo:hi])
            if len(valid):
                z = lo + (valid[0] if side==1 else valid[-1])
                edge[y] = z + 0.15
            elif base[y] < 25 or base[y] > 475:
                edge[y] = np.clip(base[y],0,W-1)
        median = np.median(np.stack([np.roll(edge,t) for t in range(-3,4)]),axis=0)
        median[:3],median[-3:]=edge[:3],edge[-3:]
        if index==1:
            # The chair's green-grey rim below the ears is not part of the face.
            good_y = (np.arange(H)<480) | (np.arange(H)>689)
            median=np.where(good_y,median,np.clip(median,base-5,base+5))
        out.append(smooth(median,2.0))
    return np.array(out)


def curve(y, pairs, softness=1.15):
    x = np.arange(np.floor(y.min())-10,np.ceil(y.max())+11)
    a = smooth(np.interp(x,*np.array(pairs).T),softness)
    return np.interp(y,x,a)


def profile(y, x, cs, edges):
    out = []
    for i in [0,2]:
        q = np.stack((x,y,np.full_like(y,1000,dtype=float)),axis=-1)
        for _ in range(5):
            uv = project(cs[i]['P'],q)
            dx = project(cs[i]['P'],q+[0,0,1])[:,0]-uv[:,0]
            d = np.interp(uv[:,1],np.arange(768),edges[i,0 if i==0 else 1])-uv[:,0]
            q[:,2] += np.clip(d/dx,-45,45)*.8
        out.append(q[:,2])
    return np.array(out)


# Ring controls: y, front profile z, lateral plane z, half-width and back z.
# All are in calibration units (mm). Shape in unobserved sectors is regularized.
RINGS = [
    (-153,1085,1090,2,1096),(-148,1059,1088,25,1120),(-140,1049,1087,37,1142),
    (-130,1034,1083,47,1151),(-120,1022,1080,61,1157),
    (-108,1010,1076,72,1164),(-95,1002,1071,77,1167),
    (-80,992,1072,81,1167),(-70,987,1074,83,1166),
    (-62,987,1075,85,1164),(-53,978,1074,86,1161),
    (-42,965,1072,85,1158),(-33,959,1071,83,1156),
    (-24,955,1071,82,1154),(-19,954.5,1071,82,1153),
    (-13,958,1070,82,1152),(-8,969,1069,82,1151),
    (-4,973,1069,82,1151),(3,972,1068,83,1151),
    (12,970,1067,84,1150),(20,975,1067,84,1150),
    (27,970,1067,84,1149),(34,973,1066,81,1148),
    (41,977,1064,77,1147),(49,972,1062,74,1146),
    (58,971,1060,72,1143),(66,973,1059,70,1141),
    (75,981,1058,69,1140),(85,991,1058,68,1139),
    (95,999,1058,67,1138),(106,1012,1059,65,1138),
    (113,1019,1061,65,1139),(122,1018,1062,72,1140),
    (132,1011,1061,93,1143),(141,1004,1060,132,1148),
    (151,996,1059,170,1153),(161,990,1058,201,1160),
    (177,985,1056,217,1165),(192,979,1054,227,1167)
]


def fit_rbf(cs, theta, ref_edges):
    pts, strengths = [], []
    for name, coords in LANDMARKS.items():
        good = [(c['P'],p) for c,p in zip(cs,coords) if p is not None]
        x,y0,z = triangulate(*zip(*good))
        # Keep I2 ray exact; it is the high-detail texture in this region.
        cp = cs[1]['P']
        u,v = coords[1]
        x,y0 = (u-cp[0,2])*z/cp[0,0], (v-cp[1,2])*z/cp[1,1]
        ring = rings(np.array([y0]),theta,cs,ref_edges,ref_edges)
        ring = ring[0]
        f = np.argsort(ring[:,0])
        iz = np.interp(x,ring[f,0],ring[f,2])
        if name.startswith('ear') or name.startswith('temple'):
            continue
        sz = 8. if name.startswith('eye') or name.startswith('iris') else 14.
        sy = 7. if name.startswith('eye') or name.startswith('iris') else 10.
        pts.append([x,y0,np.clip(z-iz,-21,23),sz,sy])
        strengths.append(.82 if name.startswith(('iris','eye','wing')) else .64)
    return np.array(pts), np.array(strengths)


def rings(y, theta, cs, edges, ref_edges, rbf=None):
    params=np.array(RINGS)
    zf,zs,w,zb = [curve(y,params[:,[0,i]],1.9 if i>1 else 1.2) for i in range(1,5)]
    pivot = curve(y,[(-153,0),(-105,4),(-72,9),(-46,12),(-22,16),(-7,14),(45,14),
                     (70,11),(103,9),(140,5),(192,4)])
    xc = curve(y,[(-153,0),(-105,1),(-65,1),(-20,4),(30,4),(63,1),(100,0),(140,-2),(192,-2)])
    measured = profile(y,pivot,cs,edges)
    reference = profile(y,pivot,cs,ref_edges)
    delta = np.median(measured-reference,axis=0)
    win=np.interp(y,[-153,-128,-70,-25,-12,0,58,88,113,134,192],
                    [0,0,.26,.40,.45,.86,.96,.75,.12,0,0])
    # Separate dynamic silhouette from noisy individual edge samples.
    dsig = 1.6 / max(.10, np.mean(np.diff(y))) if len(y)>1 else 0
    dz = np.clip(smooth(delta,dsig),-17,19)*win
    # Fit the transverse extent where the extremity is actually observed.
    q=np.stack((xc,y,zs),axis=-1)
    uv=project(cs[1]['P'],q)
    e0,e1=[np.interp(uv[:,1],np.arange(768),edges[1,k]) for k in range(2)]
    cp=cs[1]['P']
    xl=(e0-cp[0,2])*zs/cp[0,0]
    xr=(e1-cp[0,2])*zs/cp[0,0]
    # Near the ears use a smooth continuation of the cranium instead of
    # expanding the whole cross section to fit the loose helix.
    leeway=np.interp(y,[-153,-110,-45,-19,29,44,120,150,192],[2,2,2,4,2,2,1,0,0])
    xlo=xc-w
    xhi=xc+w
    a=np.interp(y,[-153,-138,-130,-113,-94,-32,-16,32,51,105,119,143,155,192],
                [0,0,.05,.80,.93,.75,.34,.36,.84,.94,.94,.72,0,0])
    xlo += a*np.clip(xl+leeway-xlo,-14,15)
    xhi += a*np.clip(xr-leeway-xhi,-14,15)
    xlo = smooth(xlo,dsig*2.1)
    xhi = smooth(xhi,dsig*2.1)
    xc=(xlo+xhi)*.5
    sx=(xhi-xlo)*.5
    co=np.cos(theta)[None,:]
    si=np.sin(theta)[None,:]
    front=np.maximum(co,0)
    x=xc[:,None]+sx[:,None]*si+(pivot-xc)[:,None]*front**1.65
    yy=np.broadcast_to(y[:,None],x.shape)
    # The helix sits off the cranium; keep the ear relief localized.
    ear_theta = np.where(theta>=0,1.49,-1.61)
    ear_y = 11 + np.where(theta>=0,1.,4.)
    ear_body = np.exp(-((theta-ear_theta)/.235)**4-.5*((yy-ear_y)/22.)**4)
    x += (si * ear_body*np.where(theta>=0,6.8,5.)) * np.exp(-.5*((yy-13)/25.)**2)
    # The bridge and nose are a narrow ridge on the broad face profile.
    power=curve(y,[(-153,.94),(-101,.90),(-73,.88),(-46,.98),(-18,.96),(4,.76),
                   (28,.77),(52,.67),(75,.72),(100,.90),(143,.63),(192,.55)])
    nose=curve(y,[(-153,0),(-76,0),(-62,5),(-52,14),(-40,27),(-26,33),(-19,34),
                  (-14,30),(-8,20),(-3,12),(3,5),(12,0),(192,0)],1.8)
    nwidth=curve(y,[(-153,18),(-63,20),(-47,15),(-26,17),(-15,20),(-4,15),(192,20)])
    base=zf+nose
    nosef=np.exp(-.5*(np.arcsin(np.clip(si,-1,1))*sx[:,None]/nwidth[:,None])**2)
    z = base[:,None]+(zs-base)[:,None]*(1-front)**power[:,None]
    z -= nose[:,None]*nosef*front
    z += dz[:,None]*(.23*front + .77*np.exp(-.5*((x-pivot[:,None])/32)**2))*front**.4
    z += (zb-zs)[:,None]*np.maximum(-co,0)**.94
    if rbf is not None:
        pts,strengths=rbf
        den=np.ones_like(x)*.22
        num=np.zeros_like(x)
        for (px,py,d,sx0,sy0),v in zip(pts,strengths):
            w0=np.exp(-.5*((x-px)/sx0)**2-.5*((yy-py)/sy0)**2)*v*front
            num+=w0*d
            den+=w0
        z+=num/den
    return np.stack((x,yy,z),axis=-1)


def sample(im,x,y):
    h,w=im.shape[:2]
    x=np.clip(x-.5,0,w-1.001)
    y=np.clip(y-.5,0,h-1.001)
    i,j=x.astype('int32'),y.astype('int32')
    a,b=(x-i)[...,None],(y-j)[...,None]
    return ((1-b)*((1-a)*im[j,i]+a*im[j,i+1])+
            b*((1-a)*im[j+1,i]+a*im[j+1,i+1]))


def ramp(x):
    x=np.clip(x,0,1)
    return x*x*(3-2*x)


def mouth_relief(grid, cs, front):
    uv=project(cs[1]['P'],grid)
    x,y=uv.transpose(2,0,1)
    middle = np.clip(1-((x-283)/73.)**2,0,1)**.6
    zone = np.exp(-.5*((y-(427+4*(x-283)/73.))/19.)**4)*middle
    row = sample(front,x,y)[...,0]
    cavity=ramp((29-row)/15)*zone*(grid[...,2]<1015)
    dz=6.1*cavity
    # Along I2 rays: sculpt the oral pocket without sliding the photographed lips.
    return grid*(1+dz[...,None]/grid[...,2:3])


def atlas(grid, theta, cs, images, edges):
    norm=np.cross(np.gradient(grid,axis=0), np.gradient(grid,axis=1))
    norm/=np.maximum(.001,np.linalg.norm(norm,axis=-1,keepdims=True))
    # Blend with a fixed subject-centered atlas, preserving cross-view identity.
    # Use the frontal camera for the central features; blend progressively
    # farther out across the cheek and temples. Maintain a wider protected mouth.
    yt = grid[...,1]
    guard=.11*np.exp(-.5*((yt-17)/23.)**2)
    wrig=ramp((theta[None,:]-.43-guard)/.83)
    wlef=ramp((-theta[None,:]-.43-guard)/.83)
    fr=1-np.maximum(wrig,wlef)
    priors=[wrig,fr,wlef]
    all_w=[]
    all_rgb=[]
    for i in range(3):
        cam=cs[i]
        uv=project(cam['P'],grid)
        x,y=uv.transpose(2,0,1)
        v=cam['C']-grid
        v/=np.linalg.norm(v,axis=-1,keepdims=True)
        d=(v*norm).sum(axis=-1)
        lo=np.interp(y,np.arange(768),edges[i,0])
        hi=np.interp(y,np.arange(768),edges[i,1])
        border=np.minimum(x-lo,hi-x)
        weight=(.05+.95*priors[i])**3 * np.clip((d+.06)/1.06,.003,1)**1.85
        weight*=np.clip((border+5)/11,.012,1)
        weight*=np.clip((np.minimum(x,500-x)+22)/32,.02,1)
        # Modest edge extension keeps dark set pixels out of the face texture.
        xx=np.maximum(np.minimum(x,hi-2.8),lo+2.8)
        if i!=1:
            xx=np.clip(xx,x-23,x+23)
        im=np.asarray(images[i]).astype(np.float32)
        col=sample(im,xx*(im.shape[1]/500.),y*(im.shape[0]/768.))
        all_w.append(weight)
        all_rgb.append(col)
    ww=np.array(all_w)
    # With no overlap (mainly rear skull), use a restrained extension of
    # adjacent photographed color, never the studio lights.
    col = (np.array(all_rgb)*ww[...,None]).sum(axis=0)/np.maximum(ww.sum(axis=0)[...,None],1e-10)
    # Continue the short, partially cropped collar on the shoulder using
    # the actually visible cloth in the two profile photographs.
    gx = grid[...,0]
    collar = yt + .62*(np.abs(gx)-96) - 142 + np.where(gx>0,-4.,1.)
    tex_mix = ramp((collar+1.3)/3.1)*ramp((yt-127)/8)
    for i, side in [(0,1),(2,-1)]:
        ix = (tex_mix>.001) & (gx*side > 0)
        cy = np.clip(706+(yt[ix]-137)*1.4+np.clip(collar[ix],0,48)*.55,704,766)
        edge = np.interp(cy,np.arange(768),edges[i,0 if i==0 else 1])
        cx = edge+(5+np.clip(collar[ix],0,50)*.18)*side
        im=np.asarray(images[i])
        cp = sample(im,cx*(im.shape[1]/500.),cy*(im.shape[0]/768.))
        blend = tex_mix[ix,None]
        col[ix]=col[ix]*(1-blend)+cp*blend
    return np.uint8(np.clip(col+.5,0,255))


def texture_grid(cs, edges, ref, rbf, h, w):
    th=-np.pi+2*np.pi*(np.arange(w)+.5)/w
    yy=-153+345*(np.arange(h)+.5)/h
    return rings(yy,th,cs,edges,ref,rbf),th


def frame_images(src, cs, i):
    return [Image.open(src/'views'/c['view_id']/'frames'/c['frames'][i]['file'])
            .convert('RGB') for c in cs[:3]]


def frame_edges(images):
    return np.array([outlines(im.resize(SIZE,Image.Resampling.LANCZOS),i) for i,im in enumerate(images)])


def make_frame(inputs):
    i, src, cs, ref, edges, rbf, target, tex = inputs
    yy=np.linspace(-153,192,199)
    th=np.linspace(-np.pi,np.pi,257)[:-1]
    im=frame_images(src,cs,i)
    front = np.asarray(im[1].resize(SIZE,Image.Resampling.LANCZOS).getchannel('G')
                       .filter(ImageFilter.GaussianBlur(2.1)),dtype=np.float32)[...,None]
    xyz=mouth_relief(rings(yy,th,cs,edges,ref,rbf),cs,front).astype(np.float32)
    grid,th2=texture_grid(cs,edges,ref,rbf,tex[1],tex[0])
    grid=mouth_relief(grid,cs,front)
    col=atlas(grid,th2,cs,im,edges)
    Image.fromarray(col).save(target/f'face_{i+1:04}.jpg',quality=96,subsampling=0)
    if i%10==0: print(f'Textured frame {i+1}',flush=True)
    return xyz


def find_edges(dat):
    i,src,cs = dat
    return frame_edges(frame_images(src,cs,i))


def build(src, out, count=104, jobs=3, width=1152, height=1024, cache=None):
    out.mkdir(parents=True,exist_ok=True)
    textures=out/'atlas'
    textures.mkdir(exist_ok=True)
    for name in ('cameras.json','speech.wav','SOURCE.txt'):
        shutil.copyfile(src/name,out/name)
    cs=cameras(src/'cameras.json')
    if cache is not None and cache.exists():
        ae=np.load(cache)[:count]
    else:
        with concurrent.futures.ProcessPoolExecutor(max_workers=jobs) as pool:
            ae=np.array(list(pool.map(find_edges, [(i,src,cs) for i in range(count)])))
        if cache is not None:
            np.save(cache,ae)
    ref=ae[0]
    # Light 30fps temporal filtering stabilizes tangencies without delaying lip motion.
    ae=smooth(ae,.64,axis=0)
    rbf=fit_rbf(cs,np.linspace(-1.4,1.4,257),ref)
    with concurrent.futures.ProcessPoolExecutor(max_workers=jobs) as pool:
        xyz=np.array(list(pool.map(make_frame,[(i,src,cs,ref,ae[i],rbf,textures,(width,height)) for i in range(count)])))
    np.savez_compressed(out/'performance.npz',xyz=xyz)


if __name__ == '__main__':
    pa=argparse.ArgumentParser(description=__doc__)
    pa.add_argument('--source',type=Path,default=ROOT.parent/'candidate')
    pa.add_argument('--assets',type=Path,default=ROOT/'assets')
    pa.add_argument('--frames',type=int,default=104)
    pa.add_argument('--jobs',type=int,default=3)
    pa.add_argument('--width',type=int,default=1152)
    pa.add_argument('--height',type=int,default=1024)
    pa.add_argument('--cache',type=Path)
    args=pa.parse_args()
    build(args.source,args.assets,args.frames,args.jobs,args.width,args.height,args.cache)
