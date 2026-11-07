"""Neutral tool demonstration, not a lesson storyboard."""
from pathlib import Path
from animation import render, font, polyline

label=font()
def draw_frame(t, canvas):
    canvas.text((70,55),'基础动画示例：文字、线条与移动标记',font=label,fill='#172c32')
    coords=polyline(canvas,[(0,0),(1,1)],(100,180,1100,580),(0,1),(0,1))
    amount=min(t/3,1)
    x=coords[0][0]+amount*(coords[1][0]-coords[0][0])
    y=coords[0][1]+amount*(coords[1][1]-coords[0][1])
    canvas.ellipse((x-12,y-12,x+12,y+12),fill='#166f68')

if __name__=='__main__':
    render(draw_frame,Path(__file__).parent/'preview.mp4')
