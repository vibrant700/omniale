"""Build or render the calibrated Blender scene. Run with Blender's Python."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

import bpy
import numpy as np
from mathutils import Matrix, Vector
from bpy_extras.object_utils import world_to_camera_view


ROOT = Path(__file__).resolve().parent
W, H = 668, 1024
# OpenCV world mm -> Blender Z-up meters.
AXIS = np.array([[1,0,0],[0,0,1],[0,-1,0]],dtype=float)
LOCAL = np.diag([1.,-1.,-1.])


def linear(x):
    x = x / 255.
    return x/12.92 if x < .04045 else ((x+.055)/1.055)**2.4


def collection(scene, name):
    col = bpy.data.collections.new(name)
    scene.collection.children.link(col)
    return col


def add_camera(data, col):
    name = data['view_id']
    cam = bpy.data.cameras.new(name + ' | Pinhole')
    ob = bpy.data.objects.new(name,cam)
    col.objects.link(ob)
    ext = np.array(data['world_to_camera'])
    r0,t = ext[:,:3],ext[:,3]
    # The JSON is rounded; project the rotation onto SO(3).
    u,_,vt = np.linalg.svd(r0)
    r = u @ vt
    basis = AXIS @ r.T @ LOCAL
    center = AXIS @ (-r.T @ t) * .001
    mx=np.eye(4)
    mx[:3,:3] = basis
    mx[:3,3] = center
    ob.matrix_world = Matrix(mx)
    k = np.array(data['K'])
    k[:2] *= (np.array([W,H])/np.array([data['width'],data['height']]))[:,None]
    fx,fy = k[0,0],k[1,1]
    aspect = fx/fy
    cam.type = 'PERSP'
    cam.sensor_fit = 'VERTICAL'
    cam.sensor_height = 36.
    cam.lens = fy*cam.sensor_height/H
    cam.shift_x = (W/2-k[0,2])/(H*aspect)
    cam.shift_y = (k[1,2]-H/2)/H
    cam.clip_start,cam.clip_end = .03,20.
    cam.display_size = .10
    cam.passepartout_alpha = 1.
    ob['role'] = data['role']
    ob['pixel_aspect_ratio'] = aspect
    ob['K_668x1024'] = [float(i) for i in k.ravel()]
    ob['world_to_camera_mm'] = [float(i) for i in ext.ravel()]
    return ob


def set_camera(scene, name):
    ob = bpy.data.objects.get(name)
    if ob is None or ob.type != 'CAMERA':
        raise RuntimeError(f'No calibrated camera named {name}.')
    scene.camera = ob
    ratio = float(ob['pixel_aspect_ratio'])
    scene.render.pixel_aspect_x = max(1,1/ratio)
    scene.render.pixel_aspect_y = max(1,ratio)


def face_material(path, count):
    mat = bpy.data.materials.new('01 | Captured radiance · synchronized UV atlas')
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    uv = nt.nodes.new('ShaderNodeUVMap')
    uv.uv_map = 'CaptureUV'
    uv.location = (-525,40)
    tex = nt.nodes.new('ShaderNodeTexImage')
    tex.name = 'Performance atlas'
    tex.label = 'Multi-camera appearance | 1 image per frame'
    tex.location = (-330,40)
    tex.image = bpy.data.images.load(str(path),check_existing=False)
    tex.image.name = 'Performance atlas (sRGB)'
    tex.image.source = 'SEQUENCE'
    tex.extension = 'REPEAT'
    tex.interpolation = 'Linear'
    usr = tex.image_user
    usr.frame_start,usr.frame_duration,usr.frame_offset = 1,count,0
    usr.use_auto_refresh = True
    em = nt.nodes.new('ShaderNodeEmission')
    em.location = (-5,40)
    em.label = 'Original studio lighting is in the capture'
    out = nt.nodes.new('ShaderNodeOutputMaterial')
    out.location = (220,40)
    nt.links.new(uv.outputs['UV'],tex.inputs['Vector'])
    nt.links.new(tex.outputs['Color'],em.inputs['Color'])
    nt.links.new(em.outputs[0],out.inputs['Surface'])
    return mat


def make_performance(col, assets):
    data = np.load(assets/'performance.npz')['xyz']
    count, rows, cols, _ = data.shape
    xyz = (data @ (AXIS.T*.001)).astype(np.float32)
    index = np.arange(rows*cols).reshape(rows,cols)
    a = index[:-1].ravel()
    b = index[1:].ravel()
    c = np.roll(index[1:],-1,axis=1).ravel()
    d = np.roll(index[:-1],-1,axis=1).ravel()
    faces = np.stack((a,b,c,d),axis=1).tolist()
    faces += [index[0,::-1].tolist(),index[-1].tolist()]
    mesh = bpy.data.meshes.new('Portrait surface | continuous transverse rings')
    mesh.from_pydata(xyz[0].reshape(-1,3).tolist(),[],faces)
    mesh.update()
    body = bpy.data.objects.new('Speaker | animated head, neck & shoulders',mesh)
    col.objects.link(body)
    mesh.polygons.foreach_set('use_smooth',np.ones(len(faces),dtype=bool))
    uv = mesh.uv_layers.new(name='CaptureUV')
    ii,jj=np.meshgrid(np.arange(cols),np.arange(rows-1))
    uu,vv=ii/cols,1-jj/(rows-1)
    vnext=vv-1/(rows-1)
    unext=uu+1/cols
    uvs = np.stack((uu,vv,uu,vnext,unext,vnext,unext,vv),axis=-1).ravel()
    cap = np.stack([(np.arange(cols)+.5)/cols, np.zeros(cols)],axis=-1)
    cap1=cap[::-1].copy()
    cap1[:,1]=1
    uv.data.foreach_set('uv',np.concatenate([uvs,cap1.ravel(),cap.ravel()]).astype(np.float32))
    body.data.materials.append(face_material(assets/'atlas'/'face_0001.jpg',count))
    keys = body.shape_key_add(name='Capture 001',from_mix=False)
    body.data.shape_keys.use_relative = False
    keys.interpolation = 'KEY_LINEAR'
    data_keys=body.data.shape_keys
    times=[keys.frame]
    for i in range(1,count):
        key = body.shape_key_add(name=f'Capture {i+1:03}',from_mix=False)
        key.data.foreach_set('co',xyz[i].ravel())
        key.interpolation = 'KEY_LINEAR'
        times.append(key.frame)
    data_keys.eval_time=times[0]
    data_keys.keyframe_insert(data_path='eval_time',frame=1)
    if count>1:
        data_keys.eval_time=times[-1]
        data_keys.keyframe_insert(data_path='eval_time',frame=count)
        ad=data_keys.animation_data
        bag=ad.action.layers[0].strips[0].channelbag(ad.action_slot)
        for fc in bag.fcurves:
            for p in fc.keyframe_points:
                p.interpolation = 'LINEAR'
        ad.action.name = 'Performance | absolute capture time'
    body['capture'] = 'Triangulated facial landmarks, tracked silhouettes and projected source images'
    body['scope'] = 'Observed front and sides of the portrait. Rear and cropped areas are extrapolated.'
    return body,count


def add_headrest(col):
    r = np.array([.0,.25,.50,.72,.84,.91,.97,1.,.98,.90,.0])[:,None]
    ang = np.linspace(0,2*np.pi,128,endpoint=False)[None,:]
    c,s = np.cos(ang), np.sin(ang)
    x = 3+103*r*np.sign(c)*np.abs(c)**.78
    y = 44+62*r*np.sign(s)*np.abs(s)**.78 + 4*(x/103)
    d = np.array([1157,1157,1157,1158,1160,1163,1166,1173,1182,1185,1186])
    z = np.broadcast_to(d[:,None],x.shape)
    pts = np.stack((x,y,z),axis=-1)
    # Collapse the two terminal rows to single pole vertices.
    xyz = np.concatenate([pts[0,:1],pts[1:-1].reshape(-1,3),pts[-1,:1]])
    ids = np.arange(1,len(xyz)-1).reshape(-1,128)
    nx=np.roll(ids,-1,axis=1)
    sides=np.stack((ids[:-1],ids[1:],nx[1:],nx[:-1]),axis=-1).reshape(-1,4)
    faces=np.stack((np.zeros(128,dtype=int),ids[0],nx[0]),axis=-1).tolist()
    faces+=sides.tolist()
    faces+=np.stack((ids[-1],np.full(128,len(xyz)-1),nx[-1]),axis=-1).tolist()
    mesh=bpy.data.meshes.new('Padded headrest')
    mesh.from_pydata((xyz @ (AXIS.T*.001)).tolist(),[],faces)
    mesh.update()
    mesh.polygons.foreach_set('use_smooth',np.ones(len(faces),dtype=bool))
    ob=bpy.data.objects.new('Headrest | dark upholstery',mesh)
    col.objects.link(ob)
    rim=np.array([0,0,0,1,4,10,14,8,3,0,0],dtype=float)[:,None]
    rim=np.broadcast_to(rim,pts.shape[:2])*(.35+.65*(.5+.5*c))
    f=np.concatenate([rim[0,:1],rim[1:-1].ravel(),rim[-1,:1]])
    rgb=np.stack([5+f*.53,6+f*1.12,7+f*.93],axis=-1)
    rgb=np.array([[linear(v) for v in row]+[1.] for row in rgb],np.float32)
    attr=mesh.color_attributes.new(name='Captured rim',type='FLOAT_COLOR',domain='POINT')
    attr.data.foreach_set('color',rgb.ravel())
    mat=bpy.data.materials.new('02 | Upholstery in ambient spill')
    mat.use_nodes=True
    nt=mat.node_tree
    nt.nodes.clear()
    vc=nt.nodes.new('ShaderNodeVertexColor')
    vc.layer_name=attr.name
    vc.location=(-220,0)
    em=nt.nodes.new('ShaderNodeEmission')
    out=nt.nodes.new('ShaderNodeOutputMaterial')
    out.location=(200,0)
    nt.links.new(vc.outputs['Color'],em.inputs['Color'])
    nt.links.new(em.outputs[0],out.inputs['Surface'])
    mesh.materials.append(mat)
    ob['capture'] = 'Approximation of the visible chair rim in I2'


def build(assets, output):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.preferences.filepaths.save_version = 0
    scene=bpy.context.scene
    scene.name = 'Multiface | Synchronized portrait'
    portrait = collection(scene,'01   PERFORMANCE')
    target = collection(scene,'02   TARGET CAMERAS')
    inputs = collection(scene,'03   SOURCE CAMERAS')
    studio = collection(scene,'04   STUDIO')
    scene.unit_settings.system='METRIC'
    body,count=make_performance(portrait,assets)
    add_headrest(studio)
    for data in json.loads((assets/'cameras.json').read_text())['cameras']:
        add_camera(data,inputs if data['role']=='input' else target)
    world=bpy.data.worlds.new('Black capture volume')
    world.use_nodes=True
    world.node_tree.nodes.get('Background').inputs[0].default_value=(*[linear(x) for x in (5,4,6)],1)
    scene.world=world
    scene.render.engine = 'CYCLES'
    scene.cycles.device = 'CPU'
    scene.cycles.samples=8
    scene.cycles.use_denoising=False
    scene.cycles.max_bounces=0
    scene.render.filter_size=1.15
    scene.render.resolution_x,scene.render.resolution_y = W,H
    scene.render.resolution_percentage=100
    scene.render.fps,scene.render.fps_base = 30,1.
    scene.frame_start,scene.frame_end = 1,count
    scene.view_settings.view_transform='Standard'
    scene.view_settings.look='None'
    scene.render.image_settings.file_format='PNG'
    scene.render.image_settings.color_mode='RGB'
    scene.render.image_settings.compression=15
    scene.render.filepath='//renders/T1/'
    scene.render.film_transparent=False
    scene.sequence_editor_create().strips.new_sound('Original speech | 48 kHz mono',str(assets/'speech.wav'),channel=1,frame_start=1)
    scene.render.use_sequencer=False
    scene.timeline_markers.new('Capture start | audio in',frame=1)
    scene.timeline_markers.new(f'Capture end | frame {count:03}',frame=count)
    scene.sync_mode='AUDIO_SYNC'
    scene['timing'] = 'Blender frame n = (n - 1) / 30 seconds.'
    set_camera(scene,'T1')
    scene.frame_set(1)
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type=='VIEW_3D':
                sp = area.spaces.active
                sp.region_3d.view_perspective='CAMERA'
                sp.region_3d.view_camera_zoom=4
                sp.shading.color_type='MATERIAL'
                sp.overlay.show_overlays=False
    bpy.context.view_layer.objects.active=body
    output.parent.mkdir(parents=True,exist_ok=True)
    # Keep Blender's // paths explicitly anchored at the actual project directory.
    for im in bpy.data.images:
        if im.source=='SEQUENCE':
            im.filepath='//'+Path(os.path.relpath(im.filepath,output.parent)).as_posix()
    for snd in bpy.data.sounds:
        snd.filepath='//'+Path(os.path.relpath(snd.filepath,output.parent)).as_posix()
    bpy.ops.wm.save_as_mainfile(filepath=str(output),relative_remap=False)


def render(path, camera, out, start, stop, threads):
    if Path(bpy.data.filepath).resolve() != path:
        bpy.ops.wm.open_mainfile(filepath=str(path))
    scene=bpy.context.scene
    set_camera(scene,camera)
    scene.render.filepath=str(out) + os.sep
    scene.render.threads_mode='FIXED'
    scene.render.threads=threads
    scene.frame_start=start or scene.frame_start
    scene.frame_end=stop or scene.frame_end
    scene.frame_set(scene.frame_start)
    out.mkdir(parents=True,exist_ok=True)
    bpy.ops.render.render(animation=True)


def check(path):
    if Path(bpy.data.filepath).resolve()!=path:
        bpy.ops.wm.open_mainfile(filepath=str(path))
    scene=bpy.context.scene
    probes=np.array([[0.,0.,1000.,1.],[-60.,-70.,1030.,1.],[70.,70.,1100.,1.]])
    for name in ('I1','I2','I3','T1','T2'):
        set_camera(scene,name)
        cam=scene.camera
        k=np.array(cam['K_668x1024']).reshape(3,3)
        ext=np.array(cam['world_to_camera_mm']).reshape(3,4)
        pix=probes @ (k@ext).T
        pix=pix[:,:2]/pix[:,2:]
        rendered=[]
        for pt in probes:
            a=world_to_camera_view(scene,cam,Vector(AXIS@pt[:3]*.001))
            rendered.append([a.x*W,(1-a.y)*H])
        err=np.max(np.abs(rendered-pix))
        print(f'{name} maximum projected pixel error: {err:.5f}')
        assert err < .025
    obj = next(i for i in scene.objects if i.name.startswith('Speaker |'))
    keys=obj.data.shape_keys.key_blocks
    count=len(keys)
    assert scene.frame_end==count and scene.frame_start==1 and scene.render.fps==30
    coords=np.empty(len(obj.data.vertices)*3,np.float32)
    for n in sorted({1,(count+1)//2,count}):
        scene.frame_set(n)
        obj.evaluated_get(bpy.context.evaluated_depsgraph_get()).data.vertices.foreach_get('co',coords)
        expected=np.empty_like(coords)
        keys[n-1].data.foreach_get('co',expected)
        assert np.max(np.abs(expected-coords)) < 1e-6
    img=next(i for i in bpy.data.images if i.source=='SEQUENCE')
    img_path=Path(bpy.path.abspath(img.filepath))
    assert img.filepath.startswith('//') and all((img_path.parent/f'face_{i+1:04}.jpg').is_file()
                                                  for i in range(count))
    sound=next(iter(bpy.data.sounds))
    assert sound.filepath.startswith('//') and Path(bpy.path.abspath(sound.filepath)).is_file()
    print(f'Validated {count} shape keys, complete portable atlas sequence, and relative audio path.')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',choices=['build','render','encode','check'])
    parser.add_argument('--assets',type=Path,default=ROOT/'assets')
    parser.add_argument('--blend',type=Path,default=ROOT/'scene.blend')
    parser.add_argument('--camera',choices=['T1','T2','I1','I2','I3'],default='T1')
    parser.add_argument('--out',type=Path)
    parser.add_argument('--frames',type=Path)
    parser.add_argument('--start',type=int)
    parser.add_argument('--stop',type=int)
    parser.add_argument('--threads',type=int,default=4)
    args=parser.parse_args(sys.argv[sys.argv.index('--')+1:])
    assets,blend=args.assets.resolve(),args.blend.resolve()
    if args.command=='build':
        build(assets,blend)
    elif args.command=='render':
        render(blend,args.camera,(args.out or ROOT.parent/'scratch'/args.camera).resolve(),
               args.start,args.stop,args.threads)
    elif args.command=='check':
        check(blend)
    else:
        frames=(args.frames or ROOT.parent/'scratch'/args.camera).resolve()
        out=(args.out or ROOT/(args.camera+'.mp4')).resolve()
        subprocess.run([
            'ffmpeg','-v','error','-y','-framerate','30','-start_number','1','-i',str(frames/'%04d.png'),
            '-i',str(assets/'speech.wav'),'-map','0:v:0','-map','1:a:0',
            '-c:v','libx264','-preset','slow','-crf','16','-pix_fmt','yuv420p',
            '-vf','scale=out_color_matrix=bt709','-color_primaries','bt709','-colorspace','bt709',
            '-color_trc','iec61966-2-1','-color_range','tv','-c:a','aac','-b:a','192k','-ar','48000',
            '-movflags','+faststart',str(out)
        ],check=True)


if __name__=='__main__':
    main()
