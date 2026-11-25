"""Build shared inputs and completed model reports from an audited allowlist."""
import argparse
import hashlib
import html
import json
from pathlib import Path
import re
import shutil
import zipfile

from PIL import Image
from scoring import make_reports

FRAMES = list(range(0, 100, 11))
SLUG = 'phoenix-reconstruction'
REPORTS = ['results', 'execution', 'analysis']


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', required=True, type=Path, help='Local phoenix-multiview-v1 archive')
    parser.add_argument('--repo', type=Path, default=Path(__file__).resolve().parents[2])
    args = parser.parse_args()
    source = args.source.resolve()
    here = Path(__file__).resolve().parent
    site = args.repo / 'docs' / SLUG
    models = json.loads((here / 'models.json').read_text(encoding='utf-8'))
    assert models and len({m['id'] for m in models}) == len(models)
    assert all(re.fullmatch(r'[a-z0-9-]+', m['id']) for m in models)
    candidate = source / 'runs' / models[0]['run'] / 'workspace/candidate'

    def copy(src, rel):
        dst = site / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dst)

    def write_json(rel, data):
        dst = site / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

    def poster(src, dest, quality=92):
        rgba = Image.open(src).convert('RGBA')
        bg = Image.new('RGBA', rgba.size, (32, 38, 48, 255))
        bg.alpha_composite(rgba)
        bg.convert('RGB').save(site / dest, quality=quality)

    input_zip = source / 'phoenix-agent-input-v1.zip'
    with zipfile.ZipFile(input_zip) as z:
        names = z.namelist()
        assert len(names) == 15
        assert not any(n.lower().endswith(('.png', '.blend', '.glb')) for n in names)
    copy(input_zip, 'assets/agent-input.zip')
    for name in ['TASK.md', 'cameras.json', 'timeline.json', 'scene_setup.json', 'ASSET-ATTRIBUTION.txt', 'INPUT-USE.md']:
        copy(candidate / name, 'assets/' + name)
    for name in ['air_long.wav', 'air_low.wav', 'feather_rustle.wav', 'sweep_broad.wav', 'sweep_light.wav', 'SOURCE.txt']:
        copy(candidate / 'audio' / name, 'assets/audio/' + name)
    for view in ['I1', 'I2', 'I3']:
        copy(candidate / f'reference/{view}.mp4', f'assets/reference/{view}.mp4')
        poster(source / f'public/reference/{view}/0000.png', f'assets/reference/{view}-poster.jpg', quality=90)
    copy(source / 'private/target/T1.mp4', 'assets/evaluation/T1-reference.mp4')
    poster(source / 'private/target/T1/0000.png', 'assets/evaluation/reference-poster.jpg')

    rows, options = [], []
    panels = {name: [] for name in REPORTS}
    for model in models:
        mid = model['id']
        run = source / 'runs' / model['run']
        evaluation = run / 'evaluation'
        dest = f'results/{mid}'
        content = here / 'models' / mid
        reports = make_reports(evaluation)
        score = reports['score.json']
        metric = reports['image_metrics.json']
        geom = json.loads((evaluation / 'geometry_metrics.json').read_text(encoding='utf-8'))
        assert score['frames'] == FRAMES
        assert score['model'] == model['model'] and score['effort'] == model['effort']
        scores = score['scores']
        assert all(isinstance(scores[k], (int, float)) for k in ['view_coverage', 'geometry', 'appearance', 'audio', 'full_total_100'])
        assert abs(sum(scores[k] for k in ['view_coverage', 'geometry', 'appearance', 'audio']) - scores['full_total_100']) < 1e-9
        for name in ['T1.mp4', 'scene.blend', 'README.md']:
            copy(run / 'remote-delivery' / name, f'{dest}/{name}')
        copy(run / model['delivery_archive'], f'{dest}/delivery.zip')
        for name, data in reports.items():
            write_json(f'{dest}/{name}', data)
        for name in ['geometry_metrics.json',
                     'evaluation-sampling.json', 'render-route-audit.json', 'geometry-self-control.json',
                     'alpha-sensitivity.json', 'gemini-neon-audio/audio-score.json']:
            copy(evaluation / name, f'{dest}/{name}')
        Image.open(evaluation / 'preview-first-frame.png').convert('RGB').save(site / dest / 'poster.jpg', quality=92)
        copy(evaluation / 'comparison-sheet.jpg', f'{dest}/comparison/comparison-sheet.jpg')
        observations = json.loads((content / 'observations.json').read_text(encoding='utf-8'))
        frame_data = []
        for frame in FRAMES:
            raw = Image.open(evaluation / f'comparisons/{frame:04d}.jpg').convert('RGB')
            pair = Image.new('RGB', (1256, 582))
            pair.paste(raw.crop((280, 77, 908, 659)), (0, 0))
            pair.paste(raw.crop((1560, 77, 2188, 659)), (628, 0))
            pair.save(site / f'{dest}/comparison/frame-{frame:02d}.webp', quality=93)
            row = metric['frames'][str(frame)]
            frame_data.append({'frame': frame, 'seconds': frame / 30,
                               'F1': geom['frames'][str(frame)]['input_visible_surface']['0.005']['f1'],
                               'IoU': {v: row[v]['IoU'] for v in ['I1', 'I2', 'I3', 'T1']},
                               'observation': observations[str(frame)], **row['T1']['appearance']})
        write_json(f'{dest}/comparison/frame-data.json', frame_data)
        esc = html.escape
        label = f"{model['label']} · {model['effort']} · {model['framework']}"
        rows.append(f'<tr data-result-model="{mid}"><th scope="row"><a href="#model-{mid}" data-select-model="{mid}">{esc(model["label"])}</a></th>'
                    f'<td>{esc(model["effort"])}</td><td>{esc(model["framework"])}</td>'
                    f'<td>{scores["view_coverage"]:.2f}</td><td>{scores["geometry"]:.2f}</td><td>{scores["appearance"]:.2f}</td><td>{scores["audio"]:.2f}</td>'
                    f'<td><strong class="score-value">{scores["full_total_100"]:.2f}</strong></td></tr>')
        options.append(f'<option value="{mid}">{esc(label)}</option>')
        for name in REPORTS:
            body = (content / f'{name}.html').read_text(encoding='utf-8')
            if mid != 'astra62-xhigh':
                for old_id in re.findall(r'(?<![\w-])id="([^"]+)"', body):
                    body = body.replace(f'id="{old_id}"', f'id="{mid}-{old_id}"')
                    body = body.replace(f'href="#{old_id}"', f'href="#{mid}-{old_id}"')
            anchor = f'model-{mid}' if name == 'results' else f'{name}-{mid}'
            heading = '' if name == 'results' else f'<h3 class="model-section-label">{esc(label)}</h3>'
            panels[name].append(f'<article class="model-panel" id="{anchor}" data-model-panel="{mid}" aria-label="{esc(label)}">{heading}\n{body}\n</article>')

    for name in ['style.css', 'app.js', 'ATTRIBUTION.md']:
        copy(here / name, name)
    page = (here / 'index.html').read_text(encoding='utf-8')
    page = page.replace('<!--TASK_TEXT-->', html.escape((candidate / 'TASK.md').read_text(encoding='utf-8')))
    page = page.replace('<!--MODEL_ROWS-->', ''.join(rows)).replace('<!--MODEL_OPTIONS-->', ''.join(options))
    for name in REPORTS:
        page = page.replace(f'<!--MODEL_{name.upper()}-->', '\n'.join(panels[name]))
    (site / 'index.html').write_text(page, encoding='utf-8')
    # These are only the previously generated Astra comparisons, now owned by its result.
    for name in [f'frame-{f:02d}.webp' for f in FRAMES] + ['frame-data.json', 'comparison-sheet.jpg']:
        (site / 'assets/evaluation' / name).unlink(missing_ok=True)
    manifest = [{'file': p.relative_to(site).as_posix(), 'bytes': p.stat().st_size,
                 'sha256': hashlib.sha256(p.read_bytes()).hexdigest()}
                for p in sorted(site.rglob('*')) if p.is_file() and p.name != 'manifest.json']
    write_json('manifest.json', {'case': SLUG, 'files': manifest})
    print(json.dumps({'models': len(models), 'files': len(manifest), 'total_bytes': sum(r['bytes'] for r in manifest)}))


if __name__ == '__main__':
    main()
