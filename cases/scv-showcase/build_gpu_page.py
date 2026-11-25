"""Package the completed GPU SCV delivery and accepted reviews; never runs a solver.

Usage: python cases/scv-showcase/build_gpu_page.py --run /path/to/astra62-xhigh-gpu-fresh01
Requires Pillow. Original private experiment records are read locally, not copied wholesale.
"""
import argparse
import hashlib
import json
import mimetypes
import shutil
import zipfile
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageOps

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SITE = ROOT / 'docs/scv-showcase'
VIEWS = {'front': '正面', 'back': '背面', 'left': '机甲左侧', 'right': '机甲右侧', 'top': '顶面', 'bottom': '底面'}


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False) + '\n', encoding='utf-8')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def font(size):
    for name in ['C:/Windows/Fonts/msyh.ttc', '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc', 'DejaVuSans.ttf']:
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            pass
    return ImageFont.load_default(size=size)


def flattened(path):
    with Image.open(path) as original:
        original = original.convert('RGBA')
        canvas = Image.new('RGBA', original.size, (128, 128, 128, 255))
        canvas.alpha_composite(original)
        return canvas.convert('RGB')


def bundle(folder, archive):
    with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as output:
        for path in sorted(folder.rglob('*')):
            if path.is_file() and '__pycache__' not in path.parts and path.suffix != '.pyc':
                info = zipfile.ZipInfo(path.relative_to(folder).as_posix(), (2026, 11, 24, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = 0o644 << 16
                output.writestr(info, path.read_bytes())
    if archive.stat().st_size >= 100 * 1024**2:
        raise ValueError(f'{archive.name} exceeds the GitHub single-file limit')


def strip_legacy_distance(value):
    if isinstance(value, dict):
        return {key: strip_legacy_distance(item) for key, item in value.items()
                if 'lpips' not in key.lower() and key.lower() not in {'torch', 'torchvision'}}
    if isinstance(value, list):
        return [strip_legacy_distance(item) for item in value]
    return value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', required=True, type=Path)
    parser.add_argument('--scores-only', action='store_true', help='Update scores/package/template while retaining identical delivery media')
    args = parser.parse_args()
    run = args.run.resolve()
    delivery = run / 'remote-delivery'
    metrics = run / 'evaluation/static60/metrics'
    static = read(run / 'evaluation/static60/STATIC-COMPARISON.json')
    experiment = read(run / 'EXPERIMENT-RESULT.json')
    detail = read(run / 'evaluation/detail-review/detail-restoration-review.json')
    music = read(run / 'evaluation/av-review/music/music-review-gemini.json')
    sfx = read(run / 'evaluation/av-review/sfx/sfx-review-gemini.json')
    for review in [detail, music, sfx]:
        assert review['assessment_status'] == 'complete'
    for dimension in detail['dimensions']:
        assert dimension['confirmed_error_count'] == len(dimension['deductions'])
        assert dimension['score'] == max(0, 10 - 5 * dimension['confirmed_error_count'])
    assert detail['total_score'] == sum(d['score'] for d in detail['dimensions'])
    for review in [music, sfx]:
        assert len(review['items']) == 5
        assert review['score'] == sum(item['score'] for item in review['items'])

    assets = SITE / 'assets'
    if not args.scores_only:
        for filename in ['asset.blend', 'showcase.mp4']:
            shutil.copy2(delivery / filename, assets / filename)
        assert sha(assets / 'showcase.mp4') == experiment['video_checks']['sha256']
        shutil.copy2(delivery / 'README.md', assets / 'delivery-README.md')
        shutil.copy2(run / 'analysis/video-grounded-review/frames/frame_0480.jpg', assets / 'poster.jpg')
        bundle(delivery, assets / 'delivery.zip')

        for view, label in VIEWS.items():
            reconstruction = assets / f'reconstruction/{view}.png'
            shutil.copy2(metrics / f'canonical_capture/textured/{view}.png', reconstruction)
            canvas = Image.new('RGB', (1280, 688), '#f4f3ee')
            draw = ImageDraw.Draw(canvas)
            draw.text((20, 10), f'{label} · 输入参考', font=font(20), fill='#172c32')
            draw.text((660, 10), f'{label} · GPU 重建', font=font(20), fill='#172c32')
            for x, image in [(0, flattened(assets / f'reference/{view}.png')), (640, flattened(reconstruction))]:
                canvas.paste(image.resize((640, 640), Image.Resampling.LANCZOS), (x, 48))
            canvas.save(assets / f'comparison/{view}.webp', quality=90)
        overview = Image.new('RGB', (1280, 1032), '#f4f3ee')
        for index, view in enumerate(VIEWS):
            with Image.open(assets / f'comparison/{view}.webp') as pair:
                overview.paste(pair.resize((640, 344)), ((index % 2) * 640, (index // 2) * 344))
        overview.save(assets / 'comparison/six-views.webp', quality=90)

        evidence = Image.new('RGB', (1400, 1200), '#f4f3ee')
        draw = ImageDraw.Draw(evidence)
        rows = [('肩侧工具挂载', (150, 170, 390, 590)), ('三爪工具造型', (75, 710, 390, 1010)), ('腰间图案标识', (540, 700, 745, 980))]
        ref = flattened(assets / 'reference/front.png')
        result = flattened(assets / 'reconstruction/front.png')
        for index, (label, crop) in enumerate(rows):
            y = index * 400
            draw.text((22, y + 12), label, font=font(26), fill='#172c32')
            for x, image, heading in [(20, ref, '输入参考'), (720, result, 'GPU 重建')]:
                draw.text((x, y + 52), heading, font=font(20), fill='#166f68')
                image = ImageOps.contain(image.crop(crop), (660, 300), Image.Resampling.LANCZOS)
                evidence.paste(image, (x + (660-image.width)//2, y+90+(300-image.height)//2))
        evidence.save(assets / 'evidence/detail-restoration.jpg', quality=94)

    # Publish reviewed scoring fields, never request/response envelopes or private host metadata.
    public_detail = {key: detail[key] for key in ['rubric_version', 'judge_model', 'assessment_status', 'total_score', 'maximum', 'dimensions']}
    public_music = {key: music[key] for key in ['judge_model', 'assessment_status', 'score', 'maximum']}
    public_music['items'] = [{key: item[key] for key in ['id', 'criterion', 'score']} for item in music['items']]
    public_music['summary'] = '乐句与段落组织、能量呼应、展示节奏、选段衔接及首尾完整五项均满足。'
    public_sfx = {key: sfx[key] for key in ['judge_model', 'assessment_status', 'score', 'maximum']}
    public_sfx['items'] = [{key: item[key] for key in ['id', 'score', 'evidence', 'reason']} for item in sfx['items']]
    public_sfx['confirmed_events'] = [event for event in sfx['candidate_checks'] if event.get('confirmation') == 'sfx']
    for filename, data in [('detail-restoration-review.json', public_detail), ('music-review.json', public_music), ('sfx-review.json', public_sfx)]:
        write(SITE / 'review' / filename, data)

    scores = {'structure': static['new_scores']['structure_30'], 'appearance': 30 * min(1, max(0, static['raw_image_means']['foreground_union_SSIM'])), 'detail_restoration': detail['total_score'], 'music': music['score'], 'sfx': sfx['score']}
    scores['total'] = sum(scores.values())
    model = {
        'case': 'scv-showcase', 'experiment': experiment['experiment'], 'model': experiment['model'],
        'model_display': 'Astra 6.2', 'framework': 'Codex', 'reasoning_effort': 'xhigh',
        'scores': scores, 'weights': {'structure': 30, 'appearance': 30, 'detail_restoration': 30, 'music': 5, 'sfx': 5},
        'raw_metrics': {'F1_tolerance_reference_diagonal_0_5_percent': static['raw_visible_F1']['fscore'], 'six_view_silhouette_IoU': static['raw_image_means']['silhouette_IoU'], 'foreground_union_SSIM': static['raw_image_means']['foreground_union_SSIM']},
        'detail_criteria': [{k: d[k] for k in ['id', 'name', 'maximum', 'deduction_per_error', 'confirmed_error_count', 'score']} for d in detail['dimensions']],
        'detail_judge': detail['judge_model'], 'audio_visual_judge': music['judge_model'],
        'engineering_gate': static['automatic_engineering_gate'], 'engineering_weight': 0,
        'runtime': {'elapsed_seconds': experiment['elapsed_seconds'], 'tool_calls': experiment['tool_calls'], 'responses': experiment['responses'], 'time_limit_seconds': None, 'tool_call_limit': None, 'cpu': 4, 'memory_gib': 8, 'gpu': 'RTX 4090 D, 24 GB', 'platform': 'Linux', 'codex_version': experiment['codex_version'], 'blender_version': '5.3.0'},
        'fresh_context': True, 'starts_from_empty_workspace': True, 'prior_outputs_or_feedback_provided': False,
        'render_route': {'backend': 'Cycles CUDA', 'samples': 24, 'gpu_denoising': True, 'native_3d_frames': 648, 'sparse_reprojection_or_video_interpolation': False},
        'delivery': {'video': 'assets/showcase.mp4', 'poster': 'assets/poster.jpg', 'asset': 'assets/asset.blend', 'archive': 'assets/delivery.zip', 'width': 1600, 'height': 900, 'fps': 24, 'video_frame_count': 648, 'video_duration_seconds': 27.0, 'audio_sample_rate': 48000, 'audio_channels': 2, 'video_sha256': sha(assets/'showcase.mp4')}
    }
    write(SITE / 'results.json', {'protocol_version': 'scv-showcase-ssim-v3', 'models': [model], 'scoring_method': 'scoring-method.md', 'scoring_reference': 'assets/reference-model.json'})

    package = HERE / 'verification-v3'
    package.mkdir(exist_ok=True)
    shutil.copy2(HERE / 'SCORING.md', package / 'SCORING.md')
    package_scoring = package / 'SCORING.md'
    package_scoring.write_text(package_scoring.read_text(encoding='utf-8').replace('../../docs/scv-showcase/', 'https://vibrant700.github.io/omniale/scv-showcase/'), encoding='utf-8')
    for filename in ['surface_metrics.json', 'image_metrics.json']:
        data = strip_legacy_distance(read(metrics / filename))
        if filename == 'surface_metrics.json':
            # Full evaluator output includes machine-local file paths. Keep numeric metric fields only.
            data = {'fscore': static['raw_visible_F1']['fscore'], 'precision': static['raw_visible_F1']['precision'], 'recall': static['raw_visible_F1']['recall'], 'threshold_world_units': static['raw_visible_F1']['threshold_world_units']}
        write(package / 'results' / filename, data)
    for path in (SITE / 'review').glob('*.json'):
        shutil.copy2(path, package / 'results' / path.name)
    write(package / 'results/expected-score.json', {'scores': scores})
    bundle(package, assets / 'scoring-verification-v3.zip')
    shutil.copy2(HERE / 'gpu-page.html', SITE / 'index.html')

    manifest = []
    for path in sorted(assets.rglob('*')):
        if path.is_file():
            manifest.append({'path': path.relative_to(SITE).as_posix(), 'mime': mimetypes.guess_type(path.name)[0] or 'application/octet-stream', 'bytes': path.stat().st_size, 'sha256': sha(path)})
    write(SITE / 'assets-manifest.json', manifest)
    print(json.dumps({'total': scores['total'], 'display_total': f'{scores["total"]:.2f}', 'delivery_zip_bytes': (assets/'delivery.zip').stat().st_size, 'asset_count': len(manifest)}, ensure_ascii=False))


if __name__ == '__main__':
    main()
