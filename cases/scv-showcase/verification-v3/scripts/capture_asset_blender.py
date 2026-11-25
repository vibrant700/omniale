"""Trusted Blender-only capture; opens assets without executing embedded scripts."""
import argparse
import json
from pathlib import Path
import sys

import bpy
import numpy as np
from mathutils import Matrix, Vector


def parse():
    argv = sys.argv[sys.argv.index('--')+1:]
    p = argparse.ArgumentParser()
    p.add_argument('--blend', required=True)
    p.add_argument('--output', required=True)
    p.add_argument('--public-root', required=True)
    p.add_argument('--scene-name')
    p.add_argument('--views', nargs='*')
    p.add_argument('--mesh-only', action='store_true')
    p.add_argument('--save-control-blend')
    return p.parse_args(argv)


def dump(path, data):
    Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False)+'\n', encoding='utf-8')


def aim(obj, target, up):
    f = (Vector(target)-obj.location).normalized()
    right = f.cross(Vector(up)).normalized()
    obj.rotation_euler = Matrix((right, right.cross(f).normalized(), -f)).transposed().to_euler()


def inside(path, root):
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def main():
    args = parse()
    blend, out, public = Path(args.blend).resolve(), Path(args.output).resolve(), Path(args.public_root).resolve()
    out.mkdir(parents=True, exist_ok=True)
    cal = json.loads((public/'cameras.json').read_text(encoding='utf-8'))
    config = json.loads((public/'scene_setup.json').read_text(encoding='utf-8'))
    bpy.ops.wm.open_mainfile(filepath=str(blend), use_scripts=False, load_ui=False)
    scene = bpy.data.scenes[args.scene_name] if args.scene_name else bpy.context.scene
    if bpy.context.window is not None: bpy.context.window.scene = scene
    bpy.context.view_layer.update()
    deps = bpy.context.evaluated_depsgraph_get()
    vertices, triangles, object_audit = [], [], []
    offset = 0
    for instance in deps.object_instances:
        obj = instance.object
        if obj.type != 'MESH' or obj.hide_render:
            continue
        if not instance.is_instance and not obj.original.visible_get(view_layer=bpy.context.view_layer):
            continue
        mesh = obj.to_mesh(preserve_all_data_layers=True, depsgraph=deps)
        try:
            mesh.calc_loop_triangles()
            xyz = np.array([list(instance.matrix_world @ v.co) for v in mesh.vertices], dtype=np.float64)
            faces = np.array([list(t.vertices) for t in mesh.loop_triangles], dtype=np.int32).reshape(-1, 3)
            if len(xyz) and len(faces):
                vertices.append(xyz)
                triangles.append(faces+offset)
                offset += len(xyz)
                sv = np.linalg.svd(xyz-xyz.mean(0), compute_uv=False)
                object_audit.append({'object':obj.name, 'vertices':len(xyz), 'triangles':len(faces),
                    'instance':bool(instance.is_instance), 'world_extent':np.ptp(xyz,axis=0).tolist(),
                    'nonplanarity_ratio':float(sv[-1]/max(sv[0],1e-12)) if len(sv)==3 else 0,
                    'uv_layers':len(mesh.uv_layers)})
        finally:
            obj.to_mesh_clear()
    xyz = np.concatenate(vertices) if vertices else np.empty((0, 3), dtype=np.float64)
    faces = np.concatenate(triangles) if triangles else np.empty((0, 3), dtype=np.int32)
    assert np.isfinite(xyz).all(), 'Nonfinite geometry coordinates'
    np.savez_compressed(out/'mesh.npz', vertices=xyz, triangles=faces)
    resources = []
    used_images,visited_trees=set(),set()
    def collect_images(tree):
        if tree is None or tree.as_pointer() in visited_trees:
            return
        visited_trees.add(tree.as_pointer())
        visited_nodes=set()
        def visit(node):
            if node.as_pointer() in visited_nodes:return
            visited_nodes.add(node.as_pointer())
            image=getattr(node,'image',None)
            if image is not None:
                used_images.add(image)
            collect_images(getattr(node,'node_tree',None))
            for socket in node.inputs:
                for link in socket.links:visit(link.from_node)
        for node in tree.nodes:
            if getattr(node,'is_active_output',False) or node.type=='GROUP_OUTPUT':visit(node)
    for obj in scene.objects:
        if not obj.hide_render:
            indices={poly.material_index for poly in obj.data.polygons} if obj.type=='MESH' else set(range(len(obj.material_slots)))
            for index,slot in enumerate(getattr(obj,'material_slots',[])):
                if index in indices and slot.material:
                    collect_images(slot.material.node_tree)
            for modifier in obj.modifiers:
                collect_images(getattr(modifier,'node_group',None))
    collect_images(scene.world.node_tree if scene.world else None)
    for image in used_images:
        if image.source in {'FILE','SEQUENCE','MOVIE','TILED'}:
            path = Path(bpy.path.abspath(image.filepath, library=image.library))
            packed = bool(image.packed_file) or bool(getattr(image, 'packed_files', []))
            resources.append({'name':image.name, 'kind':'image', 'source':image.source, 'packed':packed,
                'path':str(path), 'exists':path.exists(), 'inside_relocated_submission':inside(path,blend.parent),
                'resolved':packed or (path.exists() and inside(path,blend.parent))})
    for library in bpy.data.libraries:
        path = Path(bpy.path.abspath(library.filepath))
        resources.append({'name':library.name, 'kind':'library', 'path':str(path), 'exists':path.exists(),
            'inside_relocated_submission':inside(path,blend.parent), 'resolved':path.exists() and inside(path,blend.parent)})
    audit = {'opened_without_embedded_script_execution':True, 'scene':scene.name, 'frame':scene.frame_current,
        'blender_version':bpy.app.version_string, 'objects':object_audit, 'vertices':len(xyz), 'triangles':len(faces),
        'has_renderable_mesh':bool(len(xyz) and len(faces)), 'resources':resources,
        'resources_resolved_in_relocated_copy':all(r['resolved'] for r in resources),
        'world_extent':np.ptp(xyz,axis=0).tolist() if len(xyz) else [0,0,0], 'renders':[],
        'alignment':'Fixed task coordinate system. No registration, scale fitting or per-view alignment.'}
    dump(out/'project_audit.json', audit)
    if args.save_control_blend:
        target=Path(args.save_control_blend).resolve()
        target.parent.mkdir(parents=True,exist_ok=True)
        bpy.context.preferences.filepaths.save_version=0
        bpy.ops.wm.save_as_mainfile(filepath=str(target))
    if args.mesh_only:
        print('MESH_CAPTURED', len(xyz), len(faces), flush=True)
        return
    assert audit['has_renderable_mesh'], 'No renderable mesh in delivered scene'
    for obj in list(scene.objects):
        if obj.type in {'LIGHT','CAMERA'}:
            bpy.data.objects.remove(obj, do_unlink=True)
    scene.world = bpy.data.worlds.new('Canonical evaluation world')
    scene.world.use_nodes = True
    background = scene.world.node_tree.nodes['Background']
    background.inputs['Color'].default_value = config['world']['background_color']
    background.inputs['Strength'].default_value = config['world']['strength']
    for light_cfg in config['lights']:
        data = bpy.data.lights.new(light_cfg['name'], light_cfg['type'])
        data.energy, data.shape, data.size = light_cfg['energy'], light_cfg['shape'], light_cfg['size']
        data.color = light_cfg['color']
        light = bpy.data.objects.new(light_cfg['name'], data)
        scene.collection.objects.link(light)
        light.location = light_cfg['location']
        aim(light, light_cfg['target'], light_cfg['up'])
    render = config['render']
    scene.render.engine = render['engine']
    scene.cycles.device = 'CPU'
    scene.cycles.samples = render['samples']
    scene.cycles.seed = 0
    scene.cycles.use_denoising = render['use_denoising']
    scene.render.threads_mode = 'AUTO'
    scene.render.resolution_x, scene.render.resolution_y = render['resolution']
    scene.render.resolution_percentage = render['resolution_percentage']
    scene.render.pixel_aspect_x, scene.render.pixel_aspect_y = render['pixel_aspect']
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'RGBA'
    scene.render.image_settings.color_depth = '8'
    scene.render.film_transparent = render['film_transparent']
    scene.render.use_compositing = False
    scene.render.use_sequencer = False
    scene.render.use_multiview = False
    scene.render.use_border = False
    scene.render.use_file_extension = True
    for layer in scene.view_layers:
        layer.material_override = None
    cm = config['color_management']
    scene.view_settings.view_transform = cm['view_transform']
    scene.view_settings.look = cm['look']
    scene.view_settings.exposure = cm['exposure']
    scene.view_settings.gamma = cm['gamma']
    scene.display_settings.display_device = cm['display_device']
    clay = bpy.data.materials.new('Canonical clay geometry inspection')
    clay.use_nodes = True
    shader = clay.node_tree.nodes.get('Principled BSDF')
    shader.inputs['Base Color'].default_value = (.62,.64,.68,1)
    shader.inputs['Roughness'].default_value = .85
    shader.inputs['Specular IOR Level'].default_value = .1
    camera_data = bpy.data.cameras.new('Canonical orthographic camera')
    camera_data.type = 'ORTHO'
    camera_data.ortho_scale = cal['orthographic_scale']
    camera = bpy.data.objects.new('Canonical orthographic camera', camera_data)
    scene.collection.objects.link(camera)
    scene.camera = camera
    for view in cal['views']:
        if args.views and view['id'] not in args.views: continue
        camera.matrix_world = Matrix(view['camera_to_world'])
        camera.data.clip_start, camera.data.clip_end = view['clip_start'],view['clip_end']
        for style in ['textured','clay']:
            folder = out/style
            folder.mkdir(exist_ok=True)
            bpy.context.view_layer.material_override = clay if style=='clay' else None
            scene.render.filepath = str(folder/(view['id']+'.png'))
            bpy.ops.render.render(write_still=True)
            audit['renders'].append({'view':view['id'], 'style':style, 'path':str(folder/(view['id']+'.png'))})
            dump(out/'project_audit.json', audit)
        print('CANONICAL_VIEW_COMPLETE', view['id'], flush=True)
    audit['all_twelve_renders_completed'] = len(audit['renders']) == 12
    dump(out/'project_audit.json', audit)
    print('CANONICAL_CAPTURE_COMPLETE', flush=True)


if __name__ == '__main__':
    main()
