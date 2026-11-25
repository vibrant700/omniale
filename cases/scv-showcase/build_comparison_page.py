"""Publish both completed GPU submissions and model-specific presentation panels.

python cases/scv-showcase/build_comparison_page.py --sol-run /path/to/sol62-xhigh-gpu-fresh01
Reads sealed delivery and accepted reviews; never invokes a solver or media judge.
"""
import argparse
import copy
import json
import mimetypes
import re
import shutil
from html import escape
from pathlib import Path
from PIL import Image, ImageDraw, ImageOps

from build_gpu_page import HERE, ROOT, SITE, VIEWS, bundle, flattened, font, read, sha, strip_legacy_distance, write

SOL_ID = 'sol62-xhigh'
ASTRA_ID = 'astra62-xhigh'


def section(page, name):
    start = page.index(f'    <section class="section" id="{name}"')
    body = page.index('</div>', page.index('<div class="section-heading">', start)) + 6
    end = page.index('    </section>', body)
    return page[start:end + len('    </section>')], page[body:end]


def normalize_items(review):
    items = review['items']
    return [{'id': key, **value} for key, value in items.items()] if isinstance(items, dict) else items


def public_reviews(folder):
    detail = read(folder / 'detail-restoration-review.json')
    music = read(folder / 'music-review-gemini.json')
    sfx = read(folder / 'sfx-review-gemini.json')
    for review in [detail, music, sfx]:
        assert review['assessment_status'] == 'complete'
    for dim in detail['dimensions']:
        assert dim['confirmed_error_count'] == len(dim['deductions'])
        assert dim['score'] == max(0, 10 - 5 * dim['confirmed_error_count'])
    assert detail['total_score'] == sum(d['score'] for d in detail['dimensions'])
    base = lambda obj: {key: obj[key] for key in ['judge_model', 'assessment_status', 'score', 'maximum']}
    public_detail = {key: detail[key] for key in ['rubric_version', 'judge_model', 'assessment_status', 'total_score', 'maximum', 'dimensions']}
    public_music = base(music)
    public_music['items'] = [{key: item[key] for key in ['id', 'criterion', 'score']} for item in normalize_items(music)]
    public_music['summary'] = '乐句与段落组织、能量呼应、展示节奏、选段衔接及首尾完整五项均满足。'
    public_sfx = base(sfx)
    public_sfx['items'] = [{key: item[key] for key in ['id', 'score', 'evidence', 'reason']} for item in normalize_items(sfx)]
    public_sfx['confirmed_events'] = [event for event in sfx['candidate_checks'] if event['confirmation'] == 'sfx']
    for review in [public_music, public_sfx]:
        assert len(review['items']) == 5 and review['score'] == sum(x['score'] for x in review['items'])
    return public_detail, public_music, public_sfx


