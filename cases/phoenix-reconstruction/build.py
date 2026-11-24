"""Build the public case from an explicit, audited allowlist. Requires Pillow."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import zipfile

from PIL import Image

FRAMES = list(range(0, 100, 11))
SLUG = 'phoenix-reconstruction'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', required=True, type=Path, help='Local phoenix-multiview-v1 archive')
    parser.add_argument('--repo', type=Path, default=Path(__file__).resolve().parents[2])
    args = parser.parse_args()
    source = args.source.resolve()
    run = source / 'runs/astra62-xhigh-codex-gpu01'
    evaluation = run / 'evaluation'
    candidate = run / 'workspace/candidate'
    site = args.repo / 'docs' / SLUG
    here = Path(__file__).resolve().parent
    manifest = []

    def copy(src, rel):
        dst = site / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dst)
        manifest.append({'file': rel, 'bytes': dst.stat().st_size,
                         'sha256': hashlib.sha256(dst.read_bytes()).hexdigest()})

    def write_json(rel, data):
        dst = site / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

    # Only reviewed inputs, immutable delivery and final metric reports are copied.
    input_zip = source / 'phoenix-agent-input-v1.zip'
    with zipfile.ZipFile(input_zip) as z:
        names = z.namelist()
        assert len(names) == 15
        assert not any(n.lower().endswith(('.png', '.blend', '.glb')) for n in names)
    copy(input_zip, 'assets/agent-input.zip')
    for name in ['TASK.md', 'cameras.json', 'timeline.json', 'scene_setup.json',
                 'ASSET-ATTRIBUTION.txt', 'INPUT-USE.md']:
        copy(candidate / name, 'assets/' + name)
    for name in ['air_long.wav', 'air_low.wav', 'feather_rustle.wav', 'sweep_broad.wav',
                 'sweep_light.wav', 'SOURCE.txt']:
        copy(candidate / 'audio' / name, 'assets/audio/' + name)
    for view in ['I1', 'I2', 'I3']:
        copy(candidate / f'reference/{view}.mp4', f'assets/reference/{view}.mp4')
        rgba = Image.open(source / f'public/reference/{view}/0000.png').convert('RGBA')
        bg = Image.new('RGBA', rgba.size, (32, 38, 48, 255))
        bg.alpha_composite(rgba)
        bg.convert('RGB').save(site / f'assets/reference/{view}-poster.jpg', quality=90)
    copy(run / 'remote-delivery/T1.mp4', 'results/astra62-xhigh/T1.mp4')
    copy(run / 'remote-delivery/scene.blend', 'results/astra62-xhigh/scene.blend')
    copy(run / 'remote-delivery/README.md', 'results/astra62-xhigh/README.md')
    copy(run / 'astra62-xhigh-codex-phoenix-delivery.zip', 'results/astra62-xhigh/delivery.zip')
    for name in ['score.json', 'geometry_metrics.json', 'image_metrics.json', 'PROTOCOL.json',
                 'evaluation-sampling.json', 'render-route-audit.json', 'geometry-self-control.json',
                 'alpha-sensitivity.json', 'gemini-neon-audio/audio-score.json']:
        copy(evaluation / name, 'results/astra62-xhigh/' + name)
    # Reference target is presented only in the completed evaluation, never in the input.
    copy(source / 'private/target/T1.mp4', 'assets/evaluation/T1-reference.mp4')
    Image.open(evaluation / 'preview-first-frame.png').convert('RGB').save(
        site / 'results/astra62-xhigh/poster.jpg', quality=92)
    ref = Image.open(source / 'private/target/T1/0000.png').convert('RGBA')
    bg = Image.new('RGBA', ref.size, (32, 38, 48, 255)); bg.alpha_composite(ref)
    bg.convert('RGB').save(site / 'assets/evaluation/reference-poster.jpg', quality=92)
    copy(evaluation / 'comparison-sheet.jpg', 'assets/evaluation/comparison-sheet.jpg')
    metric = json.loads((evaluation / 'image_metrics.json').read_text(encoding='utf-8'))
    geom = json.loads((evaluation / 'geometry_metrics.json').read_text(encoding='utf-8'))
    score = json.loads((evaluation / 'score.json').read_text(encoding='utf-8'))
    assert score['frames'] == FRAMES
    assert abs(score['scores']['full_total_100'] - 39.18651588184098) < 1e-12
    frame_data = []
    for frame in FRAMES:
        raw = Image.open(evaluation / f'comparisons/{frame:04d}.jpg').convert('RGB')
        # Same crop and scale for both halves; this is display-only, not a metric input.
        left = raw.crop((280, 77, 908, 659))
        right = raw.crop((1560, 77, 2188, 659))
        pair = Image.new('RGB', (1256, 582)); pair.paste(left, (0, 0)); pair.paste(right, (628, 0))
        pair.save(site / f'assets/evaluation/frame-{frame:02d}.webp', quality=93)
        row = metric['frames'][str(frame)]
        frame_data.append({'frame': frame, 'seconds': frame / 30,
                           'F1': geom['frames'][str(frame)]['input_visible_surface']['0.005']['f1'],
                           'IoU': {v: row[v]['IoU'] for v in ['I1', 'I2', 'I3', 'T1']},
                           **row['T1']['appearance']})
    write_json('assets/evaluation/frame-data.json', frame_data)
    for name in ['index.html', 'style.css', 'app.js', 'ATTRIBUTION.md']:
        copy(here / name, name)
    # Display the exact approved brief; no solver hints are inserted.
    page = (site / 'index.html').read_text(encoding='utf-8')
    import html
    page = page.replace('<!--TASK_TEXT-->', html.escape((candidate / 'TASK.md').read_text(encoding='utf-8')))
    (site / 'index.html').write_text(page, encoding='utf-8')
    # Manifest hashes are calculated after all transformations.
    manifest = [{'file': p.relative_to(site).as_posix(), 'bytes': p.stat().st_size,
                 'sha256': hashlib.sha256(p.read_bytes()).hexdigest()}
                for p in sorted(site.rglob('*')) if p.is_file() and p.name != 'manifest.json']
    write_json('manifest.json', {'case': SLUG, 'files': manifest})
    print(json.dumps({'site': str(site), 'files': len(manifest),
                      'total_bytes': sum(r['bytes'] for r in manifest)}))


if __name__ == '__main__':
    main()
