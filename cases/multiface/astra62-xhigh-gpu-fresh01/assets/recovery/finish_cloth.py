from cache import *
from scipy.interpolate import PchipInterpolator
def finish(n):
    path=OUT/'radiance'/f'capture_{n+1:04d}.jpg'
    im=np.asarray(Image.open(path)).copy()
    v=np.load(S/f'key{n:03d}.npy')
    # Continuous shoulder/collar extension in the overlap lost to the
    # portrait crops. Keep original skin up to the base of the neck.
    h,w=im.shape[:2];cut=6*249
    bx,by=np.meshgrid((np.arange(w)+.5)/12,(np.arange(cut,h)+.5)/12)
    p=remap(v,np.stack([bx,by],-1));x,y,z=p.transpose(2,0,1)
    ang=(bx/(W/2)*2*np.pi-np.pi)
    line=151+13*np.cos(ang-.1)-.17*abs(x)+2*np.sin(2*ang)
    d=y-line
    detail=grain[(169-np.abs((by*10.8).astype(int)%338-169)),(179-np.abs((bx*10.3).astype(int)%358-179))]
    side=np.sin(ang);front=np.cos(ang)
    shade=2.8*side+1.7*front-2.5*np.cos(y/13+ang*2)
    clav=3.2*np.exp(-((y-(149-.14*abs(x)))/3.5)**2)*np.maximum(0,front)
    skin=np.array([64.,65.,39.])+(shade+clav)[:,:,None]+detail*.65
    fold=3.5*np.cos(d/12+side*5)+2*np.cos(d/6+ang*3)
    cotton=np.array([61.,78.,66.])+(shade+fold)[:,:,None]+detail*.85
    piping=2*np.exp(-((d-1.2)/.8)**2)-7*np.exp(-((d-2.6)/.5)**2)-7*np.exp(-((d+.2)/.6)**2)
    mix=np.clip(d*2+.5,0,1)[:,:,None]
    mat=skin*(1-mix)+cotton*mix+piping[:,:,None]
    alpha=np.clip((y-109)/23,0,1);alpha=alpha*alpha*(3-2*alpha)
    im[cut:]=np.uint8(np.clip(im[cut:]*(1-alpha[:,:,None])+mat*alpha[:,:,None],0,255))
    Image.fromarray(im).save(path,quality=96,subsampling=0)
if __name__=='__main__':
    grain=image(2,0)[1730:1900,440:620].astype('f')
    grain-=ndi.gaussian_filter(grain,(8,8,0))
    with mp.Pool(5) as pp:list(pp.imap_unordered(finish,range(104)))