def package_sol(run):
    target = SITE / 'assets/models' / SOL_ID
    target.mkdir(parents=True, exist_ok=True)
    delivery = run / 'remote-delivery'
    # Check every delivered file before copying or creating the public ZIP.
    receipt = read(run / 'delivery-manifest.json')
    assert not receipt['symlinks']
    for name, expected in receipt['files'].items():
        path = delivery / name
        assert path.stat().st_size == expected['bytes'] and sha(path) == expected['sha256']
    for name in ['asset.blend', 'showcase.blend', 'showcase.mp4', 'poster.jpg']:
        shutil.copy2(delivery / name, target / name)
    shutil.copy2(delivery / 'README.md', target / 'delivery-README.md')
    bundle(delivery, target / 'delivery.zip')
    for folder in ['comparison', 'reconstruction', 'evidence']:
        (target / folder).mkdir(exist_ok=True)
    for view, label in VIEWS.items():
        rendered = target / f'reconstruction/{view}.png'
        shutil.copy2(run / f'evaluation/static60/metrics/canonical_capture/textured/{view}.png', rendered)
        pair = Image.new('RGB', (1280, 688), '#f4f3ee')
        draw = ImageDraw.Draw(pair)
        draw.text((20, 10), f'{label} · 输入参考', font=font(20), fill='#172c32')
        draw.text((660, 10), f'{label} · Sol 6.2 重建', font=font(20), fill='#172c32')
        for x, image in [(0, flattened(SITE / f'assets/reference/{view}.png')), (640, flattened(rendered))]:
            pair.paste(image.resize((640, 640), Image.Resampling.LANCZOS), (x, 48))
        pair.save(target / f'comparison/{view}.webp', quality=90)
    overview = Image.new('RGB', (1280, 1032), '#f4f3ee')
    for index, view in enumerate(VIEWS):
        with Image.open(target / f'comparison/{view}.webp') as image:
            overview.paste(image.resize((640, 344)), ((index % 2) * 640, (index // 2) * 344))
    overview.save(target / 'comparison/six-views.webp', quality=90)
    evidence = Image.new('RGB', (1400, 1200), '#f4f3ee')
    draw = ImageDraw.Draw(evidence)
    ref = flattened(SITE / 'assets/reference/front.png')
    sol = flattened(target / 'reconstruction/front.png')
    for row, (label, box) in enumerate([('驾驶舱操纵装置', (535, 360, 740, 650)), ('三爪工具造型', (75, 710, 390, 1010)), ('腰间图案标识', (540, 700, 745, 980))]):
        y = row * 400
        draw.text((22, y + 12), label, font=font(26), fill='#172c32')
        for x, image, heading in [(20, ref, '输入参考'), (720, sol, 'Sol 6.2 重建')]:
            draw.text((x, y + 52), heading, font=font(20), fill='#166f68')
            crop = ImageOps.contain(image.crop(box), (660, 300), Image.Resampling.LANCZOS)
            evidence.paste(crop, (x + (660 - crop.width) // 2, y + 90 + (300 - crop.height) // 2))
    evidence.save(target / 'evidence/detail-restoration.jpg', quality=94)
    return target.relative_to(SITE).as_posix()


def render_results(model, detail, review_root):
    scores, delivery, runtime = model['scores'], model['delivery'], model['runtime']
    label = model['model_display']
    duration = f"{delivery['video_duration_seconds']:.2f}".rstrip('0').rstrip('.')
    minutes = int(runtime['elapsed_seconds'] // 60)
    seconds = runtime['elapsed_seconds'] - minutes * 60
    rows = ''.join(f'<tr><th>{escape(d["name"])}</th><td>{d["confirmed_error_count"]} 处</td><td>{d["score"]} / 10</td></tr>' for d in detail['dimensions'])
    project_link = f'<a href="{delivery["project"]}" download>下载展示工程 .blend ↓</a>' if 'project' in delivery else ''
    return f'''
      <p><strong>{label} · 总分 {scores['total']:.2f} / 100。</strong>完成 {delivery['video_frame_count']} 帧 CUDA／Cycles 渲染与有声展示；结构 {scores['structure']:.2f} 分、外观 {scores['appearance']:.2f} 分。关键细节三项均为 0 分；音乐编排与音效对应各得 5 分。</p>
      <div class="table-scroll" tabindex="0" role="region" aria-label="{label}关键细节分项得分"><table><thead><tr><th>关键细节维度</th><th>确认错误数</th><th>得分</th></tr></thead><tbody>{rows}</tbody></table></div>
      <p class="note">分数按未舍入值汇总，显示两位小数。资产独立打开、搬移后资源解析、统一六视图渲染与成片完整解码检查通过。</p>
      <p class="inline-links"><a href="results.json">完整评分数据 ↗</a><a href="{review_root}/detail-restoration-review.json">关键细节评审 ↗</a><a href="{review_root}/music-review.json">音乐评审 ↗</a><a href="{review_root}/sfx-review.json">音效评审 ↗</a></p>
      <h3>{label} 的实际交付成片</h3>
      <figure class="showcase-media"><video id="showcase-video" controls playsinline preload="metadata" poster="{delivery['poster']}" width="{delivery['width']}" height="{delivery['height']}" src="{delivery['video']}">浏览器不支持视频播放。<a href="{delivery['video']}">下载成片</a></video><figcaption>{label} · {delivery['width']} × {delivery['height']} · 24 fps · {delivery['video_frame_count']} 帧 · {duration} 秒 · 有声</figcaption></figure>
      <div class="links delivery-links"><a href="{delivery['asset']}" download>下载机甲资产 .blend ↓</a>{project_link}<a href="{delivery['archive']}" download>下载完整交付 ZIP ↓</a><a href="{delivery['video']}" download>下载成片 MP4 ↓</a><a href="{delivery['readme']}">交付说明 ↗</a></div>
      <h3>运行信息</h3>
      <dl class="runtime-list"><div><dt>模型与框架</dt><dd>{label} · xhigh · 官方 Codex</dd></div><div><dt>运行耗时</dt><dd>{minutes} 分 {seconds:.2f} 秒</dd></div><div><dt>工具调用</dt><dd>{runtime['tool_calls']} 次</dd></div><div><dt>模型响应</dt><dd>{runtime['responses']} 次</dd></div><div><dt>运行环境</dt><dd>Linux · 4 核 CPU · 8 GiB 主机内存预算 · RTX 4090 D（24 GB）</dd></div><div><dt>工具版本</dt><dd>官方 Codex CLI 0.142.4 · Blender 5.3.0 · Cycles CUDA</dd></div></dl>
      <p class="note">从空工程与全新上下文独立完成，未提供旧工程、成片、评分或缺陷反馈；未设置总时长或工具调用次数上限。</p>
'''


def sol_execution():
    steps = [
        ('六向观察与程序建模', '根据原始六张参考图编写主体、腿部、双臂与管线脚本；分别组织可编辑部件，生成自制贴花与程序材质。'),
        ('正交预览与局部修正', '使用参考机位检查模型，自行修正曲线包围盒导致的尺寸问题，并补充背部圆腔、腿部活塞及夹爪护框。'),
        ('多镜头展示与图形', '构建独立的画面场景与剪辑混音场景，安排座舱、双臂、背部、腿足、顶视、正视、环绕和片尾镜头。'),
        ('CUDA 与 GPU 降噪', '对比短段渲染，选择 CUDA 与 GPU 降噪。复用短测的前 6 张原生图，续渲第 7–686 帧，再编码 1080p 成片。'),
        ('配乐与三类音效混音', '在 Blender 剪辑场景中编排原配乐、whoosh、hit 与 drop，并设置音量变化；最终成片为 48 kHz 立体声。'),
        ('交付与复用检查', '交付独立资产、展示工程、成片、封面及源码，完成资源搬移检查与短段重导出，最后完整解码成片。')
    ]
    content = '<ol class="steps">' + ''.join(f'<li><span class="step-no" aria-hidden="true">{i}</span><div><h3>{title}</h3><p>{text}</p></div></li>' for i, (title, text) in enumerate(steps, 1)) + '</ol>'
    starts = [1, 97, 157, 217, 289, 334, 379, 424, 469, 554, 648]
    names = ['开场全景', '驾驶舱', '三爪工具', '双刃夹钳', '背部动力包', '腿足机构', '顶视检视', '正视检视', '整机环绕', '收尾全景', '片尾署名']
    content += '<h3>成片镜头组织</h3><ol class="shot-timeline shot-timeline--long" aria-label="Sol十一组镜头的时间范围">'
    for i, (frame, name) in enumerate(zip(starts, names)):
        start = (frame - 1) / 24
        end = (starts[i + 1] - 1) / 24 if i + 1 < len(starts) else 686 / 24
        content += f'<li><button type="button" data-seek="{start:.9f}"><span class="shot-time">{start:.2f}–{end:.2f} s</span><strong>{name}</strong></button></li>'
    return content + '</ol><p class="note">点击时间段可定位到所选模型成片中的对应镜头。</p>'


def sol_analysis(astra_analysis, root, detail, review_root):
    compare_start = astra_analysis.index('      <div class="comparison-tabs"')
    compare_end = astra_analysis.index('      <ul class="findings-list">')
    comparison = astra_analysis[compare_start:compare_end].replace('assets/comparison/', root + '/comparison/').replace('assets/reconstruction/', root + '/reconstruction/')
    content = '''<h3 class="first-subheading">Sol 6.2：完成整机展示，局部结构与造型还原不足</h3>
      <p>Sol 恢复了红色机甲、开放座舱和双侧工具的总体形象，并交付完整镜头与声音。固定六视图仍显示驾驶舱装配、两套工具造型及图案标识与参考存在明显差异。</p>
''' + comparison
    content += '''<ul class="findings-list"><li><strong>部件：</strong>中央操纵总成、肩侧具体挂载工具及外伸尖刺件缺失。</li><li><strong>造型：</strong>三爪工具、双刃夹钳、腰间垂片和座舱顶罩的形状特征被改写。</li><li><strong>表面：</strong>罩面图案与质感、腰间徽标、文字编号和装甲磨损未忠实还原。</li></ul>
      <h3>关键细节：三项均扣至 0 分</h3><p>Gemini 4 Neon 分别确认部件与装配 3 处、造型特征 4 处、材质与表面细节 4 处独立明确错误，按每处扣 5 分、单项最低 0 分计算。</p>
'''
    summaries = [
        ['驾驶舱中央操纵立柱与双握把中控总成缺失。', '肩侧具体工具与补给装备被抽象管条替代。', '胸部与膝甲等处的外伸金属尖刺件整体缺失。'],
        ['三爪钳瓣的弧形铲状轮廓被直尖三角形改写。', '左臂夹剪刃被规则方齿的平开夹爪替代。', '腰间战旗的撕裂边缘与开口被平滑尖旗替代。', '座舱顶罩的折面轮廓与开口边缘被圆拱造型改写。'],
        ['顶罩图案、蜂窝纹理与半透明罩面质感未还原。', '腰间手臂徽标被 V 形折线图案替代。', '机身新增自编编号与条码，原有喷涂文字遗漏。', '红色装甲的银色露底掉漆与深划痕分布未还原。']
    ]
    for dimension, descriptions in zip(detail['dimensions'], summaries):
        assert len(dimension['deductions']) == len(descriptions)
        rows = ''.join(f'<tr><td><button class="time-link" type="button" data-seek="{item["video_timestamp_s"]}">{item["video_timestamp_s"]:.2f} s</button><span class="note"> · 帧 {item["video_frame_zero_based"]}</span></td><td>{text}</td></tr>' for item, text in zip(dimension['deductions'], descriptions))
        content += f'<details class="detail-evidence"><summary>{escape(dimension["name"])} · {dimension["confirmed_error_count"]} 处错误 · 0 / 10</summary><div class="detail-body"><div class="table-scroll" tabindex="0" role="region" aria-label="Sol {escape(dimension["name"])}证据"><table class="detail-evidence-table"><thead><tr><th>成片定位</th><th>确认差异</th></tr></thead><tbody>{rows}</tbody></table></div></div></details>'
    content += f'''<figure class="evidence-figure"><a class="image-zoom" href="{root}/evidence/detail-restoration.jpg" data-zoom data-title="Sol 关键细节 · 参考与重建对照"><img src="{root}/evidence/detail-restoration.jpg" alt="Sol驾驶舱、三爪工具和腰间徽标的参考与重建局部对照" width="1400" height="1200" loading="lazy" decoding="async"></a><figcaption>同一固定机位的原图裁剪。左：输入参考；右：Sol 提交资产统一机位渲染。</figcaption></figure>
      <p class="inline-links"><a href="{review_root}/detail-restoration-review.json">查看全部扣分位置与归属说明 ↗</a></p>
      <h3>音画：音乐编排与音效对应各得 5 分</h3><p>Gemini 4 Neon 独立听看本片，音乐编排 M1–M5 与音效对应 S1–S5 均通过。确认 6 处 whoosh、7 处 hit、3 处 drop；评分来自本片实际最终混音与参考音源。</p>
      <p class="inline-links"><a href="{review_root}/music-review.json">音乐评审 ↗</a><a href="{review_root}/sfx-review.json">音效逐项裁定 ↗</a></p>'''
    return content


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sol-run', required=True, type=Path)
    args = parser.parse_args()
    run = args.sol_run.resolve()
    page = (HERE / 'gpu-page.html').read_text(encoding='utf-8')
    data = read(SITE / 'results.json')
    astra = copy.deepcopy(next(m for m in data['models'] if m['model'] == 'gpt-6.2-astra'))
    astra.update(id=ASTRA_ID, assets_root='assets', review_root='review')
    astra['delivery']['readme'] = 'assets/delivery-README.md'
    root = package_sol(run)
    review_root = 'review/' + SOL_ID
    detail, music, sfx = public_reviews(run / 'evaluation/all-scores-bundle')
    for name, value in [('detail-restoration-review.json', detail), ('music-review.json', music), ('sfx-review.json', sfx)]:
        write(SITE / review_root / name, value)
    result = read(run / 'EXPERIMENT-RESULT.json')
    static = read(run / 'evaluation/static60/STATIC-COMPARISON.json')
    final = read(run / 'evaluation/all-scores-bundle/FINAL-SCORE.json')
    assert final['scoring_version'] == data['protocol_version'] == 'scv-showcase-ssim-v3'
    scores = final['scores']
    assert scores['appearance'] == 30 * max(0, min(1, static['raw_image_means']['foreground_union_SSIM']))
    assert scores['total'] == sum(scores[key] for key in ['structure', 'appearance', 'detail_restoration', 'music', 'sfx'])
    sol = {
        'id': SOL_ID, 'case': 'scv-showcase', 'experiment': result['experiment'], 'model': result['model'], 'model_display': 'Sol 6.2', 'framework': 'Codex', 'reasoning_effort': 'xhigh',
        'scores': scores, 'weights': astra['weights'], 'raw_metrics': {'F1_tolerance_reference_diagonal_0_5_percent': static['raw_visible_F1']['fscore'], 'six_view_silhouette_IoU': static['raw_image_means']['silhouette_IoU'], 'foreground_union_SSIM': static['raw_image_means']['foreground_union_SSIM']},
        'detail_criteria': [{k: d[k] for k in ['id', 'name', 'maximum', 'deduction_per_error', 'confirmed_error_count', 'score']} for d in detail['dimensions']],
        'detail_judge': detail['judge_model'], 'audio_visual_judge': music['judge_model'], 'engineering_gate': static['automatic_engineering_gate'], 'engineering_weight': 0,
        'runtime': {**astra['runtime'], 'elapsed_seconds': result['elapsed_seconds'], 'tool_calls': result['tool_calls'], 'responses': result['responses']},
        'fresh_context': True, 'starts_from_empty_workspace': True, 'prior_outputs_or_feedback_provided': False,
        'render_route': {'backend': 'Cycles CUDA', 'samples': 18, 'gpu_denoising': True, 'native_3d_frames': 686, 'native_test_frames_reused': [1, 6], 'continued_production_frames': [7, 686], 'sparse_reprojection_or_video_interpolation': False},
        'assets_root': root, 'review_root': review_root,
        'delivery': {'video': root + '/showcase.mp4', 'poster': root + '/poster.jpg', 'asset': root + '/asset.blend', 'project': root + '/showcase.blend', 'archive': root + '/delivery.zip', 'readme': root + '/delivery-README.md', 'width': 1920, 'height': 1080, 'fps': 24, 'video_frame_count': 686, 'video_duration_seconds': 686 / 24, 'audio_sample_rate': 48000, 'audio_channels': 2, 'video_sha256': sha(SITE / root / 'showcase.mp4')}
    }
    models = [astra, sol]
    data.update(default_model=ASTRA_ID, models=models)
    write(SITE / 'results.json', data)

    old_results, _ = section(page, 'results')
    old_execution, astra_execution = section(page, 'execution')
    old_analysis, astra_analysis = section(page, 'analysis')
    astra_detail = read(SITE / 'review/detail-restoration-review.json')
    bodies = {
        ASTRA_ID: {'results': render_results(astra, astra_detail, 'review'), 'execution': astra_execution, 'analysis': astra_analysis},
        SOL_ID: {'results': render_results(sol, detail, review_root), 'execution': sol_execution(), 'analysis': sol_analysis(astra_analysis, root, detail, review_root)}
    }
    score_rows = ''
    cards = ''
    for model in models:
        score = model['scores']
        selected = model['id'] == ASTRA_ID
        score_rows += f'<tr data-result-model="{model["id"]}" data-selected="{str(selected).lower()}"><th scope="row"><button type="button" class="model-score-button" data-select-model="{model["id"]}" aria-pressed="{str(selected).lower()}">{model["model_display"]}</button><span class="model-detail">xhigh · Codex · RTX 4090 D</span></th>' + ''.join(f'<td>{score[k]:.2f}</td>' for k in ['structure', 'appearance', 'detail_restoration', 'music', 'sfx']) + f'<td><strong class="score-value">{score["total"]:.2f}</strong></td></tr>'
        cards += f'<button type="button" class="model-score-card" data-select-model="{model["id"]}" aria-pressed="{str(selected).lower()}"><span>{model["model_display"]}<small>xhigh · Codex</small></span><strong>{score["total"]:.2f}<small>/ 100</small></strong></button>'
    summary = f'''    <section class="section" id="results" aria-labelledby="results-title">
      <div class="section-heading"><h2 id="results-title"><span class="sec-no">03</span>测试结果</h2></div>
      <div class="model-score-cards" aria-label="两模型总分">{cards}</div>
      <div class="table-scroll" tabindex="0" role="region" aria-label="两模型评分表，可横向滚动"><table class="score-table"><caption class="sr-only">SCV两模型成绩，点击模型名称切换实际交付与分析</caption><thead><tr><th scope="col">模型 / 框架</th><th scope="col">结构 / 30</th><th scope="col">外观 / 30</th><th scope="col">关键细节 / 30</th><th scope="col">音乐 / 5</th><th scope="col">音效 / 5</th><th scope="col">总分 / 100</th></tr></thead><tbody>{score_rows}</tbody></table></div>
      <p class="note">两次独立GPU实验采用同一套现行评分规则。点击模型名称或下方选项，切换该模型的成片、交付、过程及失败分析；本表始终展示两者成绩。</p>
    </section>
    <div class="model-switcher" id="model-switcher">
      <span class="switcher-label">查看交付与分析</span>
      <div class="model-tabs" role="tablist" aria-label="选择展示模型">''' + ''.join(f'<button type="button" id="model-tab-{m["id"]}" role="tab" aria-selected="{str(m["id"] == ASTRA_ID).lower()}" aria-controls="model-results-panel model-execution-panel model-analysis-panel" tabindex="{0 if m["id"] == ASTRA_ID else -1}" data-select-model="{m["id"]}">{m["model_display"]}<span>{m["scores"]["total"]:.2f} / 100</span></button>' for m in models) + '''</div>
    </div>
    <section class="section" id="delivery" aria-labelledby="delivery-title">
      <div class="section-heading"><h2 id="delivery-title">实际交付与裁定</h2><span class="selected-model-label" data-model-name>Astra 6.2</span></div>
      <div id="model-results-panel" role="tabpanel" aria-labelledby="model-tab-astra62-xhigh" data-model-section="results">''' + bodies[ASTRA_ID]['results'] + '</div>\n    </section>'
    page = page.replace(old_results, summary)
    for name, old, number, title in [('execution', old_execution, '04', '执行过程'), ('analysis', old_analysis, '05', '失败分析')]:
        replacement = f'''    <section class="section" id="{name}" aria-labelledby="{name}-title"><div class="section-heading"><h2 id="{name}-title"><span class="sec-no">{number}</span>{title}</h2><span class="selected-model-label" data-model-name>Astra 6.2</span></div><div id="model-{name}-panel" role="tabpanel" aria-labelledby="model-tab-astra62-xhigh" data-model-section="{name}">{bodies[ASTRA_ID][name]}</div></section>'''
        page = page.replace(old, replacement)
    templates = ''.join(f'<template data-model-template="{model}" data-section="{name}">{content}</template>\n' for model, sections in bodies.items() for name, content in sections.items())
    page = page.replace('  <dialog id="image-dialog"', templates + '  <dialog id="image-dialog"')
    metadata = {m['id']: {'name': m['model_display'], 'assetsRoot': m['assets_root'], 'asset': m['delivery']['asset']} for m in models}
    page = page.replace('  <script src="app.js" defer></script>', '  <script src="app.js?v=sol-comparison-v1" defer></script>')
    page = page.replace('<link rel="stylesheet" href="style.css">', '<link rel="stylesheet" href="style.css?v=sol-comparison-v1">')
    page = page.replace('</head>', '  <link rel="stylesheet" href="comparison.css?v=sol-comparison-v1">\n</head>')
    page = page.replace('  <p id="player-status"', '<script type="application/json" id="model-metadata">' + json.dumps(metadata, ensure_ascii=False).replace('<', '\\u003c') + '</script>\n  <p id="player-status"')
    page = page.replace('Astra 6.2 与 Codex 的 GPU 从头实验、实际交付及评分', 'Astra 6.2、Sol 6.2 与 Codex 的 GPU 独立实验、交付与评分')
    page = page.replace('<span class="tag">Astra 6.2 · xhigh · Codex</span>', '<span class="tag">Astra 6.2 / Sol 6.2 · xhigh · Codex</span>')
    page = page.replace('<a href="assets/asset.blend" download>下载重建资产', '<a data-selected-asset href="assets/asset.blend" download>下载重建资产')
    page = page.replace('<a href="#results">三、测试结果</a>', '<a href="#results">三、测试结果与交付</a>')
    write(SITE / 'model-display.json', {'default_model': ASTRA_ID, 'models': metadata})
    (SITE / 'index.html').write_text(page, encoding='utf-8')
    shutil.copy2(HERE / 'comparison-app.js', SITE / 'app.js')
    shutil.copy2(HERE / 'comparison.css', SITE / 'comparison.css')

    package = HERE / 'verification-v3'
    out = package / 'results' / SOL_ID
    surface = static['raw_visible_F1']
    write(out / 'surface_metrics.json', {'fscore': surface['fscore'], 'precision': surface['precision'], 'recall': surface['recall'], 'threshold_world_units': surface['threshold_world_units']})
    write(out / 'image_metrics.json', strip_legacy_distance(read(run / 'evaluation/static60/metrics/image_metrics.json')))
    for path in (SITE / review_root).glob('*.json'):
        shutil.copy2(path, out / path.name)
    write(out / 'expected-score.json', {'scores': scores})
    bundle(package, SITE / 'assets/scoring-verification-v3.zip')
    manifest = [{'path': p.relative_to(SITE).as_posix(), 'mime': mimetypes.guess_type(p.name)[0] or 'application/octet-stream', 'bytes': p.stat().st_size, 'sha256': sha(p)} for p in sorted((SITE / 'assets').rglob('*')) if p.is_file()]
    write(SITE / 'assets-manifest.json', manifest)
    catalog = ROOT / 'docs/index.html'
    text = catalog.read_text(encoding='utf-8')
    text, count = re.subn(r'Astra 6\.2 xhigh \+ Codex · 35\.38 / 100 · RTX 4090 D', 'Astra 6.2 35.38 · Sol 6.2 32.90 / 100 · Codex · RTX 4090 D', text)
    assert count == 1 or 'Astra 6.2 35.38 · Sol 6.2 32.90 / 100' in text
    catalog.write_text(text, encoding='utf-8')
    print(json.dumps({'models': {m['model_display']: m['scores']['total'] for m in models}, 'sol_zip_bytes': (SITE / root / 'delivery.zip').stat().st_size, 'default': ASTRA_ID}, ensure_ascii=False))


if __name__ == '__main__':
    main()
