"""Blender 5.3 entry point. See README.md for build / render commands."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

import bpy
import numpy as np
from mathutils import Matrix, Vector

ROOT = Path(__file__).resolve().parent
ASSETS = ROOT / "assets"
CAL = json.loads((ASSETS / "cameras.json").read_text())["cameras"]
AXIS = np.array([[1, 0, 0], [0, 0, 1], [0, -1, 0]], dtype=np.float64)
ORIGIN = np.array([0, 0, 1065], dtype=np.float64)


def xyz(points):
    return np.asarray((np.asarray(points) - ORIGIN) @ AXIS.T * .001, dtype="f")


def collection(name):
    col = bpy.data.collections.new(name)
    bpy.context.scene.collection.children.link(col)
    return col


def surface(col):
    data = np.load(ASSETS / "performance.npz")
    base, delta = data["basis"], data["delta"]
    nr, nc = base.shape[:2]
    rings, columns = np.meshgrid(np.arange(nr - 1), np.arange(nc), indexing="ij")
    i, j = rings.ravel(), columns.ravel()
    k = (j + 1) % nc
    faces = np.stack((i * nc + j, (i + 1) * nc + j,
                      (i + 1) * nc + k, i * nc + k), axis=1)
    mesh = bpy.data.meshes.new("Capture surface | periodic quad topology")
    mesh.from_pydata(xyz(base).reshape(-1, 3).tolist(), [], faces.tolist())
    mesh.update()
    mesh.polygons.foreach_set("use_smooth", np.ones(len(faces), dtype=bool))
    ob = bpy.data.objects.new("Performer | head, neck & shoulders", mesh)
    col.objects.link(ob)
    rows = data["rows"] / float(data["atlas_rows"])
    uv = np.stack((np.stack([j, j, j+1, j+1], axis=1) / nc,
                   1-np.stack([rows[i], rows[i+1], rows[i+1], rows[i]], axis=1)), axis=-1)
    mesh.uv_layers.new(name="Capture atlas").data.foreach_set("uv", uv.astype("f").ravel())
    mat = bpy.data.materials.new("Skin & wardrobe | observed studio radiance")
    mat.diffuse_color = (.12, .115, .065, 1)
    mat.use_nodes = True
    tree = mat.node_tree
    tree.nodes.clear()
    uvnode = tree.nodes.new("ShaderNodeUVMap")
    uvnode.uv_map = "Capture atlas"
    uvnode.location = (-600, 40)
    img = bpy.data.images.load(str(ASSETS / "radiance/capture_0001.jpg"))
    img.name = "Three-view radiance | 104 samples"
    img.source = "SEQUENCE"
    img.filepath = "//assets/radiance/capture_0001.jpg"
    node = tree.nodes.new("ShaderNodeTexImage")
    node.image = img
    node.image_user.frame_start = 1
    node.image_user.frame_duration = len(delta)
    node.image_user.use_auto_refresh = True
    node.interpolation = "Linear"
    node.location = (-360, 40)
    node.label = "Synchronized multiview atlas"
    sh = tree.nodes.new("ShaderNodeEmission")
    sh.location = (-50, 40)
    sh.label = "Captured illumination"
    out = tree.nodes.new("ShaderNodeOutputMaterial")
    out.location = (210, 40)
    tree.links.new(uvnode.outputs["UV"], node.inputs["Vector"])
    tree.links.new(node.outputs["Color"], sh.inputs["Color"])
    tree.links.new(sh.outputs[0], out.inputs["Surface"])
    tree.nodes.active = node
    mesh.materials.append(mat)

    ob.shape_key_add(name="Basis | 040434")
    keys = mesh.shape_keys
    keys.name = "Performance | 30 Hz surface samples"
    keys.use_relative = False
    keys.key_blocks[0].interpolation = "KEY_LINEAR"
    for n in range(1, len(delta)):
        sid = CAL[1]["frames"][n]["source_frame_id"]
        key = ob.shape_key_add(name=f"{n+1:03d} | {sid}", from_mix=False)
        co = xyz(base + delta[n].astype("f") * .01).ravel()
        key.data.foreach_set("co", co)
        key.interpolation = "KEY_LINEAR"
    for n, key in enumerate(keys.key_blocks):
        keys.eval_time = key.frame
        keys.keyframe_insert(data_path="eval_time", frame=n+1)
    ob["Reconstruction"] = "Calibrated periodic surface; absolute shape keys; radiance sequence synchronized to frame 1."
    t = np.broadcast_to((np.arange(nc)/nc*2-1)*np.pi, (nr, nc))
    y = base[:, :, 1]
    regions = {"Face": (abs(t-.16) < 1.28) & (y < 78) & (y > -92),
               "Mouth & jaw": (abs(t-.16) < .72) & (y > 0) & (y < 67),
               "Eye band": (abs(t-.16) < .95) & (y < -33) & (y > -64),
               "Ear regions": (abs(t) > 1.17) & (abs(t) < 2.1) & (y < 45) & (y > -28),
               "Cranium": y <= -76, "Neck & shoulders": y >= 75}
    for label, group in regions.items():
        ob.vertex_groups.new(name=label).add(np.flatnonzero(group).tolist(), 1, "REPLACE")
    return ob


def srgb(rgb):
    v = np.array(rgb) / 255
    return tuple(np.where(v <= .04045, v / 12.92, ((v + .055) / 1.055) ** 2.4)) + (1,)


def dark_material(label, rgb, edge):
    m = bpy.data.materials.new(label)
    m.use_nodes = True
    m.diffuse_color = srgb(rgb)
    nt = m.node_tree
    nt.nodes.clear()
    facing = nt.nodes.new("ShaderNodeLayerWeight")
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = srgb(rgb)
    ramp.color_ramp.elements[1].color = srgb(edge)
    em = nt.nodes.new("ShaderNodeEmission")
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    nt.links.new(facing.outputs["Facing"], ramp.inputs[0])
    nt.links.new(ramp.outputs[0], em.inputs[0])
    nt.links.new(em.outputs[0], out.inputs[0])
    for i, node in enumerate([facing, ramp, em, out]):
        node.location = (-520+210*i, 0)
    return m


def block(label, center, dims_xyz, radius, mat, col):
    bpy.ops.mesh.primitive_cube_add(size=1, location=xyz(center))
    ob = bpy.context.object
    ob.name = label
    ob.dimensions = dims_xyz
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    mod = ob.modifiers.new("Rounded upholstery", "BEVEL")
    mod.width, mod.segments = radius, 10
    ob.modifiers.new("Panel normals", "WEIGHTED_NORMAL")
    ob.data.materials.append(mat)
    for cc in list(ob.users_collection):
        cc.objects.unlink(ob)
    col.objects.link(ob)


def stage(col):
    pad = dark_material("Headrest | charcoal upholstery", (8, 10, 9), (18, 22, 21))
    shell = dark_material("Headrest | bound edge", (5, 5, 6), (16, 18, 19))
    block("Headrest | rear shell", (1, 47, 1206), (.202, .043, .121), .02, shell, col)
    block("Headrest | cushion", (1, 46, 1193), (.195, .049, .115), .022, pad, col)
    block("Headrest | mounting stem", (1, 161, 1210), (.034, .026, .19), .008, shell, col)
    # Visible practicals are localized along the measured profile-camera rays.
    # Their depth is not triangulated: use the opposite side of the capture rig.
    m = bpy.data.materials.new("Practicals | photographed diffuser")
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = bpy.data.images.load(str(ASSETS / "diffuser.png"))
    tex.image.filepath = "//assets/diffuser.png"
    em = nt.nodes.new("ShaderNodeEmission")
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    nt.links.new(tex.outputs[0], em.inputs[0])
    nt.links.new(em.outputs[0], out.inputs[0])
    tex.location, em.location, out.location = (-400, 0), (-100, 0), (130, 0)
    for i, x, y in [(0, 35, 443), (0, 154, 439), (0, 86, 150),
                    (0, 84, 330), (2, 290, 439)]:
        c = CAL[i]
        K = np.array(c["K"])
        rt = np.array(c["world_to_camera"])
        rot = rt[:, :3]
        pos = -rot.T @ rt[:, 3]
        ray = np.linalg.solve(K, [x*4, y*4, 1])
        center = pos + rot.T @ (ray * 2130)
        hw = 111 * 2130 / K[0, 0]
        pts = [center + rot.T @ [u*hw, v*hw, 0] for u, v in [(-1, 1), (1, 1), (1, -1), (-1, -1)]]
        mesh = bpy.data.meshes.new("Diffuser")
        mesh.from_pydata(xyz(pts).tolist(), [], [(0, 1, 2, 3)])
        mesh.uv_layers.new().data.foreach_set("uv", [0, 0, 1, 0, 1, 1, 0, 1])
        ob = bpy.data.objects.new(f"Practical | {c['view_id']} {x:03}", mesh)
        col.objects.link(ob)
        ob.data.materials.append(m)


def cameras(captures, outputs):
    for c in CAL:
        name = c["view_id"]
        cam = bpy.data.cameras.new(name + " | calibrated")
        ob = bpy.data.objects.new(name, cam)
        (outputs if name.startswith("T") else captures).objects.link(ob)
        rt = np.array(c["world_to_camera"])
        rot = rt[:, :3]
        mat = np.eye(4)
        mat[:3, :3] = AXIS @ rot.T @ np.diag([1, -1, -1])
        mat[:3, 3] = xyz(-rot.T @ rt[:, 3])
        ob.matrix_world = Matrix(mat.tolist())
        k = np.diag([668/c["width"], 1024/c["height"], 1]) @ np.array(c["K"])
        aspect = k[0, 0]/k[1, 1]
        cam.sensor_fit = "HORIZONTAL"
        cam.sensor_width = 36
        cam.lens = k[0, 0]*36/668
        cam.shift_x = (.5 - k[0, 2]/668)
        cam.shift_y = (k[1, 2]-512)*aspect/668
        cam.clip_start, cam.clip_end, cam.display_size = .025, 7, .085
        cam.dof.use_dof = False
        cam.passepartout_alpha = 1
        ob["pixel_aspect_y_over_x"] = aspect
        ob["K_source"] = np.asarray(c["K"]).ravel().tolist()
        ob["RT_source_mm"] = rt.ravel().tolist()


def activate(scene, camera):
    scene.camera = bpy.data.objects[camera]
    aspect = scene.camera["pixel_aspect_y_over_x"]
    scene.render.pixel_aspect_x = max(1., 1./aspect)
    scene.render.pixel_aspect_y = max(1., aspect)


def build():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    s = bpy.context.scene
    s.name = "Multiface | performance capture"
    s.unit_settings.system = "METRIC"
    s.render.engine = "CYCLES"
    s.cycles.samples = 4
    s.cycles.use_denoising = False
    s.cycles.max_bounces = 0
    s.cycles.pixel_filter_type = "BOX"
    s.render.resolution_x, s.render.resolution_y = 668, 1024
    s.render.resolution_percentage = 100
    s.render.fps, s.render.fps_base = 30, 1
    s.frame_start, s.frame_end = 1, 104
    world = bpy.data.worlds.new("Stage | blackout")
    s.world = world
    world.use_nodes = True
    world.node_tree.nodes.get("Background").inputs["Color"].default_value = srgb((5, 4, 7))
    s.view_settings.view_transform = "Standard"
    s.view_settings.look = "None"
    s.render.dither_intensity = .35
    ob = surface(collection("01 | Performance"))
    stage(collection("02 | Capture stage"))
    cameras(collection("04 | Acquisition cameras"), collection("03 | Delivery cameras"))
    activate(s, "T1")
    seq = s.sequence_editor_create()
    sound = seq.strips.new_sound("Location sound | 48 kHz mono", str(ASSETS / "speech.wav"), channel=1, frame_start=1)
    sound.sound.filepath = "//assets/speech.wav"
    s.render.use_sequencer = False
    s.sync_mode = "AUDIO_SYNC"
    s.render.image_settings.file_format = "PNG"
    s.render.image_settings.color_mode = "RGB"
    s.render.filepath = "//renders/T1/frame_"
    s.frame_set(1)
    bpy.ops.object.select_all(action="DESELECT")
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type == "VIEW_3D":
                space = area.spaces.active
                space.region_3d.view_perspective = "CAMERA"
                space.region_3d.view_camera_zoom = 8
                space.overlay.show_overlays = False
                space.shading.color_type = "TEXTURE"
                space.shading.light = "FLAT"
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/"scene.blend"), compress=True, relative_remap=False)


def device(s, requested):
    if requested != "CPU":
        try:
            pref = bpy.context.preferences.addons["cycles"].preferences
            pref.compute_device_type = "CUDA"
            pref.refresh_devices()
            ok = False
            for dev in pref.devices:
                dev.use = dev.type == "CUDA"
                ok |= bool(dev.use)
            if ok:
                s.cycles.device = "GPU"
                return
        except (TypeError, RuntimeError):
            pass
        if requested == "CUDA":
            raise RuntimeError("Requested Cycles CUDA device was not found")
    s.cycles.device = "CPU"


def render(args):
    s = bpy.context.scene
    if "T1" not in bpy.data.objects:
        bpy.ops.wm.open_mainfile(filepath=str(ROOT / "scene.blend"))
        s = bpy.context.scene
    activate(s, args.camera)
    device(s, args.device)
    out = Path(args.output or ROOT / (args.camera + ".mp4")).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    if args.frame:
        s.frame_set(args.frame)
        s.render.filepath = str(out.with_suffix(".png"))
        bpy.ops.render.render(write_still=True)
        return
    with tempfile.TemporaryDirectory(prefix=args.camera+"_", dir=args.tmp) as tmp:
        s.render.filepath = str(Path(tmp) / "frame_")
        bpy.ops.render.render(animation=True)
        subprocess.run([
            "ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-framerate", "30",
            "-start_number", "1", "-i", str(Path(tmp)/"frame_%04d.png"),
            "-i", str(ASSETS/"speech.wav"), "-map", "0:v", "-map", "1:a",
            "-vf", "setsar=1", "-c:v", "libx264", "-crf", "16", "-preset", "slow",
            "-pix_fmt", "yuv420p", "-threads", "8", "-c:a", "aac", "-b:a", "160k",
            "-ar", "48000", "-ac", "1", "-movflags", "+faststart", str(out)
        ], check=True)


def main():
    parser = argparse.ArgumentParser()
    cmd = parser.add_subparsers(dest="command", required=True)
    cmd.add_parser("build")
    p = cmd.add_parser("render")
    p.add_argument("camera", choices=["T1", "T2"])
    p.add_argument("--output")
    p.add_argument("--tmp", help="Existing directory for temporary rendered frames")
    p.add_argument("--frame", type=int, choices=range(1, 105))
    p.add_argument("--device", choices=["AUTO", "CUDA", "CPU"], default="AUTO")
    args = parser.parse_args(sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else ["build"])
    build() if args.command == "build" else render(args)


if __name__ == "__main__":
    main()
