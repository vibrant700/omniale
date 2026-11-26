#include <opencv2/opencv.hpp>
using namespace cv;
extern "C" {
void threads(int n){setNumThreads(n);}
void remap1(const void* src, int h,int w,int ch,int u8,const float*xy, int H,int W,void* out,int border) {
 int typ=CV_MAKETYPE(u8?CV_8U:CV_32F,ch);
 Mat a(h,w,typ,(void*)src), b(H,W,typ,out), m(H,W,CV_32FC2,(void*)xy);
 remap(a,b,m,noArray(),INTER_LINEAR,border?BORDER_REPLICATE:BORDER_CONSTANT);
}
void resize1(const void* src,int h,int w,int ch,int u8,int H,int W,void*out,int method){
 int typ=CV_MAKETYPE(u8?CV_8U:CV_32F,ch);
 Mat a(h,w,typ,(void*)src),b(H,W,typ,out); resize(a,b,b.size(),0,0,method);
}
void flow1(const unsigned char* a,const unsigned char*b,int h,int w,float*out,int fine) {
 Mat m(h,w,CV_8U,(void*)a),n(h,w,CV_8U,(void*)b),f;
 auto d=DISOpticalFlow::create(DISOpticalFlow::PRESET_MEDIUM);
 d->setFinestScale(fine);
 d->calc(m,n,f);
 memcpy(out,f.ptr(),h*w*2*sizeof(float));
}
void raster(const float* v,int h,int w,int H,int W,float*depth,float*xy){
 for(int j=0;j<h-1;j++) for(int i=0;i<w;i++){
  int k=(i+1)%w,ids[]={j*w+i,j*w+k,(j+1)*w+i,(j+1)*w+k};
  for(int t=0;t<2;t++){
   const float *a=v+ids[t]*3,*b=v+ids[t+1]*3,*c=v+ids[t+2]*3;
   float dx=b[0]-a[0],dy=b[1]-a[1],ex=c[0]-a[0],ey=c[1]-a[1],det=dx*ey-dy*ex;
   if(fabs(det)<1e-7)continue;
   int l=std::max(0,(int)ceil(std::min({a[0],b[0],c[0]}))),r=std::min(W-1,(int)floor(std::max({a[0],b[0],c[0]})));
   int u=std::max(0,(int)ceil(std::min({a[1],b[1],c[1]}))),d=std::min(H-1,(int)floor(std::max({a[1],b[1],c[1]})));
   for(int y=u;y<=d;y++)for(int x=l;x<=r;x++){
    float u=((x-a[0])*ey-(y-a[1])*ex)/det,s=(dx*(y-a[1])-dy*(x-a[0]))/det;
    if(u<0||s<0||s+u>1)continue;
    float z=a[2]+u*(b[2]-a[2])+s*(c[2]-a[2]);
    int idx=y*W+x;
    if(z<depth[idx]){
     depth[idx]=z;
     xy[2*idx]=i+(t?1-u:u);
     xy[2*idx+1]=j+(t?u+s:s);
    }
   }
  }
 }
}
}
