"""Run with Blender: blender -b -t 4 --python build.py -- [options]."""
import bpy
import sys
import argparse
import json
from pathlib import Path
import numpy as np
from mathutils import Matrix

ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
from reconstruct import cameras, project, visibility, normals

def mathnode(nt,op,a,b=None):
    n=nt.nodes.new('ShaderNodeMath');n.operation=op
    for i,x in enumerate([a,b]):
        if x is None:continue
        if isinstance(x,(float,int)):n.inputs[i].default_value=x
        else:nt.links.new(x,n.inputs[i])
    return n.outputs[0]

def vect(nt,op,a,b=None):
    n=nt.nodes.new('ShaderNodeVectorMath');n.operation=op
    for i,x in enumerate([a,b]):
        if x is None:continue
        if isinstance(x,(tuple,list,np.ndarray)):n.inputs[i].default_value=tuple(x)
        else:nt.links.new(x,n.inputs[i])
    return n.outputs['Value'] if op=='DOT_PRODUCT' else n.outputs['Vector']

def make_camera(c):
    data=bpy.data.cameras.new(c['view_id']);obj=bpy.data.objects.new(c['view_id'],data);bpy.context.collection.objects.link(obj)
    R=c['R'];C=c['C'];w=np.eye(4);w[:3,:3]=R.T@np.diag([1,-1,-1]);w[:3,3]=C;obj.matrix_world=Matrix(w.tolist())
    K=c['K'];W=668;H=1024
    data.type='PERSP';data.sensor_fit='HORIZONTAL';data.sensor_width=36;data.lens=K[0,0]*36/W
    data.shift_x=(W/2-K[0,2])/W;data.shift_y=(K[1,2]-H/2)/W
    data.clip_start=1;data.clip_end=5000
    obj['calibration_K_668x1024']=K.ravel().tolist();obj['world_to_camera']=np.array(c['world_to_camera']).ravel().tolist()
    return obj

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--work',default=str(ROOT.parent/'scratch'));ap.add_argument('--source',default=str(ROOT.parent/'candidate'));ap.add_argument('--preview',action='store_true');ap.add_argument('--geometry-only',action='store_true');ap.add_argument('--hull',action='store_true');args=ap.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
    work=Path(args.work);assets=ROOT/'assets';assets.mkdir(exist_ok=True)
    bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
    path=assets/'reconstruction.npz'
    if not path.exists():path=work/('base.npz' if (work/'base.npz').exists() else 'hull.npz')
    if args.hull:path=work/'hull.npz'
    d=np.load(path);v=d['verts'];f=d['faces']
    mesh=bpy.data.meshes.new('Multiview_Head_Surface');mesh.from_pydata(v.tolist(),[],f.tolist());mesh.update()
    ob=bpy.data.objects.new('Reconstructed_Dynamic_Head',mesh);bpy.context.collection.objects.link(ob);bpy.context.view_layer.objects.active=ob;ob.select_set(True)
    if args.geometry_only:
        mod=ob.modifiers.new('Surface simplification','DECIMATE');mod.ratio=.13;bpy.ops.object.modifier_apply(modifier=mod.name)
        v=np.array([p.co[:] for p in ob.data.vertices],np.float32)
        # Store triangles for portable independent reconstruction.
        ob.data.calc_loop_triangles();f=np.array([p.vertices[:] for p in ob.data.loop_triangles],np.int32)
        np.savez_compressed(work/'compact.npz',verts=v,faces=f)
        return
    cs=cameras(assets/'cameras.json' if (assets/'cameras.json').exists() else Path(args.source)/'cameras.json')
    for c in cs:make_camera(c)
    scene=bpy.context.scene;scene.camera=bpy.data.objects['T1'];scene.frame_start=1;scene.frame_end=104;scene.render.fps=30
    scene.render.resolution_x=668;scene.render.resolution_y=1024;scene.render.resolution_percentage=100
    scene.render.pixel_aspect_x=1;scene.render.pixel_aspect_y=cs[3]['K'][0,0]/cs[3]['K'][1,1]
    scene.render.engine='CYCLES';scene.cycles.device='CPU';scene.cycles.samples=1;scene.cycles.use_denoising=False
    scene.render.threads_mode='FIXED';scene.render.threads=4
    scene.world.color=(0,0,0);scene.world.use_nodes=True;scene.world.node_tree.nodes.get('Background').inputs[0].default_value=(0,0,0,1)
    scene.view_settings.view_transform='Standard';scene.view_settings.look='None';scene.view_settings.exposure=0;scene.view_settings.gamma=1
    scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGB';scene.render.image_settings.color_depth='8'
    mat=bpy.data.materials.new('Calibrated_surface_radiance');mat.use_nodes=True;nt=mat.node_tree;nt.nodes.clear()
    out=nt.nodes.new('ShaderNodeOutputMaterial');em=nt.nodes.new('ShaderNodeEmission');nt.links.new(em.outputs[0],out.inputs['Surface']);ob.data.materials.append(mat)
    pos=nt.nodes.new('ShaderNodeNewGeometry').outputs['Position']
    # Per-surface confidence is common to all render cameras, not target-dependent.
    if 'weights' in d:weights=d['weights']
    else:
        n=np.zeros_like(v)
        fn=np.cross(v[f[:,1]]-v[f[:,0]],v[f[:,2]]-v[f[:,0]])
        for k in range(f.shape[1]):np.add.at(n,f[:,k],fn)
        n/=np.maximum(np.linalg.norm(n,axis=1,keepdims=True),1e-8)
        weights=visibility(v,n,cs[:3])**4
        weights/=np.maximum(weights.sum(1,keepdims=True),1e-8)
    attr=mesh.color_attributes.new(name='SourceConfidence',type='FLOAT_COLOR',domain='POINT')
    attr.data.foreach_set('color',np.concatenate([weights,np.ones((len(v),1))],1).astype(np.float32).ravel())
    an=nt.nodes.new('ShaderNodeVertexColor');an.layer_name='SourceConfidence';separate=nt.nodes.new('ShaderNodeSeparateColor');nt.links.new(an.outputs['Color'],separate.inputs['Color'])
    cols=[]
    for j,c in enumerate(cs[:3]):
        q=[mathnode(nt,'ADD',vect(nt,'DOT_PRODUCT',pos,c['R'][i]),float(c['t'][i])) for i in range(3)]
        u=mathnode(nt,'ADD',mathnode(nt,'MULTIPLY',mathnode(nt,'DIVIDE',q[0],q[2]),float(c['K'][0,0]/668)),float(c['K'][0,2]/668))
        vv=mathnode(nt,'SUBTRACT',1.,mathnode(nt,'ADD',mathnode(nt,'MULTIPLY',mathnode(nt,'DIVIDE',q[1],q[2]),float(c['K'][1,1]/1024)),float(c['K'][1,2]/1024)))
        co=nt.nodes.new('ShaderNodeCombineXYZ');nt.links.new(u,co.inputs[0]);nt.links.new(vv,co.inputs[1])
        tex=nt.nodes.new('ShaderNodeTexImage');tex.name='Observed_'+c['view_id'];tex.interpolation='Linear';tex.extension='EXTEND'
        p=assets/c['view_id']/'0001.png'
        if p.exists():
            im=bpy.data.images.load(str(p));im.source='SEQUENCE';tex.image=im;tex.image_user.frame_duration=104;tex.image_user.frame_start=1;tex.image_user.use_auto_refresh=True;im.filepath='//assets/'+c['view_id']+'/0001.png'
        else:tex.image=bpy.data.images.load(str(Path(args.source)/'views'/c['view_id']/'frames'/c['frames'][0]['file']));tex.image.pack()
        nt.links.new(co.outputs[0],tex.inputs['Vector'])
        cols.append(vect(nt,'SCALE',tex.outputs['Color']))
        # SCALE uses its dedicated scalar socket rather than the second vector.
        nt.links.new(separate.outputs[j],cols[-1].node.inputs['Scale'])
    color=vect(nt,'ADD',vect(nt,'ADD',cols[0],cols[1]),cols[2]);nt.links.new(color,em.inputs['Color'])
    for p in mesh.polygons:p.use_smooth=True
    if 'animation' in d:
        ob.shape_key_add(name='Basis')
        for i,coords in enumerate(d['animation']):
            key=ob.shape_key_add(name='Capture_%03d'%(i+1));key.data.foreach_set('co',coords.astype(np.float32).ravel())
            for fr,val in [(max(1,i),0),(i+1,1),(min(104,i+2),0)]:
                if (fr==1 and i==0) or (fr==104 and i==103):continue
                key.value=val;key.keyframe_insert('value',frame=fr)
            if i==0:key.value=1;key.keyframe_insert('value',frame=1);key.value=0;key.keyframe_insert('value',frame=2)
            if i==103:key.value=0;key.keyframe_insert('value',frame=103);key.value=1;key.keyframe_insert('value',frame=104)
        action=mesh.shape_keys.animation_data.action
        for layer in action.layers:
            for strip in layer.strips:
                for bag in strip.channelbags:
                    for fc in bag.fcurves:
                        for kp in fc.keyframe_points:kp.interpolation='LINEAR'
    if (assets/'speech.wav').exists():
        ed=scene.sequence_editor_create();ed.strips.new_sound('Original_48kHz_Speech',str(assets/'speech.wav'),channel=1,frame_start=1)
        bpy.data.sounds[-1].filepath='//assets/speech.wav'
    scene['Reconstruction']='Three calibrated input views; time-varying 3D surface and view-independent surface radiance.'
    scene['Timeline']='frame n: time (n-1)/30 s; 104 observed frames; original audio unchanged'
    scene.render.use_sequencer=False
    scene.frame_set(1);bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'scene.blend'))
    if args.preview:
        for cam in ['T1','T2']:
            scene.camera=bpy.data.objects[cam];scene.render.pixel_aspect_y=float(scene.camera['calibration_K_668x1024'][0]/scene.camera['calibration_K_668x1024'][4]);scene.render.filepath=str(work/(cam+'_preview.png'));bpy.ops.render.render(write_still=True)

if __name__=='__main__':main()
