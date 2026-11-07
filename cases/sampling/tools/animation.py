"""Generic frame rendering helpers; no lesson-specific scenes."""
import os
from pathlib import Path
import shutil
import subprocess
from PIL import Image, ImageDraw, ImageFont

def encoder():
    found=shutil.which('ffmpeg')
    if found:return found
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()

def font(size=32):
    paths=[os.environ.get('CASE_FONT',''),'C:/Windows/Fonts/msyh.ttc',
           '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc']
    for path in paths:
        if path and Path(path).is_file():return ImageFont.truetype(path,size)
    raise RuntimeError('Set CASE_FONT to an available Chinese font file.')

def polyline(draw, points, box, xlim, ylim, color='#166f68', width=3):
    x0,y0,x1,y1=box
    coords=[(x0+(x-xlim[0])/(xlim[1]-xlim[0])*(x1-x0),
             y1-(y-ylim[0])/(ylim[1]-ylim[0])*(y1-y0)) for x,y in points]
    if len(coords)>1:draw.line(coords,fill=color,width=width)
    return coords

def render(draw_frame, output='preview.mp4', duration=4, size=(1280,720), fps=25, background='#f4f3ee'):
    output=Path(output)
    output.parent.mkdir(parents=True,exist_ok=True)
    command=[encoder(),'-y','-v','error','-f','rawvideo','-pix_fmt','rgb24',
             '-s',f'{size[0]}x{size[1]}','-r',str(fps),'-i','pipe:0',
             '-an','-c:v','libx264','-pix_fmt','yuv420p',str(output)]
    with subprocess.Popen(command,stdin=subprocess.PIPE) as process:
        try:
            for i in range(round(duration*fps)):
                image=Image.new('RGB',size,background)
                draw_frame(i/fps,ImageDraw.Draw(image))
                process.stdin.write(image.tobytes())
        finally:
            process.stdin.close()
        if process.wait():raise RuntimeError('Video render failed.')
    return output

def compose(video, audio, output, captions=None):
    command=[encoder(),'-y','-v','error','-i',str(video),'-i',str(audio)]
    if captions:command+=['-i',str(captions)]
    command+=['-map','0:v:0','-map','1:a:0','-c:v','copy','-c:a','aac']
    if captions:command+=['-map','2:s:0','-c:s','mov_text']
    command+=['-movflags','+faststart',str(output)]
    subprocess.run(command,check=True)
