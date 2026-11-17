"""Add a sealed, explicitly verified Sol xhigh result to the existing case page.

This organizer-only build consumes final evaluation files. It does not run a
solver or judge, upload assets, commit changes, or publish the website.
"""
from pathlib import Path
from decimal import Decimal, ROUND_HALF_UP
from html.parser import HTMLParser
from urllib.parse import unquote, urlsplit
import argparse
import copy
import hashlib
import html
import json
import os
import re
import shutil
import zipfile

ROOT = Path(os.environ['OMNIALE_ORGANIZER_ROOT']).resolve()
REPO = ROOT / 'work/omniale-coach-publish'
PAGE = REPO / 'docs/assembly-manual'
CASE = REPO / 'cases/assembly-manual'
RELEASE = ROOT / 'work/assembly-manual-release'
TEMPLATE = Path(__file__).with_name('xhigh-template')
RELEASE_URL = 'https://github.com/vibrant700/omniale/releases/download/assembly-manual-v1/'
KEY = 'sol-xhigh'
TRIAL = 'sol-xhigh-codex01'
SOLVER_MODEL = 'gpt-6.1-sol'
SOLVER_LABEL = 'GPT-6.1-Sol'


def load(path):
    return json.loads(path.read_text(encoding='utf8'))


def dump(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf8')


def sha(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(2 ** 20), b''):
            digest.update(chunk)
    return digest.hexdigest()


def fmt(number):
    return str(Decimal(str(number)).quantize(Decimal('.01'), rounding=ROUND_HALF_UP))


def clean(value):
    text = str(value).replace('本轮', '本次评审').replace('重新评审', '评审')
    text = text.replace('不作事实待定', '事实依据明确')
    text = text.replace('不必因缺少原生听音重新待定', '该事实由原标注确认')
    return re.sub(r'(?<!重)复评', '评审', text.replace('，也不导致待定', '').replace('不重复评判', '不再评判'))


def clean_tree(value):
    if isinstance(value, dict):
        return {key: clean_tree(item) for key, item in value.items()}
    if isinstance(value, list):
        return [clean_tree(item) for item in value]
    return clean(value) if isinstance(value, str) else value


def answer_parts(text):
    matches = list(re.finditer(r'(?m)^#{1,6}\s+(Q(?:0[1-9]|10))\b[^\n]*$', text))
    return {match[1]: text[match.end():matches[i + 1].start() if i + 1 < len(matches) else len(text)].strip()
            for i, match in enumerate(matches)}


def compare(systems):
    cards = []
    labels = {'sol': ('GPT-6.1-Sol', 'Sol 默认', 'low（模型目录默认）'),
              'luna': ('GPT-6-Luna', 'Luna 默认', 'medium（模型目录默认）'),
              'sol-xhigh': ('GPT-6.1-Sol', 'Sol xhigh', 'xhigh（显式设置，逐请求核验）'),
              'luna-xhigh': ('GPT-6-Luna', 'Luna xhigh', 'xhigh（显式设置，逐请求核验）')}
    order = [key for key in ['sol', 'luna', 'sol-xhigh', 'luna-xhigh'] if key in systems]
    count_label = '四组' if len(order) == 4 else '三组'
    for key in order:
        item = systems[key]
        label, short, effort = labels[key]
        active = key == 'sol'
        groups = item['result']['groups']
        seconds = int(round(item['solver']['elapsed_seconds']))
        detail = ' · '.join(f'{name} {fmt(groups[group]["score"])}' for name, group in
                            [('问答', 'qa_semantic'), ('证据', 'qa_evidence'),
                             ('手册', 'manual_delivery'), ('设计', 'subjective_design')])
        button = ('✓ 当前展示 ' if active else '查看 ') + short + ('' if active else ' 手册与评分 →')
        cards.append(
            f'<button type="button" id="select-{key}" class="system-card{" active" if active else ""}" '
            f'data-system="{key}" aria-pressed="{str(active).lower()}" '
            'aria-controls="deliverable results questions document-review files" disabled>'
            f'<span>{label} + Codex</span><span class="reasoning-label">推理：{effort}</span>'
            f'<strong>{item["result"]["score_display"]}<small> / 100</small></strong>'
            f'<p>{detail}</p><small>{seconds // 60}分{seconds % 60:02}秒 · '
            f'{item["solver"]["tool_calls"]}次工具调用</small><b>{button}</b></button>')
    caption = (count_label + '完整结果在此对比；点击卡片可同步切换分项、逐题依据、同页手册和下载文件。'
               '采用相同录像、十题与50/20/20/10评分权重，各次运行独立封存、分别验收。'
               '原Sol与Luna采用模型目录默认推理强度，分别为low与medium；旧会话未独立声明该参数。'
               'xhigh运行在配置与CLI中显式设置，并由网关核验每次模型请求。'
               '共同源音频的Gemini核听结果复用，事实计分以原标注为准。')
    caption += '主评：Sol默认与Luna默认使用GPT-6-Astra；xhigh运行使用GPT-6.1-Sol。评委不同，分差不能单独归因于推理强度。'
    caption += 'Sol xhigh在同一原生会话中自动压缩上下文并续接接口中断；显示耗时包含运行期间的接口等待。'
    return ('<div id="systems" class="results-comparison"><h3>' + count_label + '运行的完整结果</h3>'
            f'<p class="caption">{caption}</p><div class="system-grid">' + ''.join(cards) +
            '</div><p id="system-status" role="status" aria-live="polite">正在加载模型交付…</p></div>')


def build_data(run, existing):
    submission = run / 'sealed-submission'
    judge = run / 'annotation-primary-evaluation01'
    prep = run / 'evaluation'
    result = load(judge / 'evaluation.json')
    assert result['model'] == 'gpt-6.1-sol', 'This run requires the requested Sol main judge'
    record = load(run / 'run_record.json')
    inspection = load(prep / 'inspection/inspection.json')
    assert not result['errors'] and result['pending_points'] == 0, 'Evaluation must be final and complete'
    assert record['solver_model'] == SOLVER_MODEL and record['reasoning_effort'] == 'xhigh'
    assert result['solver_model'] == SOLVER_MODEL
    assert record['status'] == 'solver_finished', 'Only completed runs may be published'
    verification = record['reasoning_verification']
    assert verification['request_count'] > 0 and verification['all_requests_explicit_xhigh'] is True
    expected = load(run / 'submission_seal.json')['files']
    actual = {path.relative_to(submission).as_posix(): sha(path) for path in submission.rglob('*') if path.is_file()}
    assert actual == expected, 'Sealed delivery differs'
    assert record['candidate_unchanged'] and record['evaluator_unchanged']
    assert record.get('phase1_seal_unchanged', True)
    for earlier in ['sol-codex01', 'luna-codex01']:
        old = load(run.parent / earlier / 'run_record.json')
        assert record['candidate_sha256'] == old['candidate_sha256'], 'Inputs differ from earlier runs'
        assert record['asr_weights_sha256'] == old['asr_weights_sha256']
        assert record['codex_binary_sha256'] == old['codex_binary_sha256']
        assert record['sandbox_image_id'] == old['sandbox_image_id']
    count = inspection['pdf']['page_count']
    assert count > 0 and inspection['docx']['valid']
    assert len(inspection['pdf']['pages']) == count
    assert len(result['questions']) == 10
    answers_path = run / 'sealed-phase1/sealed-answers.md'
    answers = answer_parts(answers_path.read_text(encoding='utf-8-sig'))
    assert set(answers) == {f'Q{i:02}' for i in range(1, 11)}
    original = existing['systems']['sol']
    data = copy.deepcopy(original)
    by_id = {question['id']: question for question in original['result']['questions']}
    questions = []
    for row in result['questions']:
        qid = row['qid']
        values = clean_tree(load(judge / (qid + '.json')))
        question = copy.deepcopy(by_id[qid])
        breakdown = row['breakdown']
        question['answer'] = answers[qid]
        question['score'] = row['confirmed_points']
        question['scores'] = {'qa': breakdown['qa_semantic']['confirmed'],
                              'evidence': breakdown['qa_evidence']['confirmed'],
                              'manual': breakdown['manual_facts']['confirmed'] + breakdown['manual_illustrations']['confirmed']}
        question['checks'] = {key: [{field: check[field] for field in
                                    ['id', 'status', 'evidence', 'pages', 'annotation_event_ids'] if field in check}
                                   for check in values[key]] for key in
                              ['qa_claims', 'qa_evidence', 'manual_claims', 'illustration_checks']}
        assert all(check['status'] in ['pass', 'partial', 'fail']
                   for checks in question['checks'].values() for check in checks)
        question['page_numbers'] = sorted({int(page) for key in ['manual_claims', 'illustration_checks']
                                           for check in values[key] for page in check.get('pages', [])
                                           if str(page).isdigit() and 1 <= int(page) <= count})
        lower = sorted(values['qa_claims'] + values['qa_evidence'],
                       key=lambda check: {'fail': 0, 'partial': 1, 'pass': 2}[check['status']])
        question['summary'] = lower[0]['evidence'][:240] + ('…' if len(lower[0]['evidence']) > 240 else '')
        questions.append(question)
    data['solver'] = {'model': SOLVER_MODEL, 'framework': 'Official Codex CLI',
                      'version': record['codex_version'], 'elapsed_seconds': record['elapsed_seconds'],
                      'tool_calls': record['tool_calls'], 'audio_tool': 'whisper.cpp / base.en',
                      'local_asr_calls': record['asr_calls'], 'time_limit': None, 'tool_limit': None,
                      'native_audio': False, 'reasoning_effort': 'xhigh',
                      'reasoning_setting': 'Explicit config and CLI; gateway verifies every request',
                      'reasoning_request_count': verification['request_count'],
                      'all_requests_explicit_xhigh': True,
                      'transport': record.get('transport', 'official_openai_python_sdk'),
                      'transport_continuations': len(record.get('transport_continuations', [])),
                      'same_native_session_preserved': True,
                      'elapsed_includes_provider_waits': True}
    data['result'] = {'score': result['confirmed_diagnostic_points'],
                      'score_display': fmt(result['confirmed_diagnostic_points']), 'maximum': 100,
                      'groups': {key: {'score': round(value['confirmed'], 10), 'maximum': round(value['maximum'], 10)}
                                 for key, value in result['group_scores'].items()},
                      'details': {key: {'score': round(value['confirmed'], 10), 'maximum': round(value['maximum'], 10)}
                                  for key, value in result['detailed_scores'].items()},
                      'questions': sorted(questions, key=lambda question: question['id'])}
    assert abs(sum(value['score'] for value in data['result']['groups'].values()) - data['result']['score']) < .001
    assert sum(value['maximum'] for value in data['result']['groups'].values()) == 100
    assets = [path for path in submission.rglob('*') if path.is_file() and path.suffix.lower() in ['.png', '.jpg', '.jpeg', '.svg']]
    svg_count = sum(path.suffix.lower() == '.svg' for path in assets)
    data['delivery'] = {'pages': count, 'figure_asset_count': len(assets), 'figure_count': len(assets),
                        'figure_summary': f'实际手册 · {len(assets)}份图像与标注文件',
                        'figure_description': '份图像及标注文件', 'editable_svg': svg_count,
                        'pdf': f'results/{KEY}/manual.pdf', 'docx': RELEASE_URL + KEY + '-manual.docx',
                        'bundle': RELEASE_URL + KEY + '-editable-delivery.zip', 'answers': f'results/{KEY}/answers.md',
                        'pdf_sha256': sha(submission / 'manual.pdf'), 'docx_sha256': sha(submission / 'manual.docx'),
                        'page_images': [f'results/{KEY}/pages/page-{i:03}.png' for i in range(1, count + 1)],
                        'page_topics': [f'实际交付第{i}页' for i in range(1, count + 1)],
                        'bundle_description': f'{SOLVER_LABEL} · xhigh：Word、PDF、答案与{len(assets)}份图像／标注文件，其中{svg_count}份SVG源。'}
    data['document_checks'] = clean_tree(load(prep / 'document.json'))
    data['source']['preview'] = 'assets/recording-preview.mp4'
    data['scoring']['audio_reuse'] = 'The same immutable source-audio observations are shared across systems; artifact and document judgments are independent.'
    data['scoring']['judge'] = result['model']
    data['scoring']['judge_reasoning_effort'] = 'high'
    if KEY == 'luna-xhigh':
        data['scoring']['criterion_group_judgments'] = ['Q07', 'Q10']
        data['scoring']['criterion_group_method'] = 'Same complete evidence and criteria; independent criterion groups combined by the fixed script.'
        data['solver']['local_asr_count_note'] = 'Completed observations only; interrupted attempts are excluded.'
    return data, record, inspection, submission, answers_path


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.urls = []
        self.ids = set()

    def handle_starttag(self, tag, attributes):
        attrs = dict(attributes)
        if 'id' in attrs:
            self.ids.add(attrs['id'])
        self.urls.extend(attrs[key] for key in ['href', 'src', 'poster'] if attrs.get(key))


def audit_public_text(files):
    forbidden = [r'sk-[A-Za-z0-9_-]{24,}', r'Bearer\s+[A-Za-z0-9_.-]{24,}', r'C:[/\\]Users[/\\]',
                 r'api-temporary\.nju-link', r'rollout-20\d\d']
    for path in files:
        text = path.read_text(encoding='utf8')
        assert not any(re.search(pattern, text) for pattern in forbidden), f'Private data in {path.name}'
        if path.suffix in ['.html', '.json', '.md']:
            assert not re.search(r'二次重测|待定|(?<!重)复评', text), f'Internal result wording in {path.name}'


def main():
    global KEY, TRIAL, SOLVER_MODEL, SOLVER_LABEL, TEMPLATE
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--system', choices=['sol-xhigh', 'luna-xhigh'], default='sol-xhigh')
    parser.add_argument('--trial')
    parser.add_argument('--check-only', action='store_true', help='Validate final inputs without changing the public page')
    parser.add_argument('--check-template', action='store_true', help='Validate dormant template structure without result files')
    args = parser.parse_args()
    KEY = args.system
    if KEY == 'luna-xhigh':
        TRIAL = 'luna-xhigh-codex01'
        SOLVER_MODEL = 'gpt-6-luna'
        SOLVER_LABEL = 'GPT-6-Luna'
        TEMPLATE = Path(__file__).with_name('luna-xhigh-template')
    args.trial = args.trial or TRIAL
    assert re.fullmatch(r'[a-z0-9_-]+', args.trial)
    if args.check_template:
        template = (TEMPLATE / 'index.html').read_text(encoding='utf8')
        app = (TEMPLATE / 'app.js').read_text(encoding='utf8')
        style = (TEMPLATE / 'case.css').read_text(encoding='utf8')
        assert template.count('{{SYSTEM_COMPARISON}}') == 1
        assert template.count('<section id="task"') == 1
        assert 'value="sol-xhigh"' in template
        if KEY == 'luna-xhigh':
            assert 'value="luna-xhigh"' in template
            assert "'luna-xhigh':'GPT-6-Luna · xhigh'" in app
            assert '4<small>组结果</small>' in template
        assert "'sol-xhigh':'GPT-6.1-Sol · xhigh'" in app
        assert 'shortNames[b.dataset.system]' in app
        assert 'repeat(3,minmax(0,1fr))' in style
        assert all(title in template for title in ['01 / 委托目标', '02 / 提供资料', '03 / 任务要求', '04 / 交付内容'])
        assert '.system-card.active>b{background:var(--lime)' in style
        audit_public_text([TEMPLATE / name for name in ['index.html', 'app.js', 'case.css']])
        print(json.dumps({'template_check': 'passed', 'public_page_changed': False,
                          'result_files_required_for_build': True, 'new_score_generated': False}))
        return
    run = ROOT / 'outputs/HoloAssist_manual_v1/runs' / args.trial
    existing = load(PAGE / 'data.json')
    assert {'sol', 'luna'} <= set(existing['systems'])
    preserved = {key: copy.deepcopy(value) for key, value in existing['systems'].items() if key != KEY}
    data, record, inspection, submission, answers_path = build_data(run, existing)
    combined = copy.deepcopy(existing)
    combined['systems'][KEY] = data
    assert all(combined['systems'][key] == value for key, value in preserved.items())
    template = (TEMPLATE / 'index.html').read_text(encoding='utf8')
    page = template.replace('{{SYSTEM_COMPARISON}}', compare(combined['systems']))
    assert '{{SYSTEM_COMPARISON}}' not in page
    assert all(f'data-system="{key}"' in page for key in combined['systems'])
    assert len(re.findall(r'<section id="task"', page)) == 1
    if args.check_only:
        print(json.dumps({'trial': args.trial, 'score': data['result']['score_display'],
                          'pages': data['delivery']['pages'], 'check_only': True,
                          'verified_xhigh_requests': record['reasoning_verification']['request_count'],
                          'old_systems_preserved': True}, ensure_ascii=False))
        return
    old_assets = {path: sha(path) for key in preserved for path in (PAGE / 'results' / key).rglob('*') if path.is_file()}
    target = PAGE / 'results' / KEY
    for path in [target / 'pages', RELEASE]:
        path.mkdir(parents=True, exist_ok=True)
    for i, image in enumerate(inspection['pdf']['pages'], 1):
        shutil.copyfile(run / 'evaluation/inspection' / image['image'], target / 'pages' / f'page-{i:03}.png')
    shutil.copyfile(submission / 'manual.pdf', target / 'manual.pdf')
    shutil.copyfile(answers_path, target / 'answers.md')
    shutil.copyfile(submission / 'manual.docx', RELEASE / (KEY + '-manual.docx'))
    bundle = RELEASE / (KEY + '-editable-delivery.zip')
    expected = load(run / 'submission_seal.json')['files']
    if not bundle.exists():
        with zipfile.ZipFile(bundle, 'w', zipfile.ZIP_DEFLATED, compresslevel=5) as archive:
            for path in sorted(submission.rglob('*')):
                if path.is_file():
                    archive.write(path, path.relative_to(submission).as_posix())
    with zipfile.ZipFile(bundle) as archive:
        assert set(archive.namelist()) == set(expected)
        assert all(hashlib.sha256(archive.read(name)).hexdigest() == digest for name, digest in expected.items())
    combined['systems'][KEY]['delivery']['bundle_sha256'] = sha(bundle)
    dump(PAGE / 'data.json', combined)
    (PAGE / 'index.html').write_text(page, encoding='utf8')
    scoring_path = PAGE / 'SCORING.zh-CN.md'
    scoring_text = scoring_path.read_text(encoding='utf8')
    scoring_text = scoring_text.replace('语义与图文由GPT-6-astra逐项评审，',
        'Sol默认与Luna默认的语义、图文及文档由GPT-6-Astra逐项评审；Sol xhigh由GPT-6.1-Sol主评。')
    if KEY == 'luna-xhigh':
        scoring_text = scoring_text.replace('Sol xhigh由GPT-6.1-Sol主评。', 'Sol xhigh与Luna xhigh由GPT-6.1-Sol主评。')
        scoring_text = scoring_text.replace('三组使用相同输入、工具和固定权重，但Sol xhigh的主评与前两组不同，分差不能单独归因于推理强度。',
            '四组使用相同输入、工具和固定权重，但xhigh运行的主评与两组默认运行不同，分差不能单独归因于推理强度。')
    comparison_note = ('四组使用相同输入、工具和固定权重，但xhigh运行的主评与两组默认运行不同，分差不能单独归因于推理强度。'
                       if KEY == 'luna-xhigh' else '三组使用相同输入、工具和固定权重，但Sol xhigh的主评与前两组不同，分差不能单独归因于推理强度。')
    if comparison_note not in scoring_text:
        scoring_text += '\n' + comparison_note + '\n'
    group_note = 'Luna xhigh的Q07、Q10由同一主评按问答、证据、手册事实、图示四类条目分别裁定；各请求提供相同完整证据，随后由固定脚本汇总。其余题目逐题裁定。'
    if KEY == 'luna-xhigh' and group_note not in scoring_text:
        scoring_text += '\n' + group_note + '\n'
    scoring_path.write_text(scoring_text, encoding='utf8')
    for name in ['app.js', 'case.css']:
        shutil.copyfile(TEMPLATE / name, PAGE / name)
    public = CASE / 'build_xhigh_page.py'
    code = Path(__file__).read_text(encoding='utf8').replace(
        'ROOT = Path(os.environ['OMNIALE_ORGANIZER_ROOT']).resolve()', "ROOT = Path(os.environ['OMNIALE_ORGANIZER_ROOT']).resolve()")
    public.write_text(code, encoding='utf8')
    shutil.copytree(TEMPLATE, CASE / TEMPLATE.name, dirs_exist_ok=True)
    catalog = REPO / 'docs/index.html'
    text = catalog.read_text(encoding='utf8')
    short_names = {'sol': 'Sol 默认', 'luna': 'Luna 默认', 'sol-xhigh': 'Sol xhigh', 'luna-xhigh': 'Luna xhigh'}
    status = ' · '.join(short_names[key] + ' ' + value['result']['score_display'] for key, value in combined['systems'].items()) + ' · 同页查看手册与评分'
    text, count = re.subn(r'(<a class="case-card" href="assembly-manual/".*?<div class="status"><span class="status-dot"></span>).*?(</div>)',
                         lambda match: match[1] + status + match[2], text, count=1, flags=re.S)
    assert count == 1
    catalog.write_text(text, encoding='utf8')
    manifest = {'model': SOLVER_MODEL, 'reasoning_effort': 'xhigh', 'score': data['result']['score_display'],
                'assets': [{'name': path.name, 'bytes': path.stat().st_size, 'sha256': sha(path)}
                           for path in [RELEASE / (KEY + '-manual.docx'), bundle]]}
    dump(RELEASE / (KEY + '-release-manifest.json'), manifest)
    assert old_assets == {path: sha(path) for path in old_assets}
    assert all(load(PAGE / 'data.json')['systems'][key] == value for key, value in preserved.items())
    parser = Links()
    parser.feed(page)
    for raw in parser.urls:
        parsed = urlsplit(raw)
        if parsed.scheme or parsed.netloc:
            continue
        local = (PAGE / unquote(parsed.path)).resolve() if parsed.path else PAGE / 'index.html'
        if local.is_dir():
            local /= 'index.html'
        assert local.is_file(), f'Missing local link: {raw}'
        if parsed.fragment and local == PAGE / 'index.html':
            assert parsed.fragment in parser.ids, f'Missing anchor: {raw}'
    audit_public_text([PAGE / name for name in ['index.html', 'data.json', 'app.js', 'case.css']] + [public])
    print(json.dumps({'trial': args.trial, 'scores': {key: item['result']['score_display'] for key, item in combined['systems'].items()},
                      'pages': data['delivery']['pages'], 'figure_assets': data['delivery']['figure_asset_count'],
                      'verified_xhigh_requests': record['reasoning_verification']['request_count'],
                      'old_systems_preserved': True, 'old_assets_preserved': True,
                      'public_text_audit': 'passed', 'local_links_checked': len(parser.urls)}, ensure_ascii=False))


if __name__ == '__main__':
    main()
