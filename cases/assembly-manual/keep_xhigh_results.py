"""Keep only the two xhigh submissions in the public case; archive removed assets locally."""
from pathlib import Path
import copy
import json
import re
import shutil
import hashlib

ROOT = Path(__file__).resolve().parents[2]
REPO = ROOT / 'work/omniale-coach-publish'
PAGE = REPO / 'docs/assembly-manual'
ARCHIVE = ROOT / 'outputs/HoloAssist_manual_v1/non-xhigh-public-archive'


def main():
    ARCHIVE.mkdir(exist_ok=True)
    source = PAGE / 'data.json'
    data = json.loads(source.read_text(encoding='utf8'))
    kept = {key: copy.deepcopy(data['systems'][key]) for key in ['sol-xhigh', 'luna-xhigh']}
    if not (ARCHIVE / 'data-before-removal.json').exists():
        shutil.copyfile(source, ARCHIVE / 'data-before-removal.json')
    data['systems'] = kept
    data['default_system'] = 'sol-xhigh'
    source.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
    html = (PAGE / 'index.html').read_text(encoding='utf8')
    for key in ['sol', 'luna']:
        html, _ = re.subn(r'<button\b[^>]*id="select-' + key + r'".*?</button>', '', html, flags=re.S)
        html = re.sub(r'<option value="' + key + r'"[^>]*>.*?</option>', '', html)
    html = html.replace('Sol默认、Luna默认、Sol xhigh与Luna xhigh', 'Sol xhigh与Luna xhigh')
    html = html.replace('四组独立交付', '两组独立交付').replace('四组运行', '两组运行').replace('四组完整结果', '两组完整结果')
    html = html.replace('四组手册', '两组手册').replace('四组独立运行', '两组独立运行')
    html = html.replace('原Sol与Luna采用模型目录默认推理强度，分别为low与medium；旧会话未独立声明该参数。', '')
    html = html.replace('手册20分与设计10分统一采用v3标准，由GPT-6.1-Sol验收；问答50分与时间证据20分保留各组原裁定，默认运行使用GPT-6-Astra，xhigh运行使用GPT-6.1-Sol。问答评委不同，分差不能单独归因于推理强度。',
        '两组均由GPT-6.1-Sol主评；手册20分与设计10分统一采用v3标准，Gemini核听源音频。')
    html = html.replace('问答及时间证据保留原裁定：两组xhigh由GPT-6.1-Sol主评，两组默认由GPT-6-Astra主评。',
        '问答及时间证据由GPT-6.1-Sol主评。')
    html = html.replace('不同主评之间的分差不能单独归因于推理强度。', '')
    html = html.replace('GPT-6.1-Sol / GPT-6-Astra', 'GPT-6.1-Sol')
    html = html.replace('app.js?v=manual-v3', 'app.js?v=xhigh-only-1')
    # Ensure the static fallback is also the retained Sol xhigh artifact.
    sol = kept['sol-xhigh']
    delivery = sol['delivery']
    html = html.replace('results/sol/', 'results/sol-xhigh/')
    html = html.replace('/sol-manual.docx', '/sol-xhigh-manual.docx').replace('/sol-editable-delivery.zip', '/sol-xhigh-editable-delivery.zip')
    html = re.sub(r'(<select[^>]*id="manual-page"[^>]*>).*?(</select>)',
        lambda m: m[1] + ''.join(f'<option value="{i}">第{i}页</option>' for i in range(1, delivery['pages'] + 1)) + m[2], html, flags=re.S)
    for key in ['select-sol-xhigh', 'select-luna-xhigh']:
        pattern = r'(<button\b[^>]*id="' + key + r'"[^>]*>)(.*?)(</button>)'
        def update(match):
            opening = re.sub(r'class="system-card(?: active)?"',
                'class="system-card' + (' active' if key == 'select-sol-xhigh' else '') + '"', match[1])
            opening = re.sub(r'aria-pressed="(?:true|false)"',
                'aria-pressed="' + ('true' if key == 'select-sol-xhigh' else 'false') + '"', opening)
            body = match[2]
            if key == 'select-sol-xhigh':
                body = re.sub(r'<b>.*?</b>', '<b>✓ 当前展示 Sol xhigh</b>', body)
            return opening + body + match[3]
        html = re.sub(pattern, update, html, flags=re.S)
    for id_, value in [('result-total', sol['result']['score_display'] + '<small>/ 100</small>'),
                       ('result-duration', '约462分58秒'), ('result-tools', str(sol['solver']['tool_calls']) + '次工具调用'),
                       ('page-label', '01 / 13'), ('artifact-pages', '13'),
                       ('file-bundle-description', delivery['bundle_description'])]:
        html = re.sub(r'(<[^>]+\bid="' + id_ + r'"[^>]*>).*?(</(?:div|span|p)>)',
            lambda m: m[1] + value + m[2], html, flags=re.S)
    # Static intro details are filled from actual xhigh delivery.
    html = re.sub(r'(<strong id="hero-pages">).*?(</strong>)',
                  lambda m: m[1] + '13<small>页</small>' + m[2], html, flags=re.S)
    html = html.replace('<strong id="hero-pages">13<small>页</small></div>',
        '<strong id="hero-pages">13<small>页</small></strong><span id="hero-figures">实际手册 · 84份图像与标注文件</span></div>')
    html = html.replace('<b id="artifact-pages">13</span>', '<b id="artifact-pages">13</b><span>页 · 实际PDF手册</span>')
    html = html.replace('4<small>组结果</small>', '2<small>组结果</small>').replace('Sol／Luna · 默认与xhigh', 'Sol／Luna · xhigh')
    html = html.replace('<b id="artifact-figures">26</b>', '<b id="artifact-figures">84</b>')
    html = html.replace('组原图及SVG标注源', '份图像及标注文件')
    facts = ('<div class="facts"><div><strong>18:31</strong><span>输入 · 完整装配音视频</span></div>'
        '<div><strong>10</strong><span>核查问题 · 跨时刻事件关系</span></div>'
        '<div><strong id="hero-pages">13<small>页</small></strong><span id="hero-figures">实际手册 · 84份图像与标注文件</span></div>'
        '<div><strong>2<small>组结果</small></strong><span>Sol／Luna · xhigh</span></div></div>')
    html = re.sub(r'<div class="facts">.*?</section>', facts + '</section>', html, count=1, flags=re.S)
    html = re.sub(r'(<[^>]+id="manual-description"[^>]*>).*?(</p>)',
                  lambda m: m[1] + '这里展示Sol xhigh实际提交的13页PDF，正文、截图和标注保留原样。' + m[2], html, flags=re.S)
    assert not re.search(r'data-system="(?:sol|luna)"|value="(?:sol|luna)"|results/(?:sol|luna)/|Sol默认|Luna默认|四组|GPT-6-Astra', html)
    (PAGE / 'index.html').write_text(html, encoding='utf8')
    app = (PAGE / 'app.js').read_text(encoding='utf8')
    app = re.sub(r'const modelNames=.*?;', "const modelNames={'sol-xhigh':'GPT-6.1-Sol · xhigh','luna-xhigh':'GPT-6-Luna · xhigh'};", app)
    app = re.sub(r'const shortNames=.*?;', "const shortNames={'sol-xhigh':'Sol xhigh','luna-xhigh':'Luna xhigh'};", app)
    app = app.replace("active='sol'", "active='sol-xhigh'").replace("||'sol',false", "||'sol-xhigh',false")
    app = app.replace('systems.sol.result.questions', "systems[all.default_system].result.questions")
    app = app.replace("${key==='luna'?'，附标注PNG预览':''}", '')
    (PAGE / 'app.js').write_text(app, encoding='utf8')
    rules = (PAGE / 'SCORING.zh-CN.md').read_text(encoding='utf8')
    rules = rules.replace('问答50分与时间证据20分：Sol默认、Luna默认由GPT-6-Astra裁定，两个xhigh运行由GPT-6.1-Sol裁定。',
                          '问答50分与时间证据20分：两个xhigh运行均由GPT-6.1-Sol裁定。')
    rules = rules.replace('四组统一', '两组统一').replace(
        '四组使用相同输入、工具和固定权重，但xhigh运行的主评与两组默认运行不同，分差不能单独归因于推理强度。',
        '两组使用相同输入、工具、显式xhigh推理设置与固定权重，均由GPT-6.1-Sol主评。')
    (PAGE / 'SCORING.zh-CN.md').write_text(rules, encoding='utf8')
    for path in [PAGE / 'STRICT_MANUAL_RUBRIC.zh-CN.md', REPO / 'cases/assembly-manual/STRICT_MANUAL_RUBRIC.zh-CN.md']:
        text = path.read_text(encoding='utf8').replace('适用于四组封存交付', '适用于两组xhigh封存交付')
        path.write_text(text, encoding='utf8')
    catalog = REPO / 'docs/index.html'
    text = catalog.read_text(encoding='utf8')
    status = 'Sol xhigh ' + kept['sol-xhigh']['result']['score_display'] + ' · Luna xhigh ' + kept['luna-xhigh']['result']['score_display'] + ' · 同页查看手册与评分'
    text, count = re.subn(r'(<a class="case-card" href="assembly-manual/".*?<div class="status"><span class="status-dot"></span>).*?(</div>)',
        lambda m: m[1] + status + m[2], text, count=1, flags=re.S)
    assert count == 1
    catalog.write_text(text, encoding='utf8')
    # Removed public assets remain available in the organizer's local archive.
    for key in ['sol', 'luna']:
        target = (PAGE / 'results' / key).resolve()
        assert target.parent == (PAGE / 'results').resolve() and target.name in ['sol', 'luna']
        if target.exists():
            backup = ARCHIVE / key
            shutil.copytree(target, backup, dirs_exist_ok=True)
            for p in target.rglob('*'):
                if p.is_file():
                    saved = backup / p.relative_to(target)
                    assert hashlib.sha256(p.read_bytes()).digest() == hashlib.sha256(saved.read_bytes()).digest()
            shutil.rmtree(target)
    assert json.loads(source.read_text(encoding='utf8'))['systems'] == kept
    shutil.copyfile(Path(__file__), REPO / 'cases/assembly-manual/keep_xhigh_results.py')
    print(json.dumps({'systems': list(kept), 'default_system': data['default_system'],
                      'scores_unchanged': True, 'removed_public_assets_archived': True}))


if __name__ == '__main__':
    main()
