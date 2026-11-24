"""Reproduce fixed-camera SCV geometry/image metrics from two Blender assets.

The agent input directory supplies exact reference RGBA images, cameras and
scene setup. The reference Blender asset supplies geometry only. Engineering
checks are a delivery gate and are never added to the quality score.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess

from evaluate_images import dump, image_metrics

HERE = Path(__file__).resolve().parent


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024*1024), b''):
            h.update(chunk)
    return h.hexdigest()


def run_blender(blender, script, params, log):
    command = [str(blender), '--background', '--factory-startup', '--disable-autoexec',
               '--python-exit-code', '1', '--python', str(script), '--', *map(str, params)]
    with Path(log).open('w', encoding='utf-8') as stream:
        result = subprocess.run(command, stdout=stream, stderr=subprocess.STDOUT, cwd=HERE)
    if result.returncode:
        raise RuntimeError(f'Blender returned {result.returncode}; see {log}')


def clip01(value):
    return min(1., max(0., float(value)))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--reference-blend', required=True)
    p.add_argument('--submission-blend', required=True)
    p.add_argument('--public-root', required=True)
    p.add_argument('--blender', default='blender', help='Blender executable (recorded evaluation used Blender 5.3)')
    p.add_argument('--output', required=True, help='New output directory; must be empty or absent')
    p.add_argument('--submission-root', help='Optional complete delivery root copied before evaluation; defaults to the submission .blend parent')
    p.add_argument('--torch-home', help='PyTorch cache containing official AlexNet weights')
    args = p.parse_args()
    if args.torch_home:
        os.environ['TORCH_HOME'] = str(Path(args.torch_home).resolve())
    ref, sub, public = (Path(x).resolve() for x in
                        (args.reference_blend, args.submission_blend, args.public_root))
    out = Path(args.output).resolve()
    root = Path(args.submission_root).resolve() if args.submission_root else sub.parent
    if not ref.is_file() or not sub.is_file():
        p.error('Both Blender asset files must exist')
    try:
        sub_relative = sub.relative_to(root)
    except ValueError:
        p.error('--submission-blend must be inside --submission-root')
    if out.exists() and any(out.iterdir()):
        p.error('--output must be empty or absent')
    if out == root or root in out.parents:
        p.error('--output must be outside the submission root (which is copied)')
    for name in ('cameras.json', 'scene_setup.json'):
        if not (public/name).is_file():
            p.error(f'Missing public input configuration: {name}')
    out.mkdir(parents=True, exist_ok=True)
    before = {f.relative_to(root).as_posix(): sha(f) for f in root.rglob('*') if f.is_file()}
    relocated = out/'relocated_submission'
    shutil.copytree(root, relocated)
    source_hashes = {f.name: sha(f) for f in (Path(__file__), HERE/'evaluate_images.py',
                      HERE/'capture_asset_blender.py', HERE/'surface_metrics_blender.py')}
    dump(out/'input_integrity.json', {
        'reference_blend_sha256': sha(ref), 'submission_files': before,
        'cameras_sha256': sha(public/'cameras.json'),
        'scene_setup_sha256': sha(public/'scene_setup.json'),
        'reference_images': {f.relative_to(public).as_posix(): sha(f) for f in (public/'reference').glob('*.png')},
        'evaluator_hashes': source_hashes,
    })
    reference_capture, capture = out/'reference_capture', out/'canonical_capture'
    run_blender(args.blender, HERE/'capture_asset_blender.py',
        ['--blend', ref, '--output', reference_capture, '--public-root', public, '--mesh-only'],
        out/'reference_capture.log')
    try:
        run_blender(args.blender, HERE/'capture_asset_blender.py',
            ['--blend', relocated/sub_relative, '--output', capture, '--public-root', public],
            out/'canonical_capture.log')
    except RuntimeError as exc:
        dump(out/'delivery_gate.json', {'passed': False, 'reason': str(exc),
            'engineering_is_not_a_scored_component': True})
        raise
    audit = json.loads((capture/'project_audit.json').read_text(encoding='utf-8'))
    gate = {
        'passed': bool(audit['has_renderable_mesh'] and
            audit['resources_resolved_in_relocated_copy'] and audit['all_twelve_renders_completed']),
        'has_renderable_mesh': audit['has_renderable_mesh'],
        'resources_resolved_in_relocated_copy': audit['resources_resolved_in_relocated_copy'],
        'canonical_views_rendered': 6, 'engineering_is_not_a_scored_component': True,
        'note': 'Automated reopen/resource/render checks. Editability and camera-facing impostors are reviewed separately using the asset audit and clay views.',
    }
    dump(out/'delivery_gate.json', gate)
    run_blender(args.blender, HERE/'surface_metrics_blender.py',
        ['--reference', reference_capture/'mesh.npz', '--submission', capture/'mesh.npz',
         '--cameras', public/'cameras.json', '--output', out/'surface_metrics.json', '--samples', '50000'],
        out/'surface_metrics.log')
    im = image_metrics(public, capture, out/'image_metrics.json')
    surface = json.loads((out/'surface_metrics.json').read_text(encoding='utf-8'))
    f1 = surface['six_input_view_visible_samples']['fscore_by_reference_diagonal_fraction']['0.005']['fscore']
    means = im['mean']['textured']
    structure = None if f1 is None else 15*float(f1) + 15*means['silhouette_IoU']
    appearance = 15*(clip01(means['foreground_union_SSIM']) +
                     1-clip01(means['foreground_union_LPIPS_alex_spatial']))
    after = {f.relative_to(root).as_posix(): sha(f) for f in root.rglob('*') if f.is_file()}
    if before != after:
        raise RuntimeError('Submission changed during evaluation')
    if source_hashes != {f.name: sha(f) for f in (Path(__file__), HERE/'evaluate_images.py',
                         HERE/'capture_asset_blender.py', HERE/'surface_metrics_blender.py')}:
        raise RuntimeError('Evaluator changed during evaluation')
    result = {'delivery_gate': gate, 'mean_image_metrics': im['mean'],
              'visible_surface_metrics': surface['six_input_view_visible_samples'],
              'structure_30': structure, 'appearance_30': appearance,
              'quality_subtotal_60': None if structure is None else structure+appearance,
              'source_unchanged': True, 'evaluator_hashes': source_hashes}
    dump(out/'raw_result.json', result)
    print(json.dumps({k: result[k] for k in ('structure_30', 'appearance_30', 'quality_subtotal_60')}))


if __name__ == '__main__':
    main()
