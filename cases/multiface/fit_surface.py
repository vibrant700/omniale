"""Landmark-constrained smooth depth surface, in calibration world units."""
from pathlib import Path
import numpy as np
from PIL import Image,ImageFilter
from reconstruct import cameras,triangulate,project

ROOT=Path(__file__).resolve().parent
WORK=ROOT.parent/'scratch'
CS=cameras(ROOT.parent/'candidate/cameras.json')[:3]

def main():
    # Correspondences measured on the supplied half-resolution observations.
    # I2 coordinates followed by I1 or I3, with their calibrated ray intersection.
    marks=[
      ((371,394),0,(80,440)),((371,394),2,(650,436)),
      ((359,307),0,(177,317)),((359,307),2,(556,312)),
      ((369,450),0,(151,488)),((369,450),2,(582,493)),
      ((410,425),0,(178,480)),((326,427),2,(550,483)),
      ((489,286),0,(294,345)),((537,297),0,(350,361)),((423,283),0,(247,329)),
      ((242,286),2,(466,352)),((168,300),2,(402,372)),((299,282),2,(498,335)),
      ((489,216),0,(285,275)),((231,216),2,(467,278)),
      ((369,556),0,(161,589)),((369,556),2,(585,577)),
      ((463,565),0,(232,608)),((277,565),2,(521,606)),
      ((370,531),0,(145,555)),((370,586),0,(153,624)),
      ((353,746),0,(177,758)),((353,746),2,(558,752)),
      ((350,690),0,(156,703)),((350,690),2,(574,695)),
      ((337,106),0,(302,100)),((337,106),2,(429,98)),
      ((342,30),0,(382,25)),((342,30),2,(328,22)),
      ((548,432),0,(398,488)),((181,434),2,(380,490)),
      ((548,657),0,(424,727)),((132,658),2,(338,731)),
      ((607,479),0,(614,518)),((27,477),2,(66,520)),
      ((338,892),0,(362,954)),((338,892),2,(368,952)),
    ]
    coords=[];depth=[]
    for uv,j,side in marks:
        p=triangulate([uv,side],[CS[1],CS[j]])
        coords.append(uv);depth.append(p[2])
        print(uv,j,'depth',round(p[2],1),'error',np.round(project(p,CS[1])-uv,1))
    # Additional silhouette/nape constraints ensure a genuine curved volume.
    additional=[(40,200,1060),(90,100,1050),(585,160,1060),(610,300,1055),
      (25,350,1050),(70,650,1045),(585,650,1045),(99,850,1055),(570,850,1055),
      (30,1000,1065),(640,1000,1065),(330,1015,1025),
      (130,35,1055),(530,35,1055),(330,0,1035),
      (155,190,1032),(540,190,1032),
      (210,395,1006),(480,395,1006),(220,520,1007),(510,520,1007)]
    coords+= [(a,b) for a,b,z in additional];depth +=[z for a,b,z in additional]
    # Consolidate duplicate measurements before solving a regularized TPS.
    unique={}
    for uv,z in zip(coords,depth):unique.setdefault(tuple(uv),[]).append(z)
    pts=np.array(list(unique))/400;zz=np.array([np.mean(a) for a in unique.values()])
    dist=((pts[:,None]-pts[None])**2).sum(2)
    kernel=dist*np.log(dist+1e-8)
    poly=np.column_stack([np.ones(len(pts)),pts]);mat=np.block([[kernel+np.eye(len(pts))*.0015,poly],[poly.T,np.zeros((3,3))]])
    coef=np.linalg.solve(mat,np.r_[zz,[0,0,0]])
    h,w=256,167
    yy,xx=np.mgrid[:h,:w];uv=np.stack([xx*4+2,yy*4+2],-1).reshape(-1,2)
    p=uv/400;dd=((p[:,None]-pts[None])**2).sum(2)
    z=(dd*np.log(dd+1e-8))@coef[:-3]+np.column_stack([np.ones(len(p)),p])@coef[-3:]
    z=np.clip(z,950,1105)
    Image.fromarray(((z.reshape(h,w)-945)*1.5).astype(np.uint8)).resize((668,1024)).save(WORK/'fitted_depth.png')
    c=CS[1];v=np.column_stack([(uv[:,0]-c['K'][0,2])/c['K'][0,0]*z,(uv[:,1]-c['K'][1,2])/c['K'][1,1]*z,z]).astype(np.float32)
    mask=np.array(Image.open(WORK/'I2_mask.png').resize((w,h),Image.Resampling.NEAREST))>0
    # Remove the capture cable and unobserved side fragments from the front outline.
    for row in range(h):
        ii=np.flatnonzero(mask[row])
        if len(ii):
            if row>115 and row<220:
                mask[row,:max(ii.min(),19)]=False;mask[row,min(ii.max()+1,152):]=False
    ids=np.arange(h*w).reshape(h,w)
    faces=[]
    for y in range(h-1):
        for x in range(w-1):
            if mask[y:y+2,x:x+2].all():
                a=ids[y,x];b=ids[y,x+1];c=ids[y+1,x];d=ids[y+1,x+1]
                faces.extend([(a,c,b),(b,c,d)])
    f=np.array(faces,np.int32)
    # Front and rear share the boundary: the result has physical head depth.
    used=np.unique(f);remap=np.full(len(v),-1,np.int32);remap[used]=np.arange(len(used));v=v[used];f=remap[f]
    all_edges=np.sort(np.concatenate([f[:,[0,1]],f[:,[1,2]],f[:,[2,0]]]),axis=1)
    ed,count=np.unique(all_edges,axis=0,return_counts=True);boundary=ed[count==1]
    n=len(v);back=v.copy();back[:,2]=1145-((back[:,1]+20)/400)**2*20
    back[:,0]*=.94
    sides=[]
    for a,b in boundary:sides.extend([(a,b,b+n),(a,b+n,a+n)])
    vv=np.concatenate([v,back]);ff=np.concatenate([f,f[:,::-1]+n,np.array(sides)])
    np.savez_compressed(WORK/'compact.npz',verts=vv,faces=ff)
    np.savez_compressed(WORK/'base.npz',verts=vv,faces=ff)
    print('surface',vv.shape,ff.shape,flush=True)

if __name__=='__main__':main()
