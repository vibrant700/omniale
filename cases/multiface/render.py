"""Reopen the delivered scene, render T1/T2, and mux the original audio."""
import bpy
from pathlib import Path
import argparse
import sys
import subprocess
import json

ROOT=Path(__file__).resolve().parent

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--camera',choices=['T1','T2','both'],default='both');ap.add_argument('--frames-dir',default=str(ROOT.parent/'scratch'/'render'));ap.add_argument('--preview',action='store_true')
    args=ap.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
    bpy.ops.wm.open_mainfile(filepath=str(ROOT/'scene.blend'))
    scene=bpy.context.scene
    assert scene.frame_start==1 and scene.frame_end==104
    scene.render.use_sequencer=False
    scene.render.resolution_x=668;scene.render.resolution_y=1024;scene.render.resolution_percentage=100
    scene.render.threads_mode='FIXED';scene.render.threads=4
    scene.cycles.samples=1;scene.cycles.use_denoising=False
    names=['T1','T2'] if args.camera=='both' else [args.camera]
    for name in names:
        scene.camera=bpy.data.objects[name]
        k=scene.camera['calibration_K_668x1024'];scene.render.pixel_aspect_y=k[0]/k[4]
        folder=Path(args.frames_dir)/name;folder.mkdir(parents=True,exist_ok=True)
        frames=[1,26,51,76,104] if args.preview else range(1,105)
        for frame in frames:
            scene.frame_set(frame)
            scene.render.filepath=str(folder/('%04d.png'%frame))
            bpy.ops.render.render(write_still=True)
            print('DELIVERY_RENDER',name,frame,flush=True)
        if not args.preview:
            subprocess.run(['ffmpeg','-y','-hide_banner','-loglevel','error','-framerate','30','-start_number','1','-i',str(folder/'%04d.png'),'-i',str(ROOT/'assets'/'speech.wav'),'-map','0:v:0','-map','1:a:0','-frames:v','104','-c:v','libx264','-preset','medium','-crf','18','-pix_fmt','yuv420p','-r','30','-c:a','aac','-b:a','192k','-ar','48000','-af','atrim=end_sample=166400','-movflags','+faststart',str(ROOT/(name+'.mp4'))],check=True)
            print('ENCODED',name,flush=True)

if __name__=='__main__':main()
