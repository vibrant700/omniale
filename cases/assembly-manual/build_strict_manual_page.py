"""Publish complete uniform manual/design judgments while preserving fixed 70 points."""
from pathlib import Path
import copy
import json
import re
import shutil
import argparse
import build_xhigh_page as page_builder

ROOT = Path(__import__('os').environ['OMNIALE_ORGANIZER_ROOT']).resolve()
OUT = ROOT / 'outputs/HoloAssist_manual_v1/strict-manual-v3'
REPO = ROOT / 'work/omniale-coach-publish'
PAGE = REPO / 'docs/assembly-manual'
RULES = Path(__file__).with_name('STRICT_MANUAL_RUBRIC.zh-CN.md')

def main():
    global OUT
    parser = argparse.ArgumentParser()
    parser.add_argument('--check-only', action='store_true')
    parser.add_argument('--output-name', default='strict-manual-v3')
    args = parser.parse_args()
    assert args.output_name and all(c.isalnum() or c in '-_' for c in args.output_name)
    OUT = ROOT / 'outputs/HoloAssist_manual_v1' / args.output_name
    final = page_builder.load(OUT / 'evaluation.json')
    assert final['all_seals_unchanged'] and page_builder.load(OUT / 'errors.json') == []
    original = page_builder.load(OUT / 'baseline-public-data.json')
    data = copy.deepcopy(original)
    for key, review in final['systems'].items():
        item = data['systems'][key]
        for group in ['manual_delivery', 'subjective_design']:
            item['result']['groups'][group]['score'] = review[group]
        for group in ['manual_facts', 'manual_illustrations', 'manual_organization', 'editable_delivery', 'subjective_design']:
            item['result']['details'][group]['score'] = review[group]
        item['result']['score'] = review['total']
        item['result']['score_display'] = page_builder.fmt(review['total'])
        byid = {q['id']: q for q in item['result']['questions']}
        factor = {'pass': 1, 'partial': .5, 'fail': 0}
        for q in review['questions']:
            target = byid[q['qid']]
            target['checks'].update({group: q['verdict'][group] for group in ['manual_claims', 'illustration_checks']})
            manual = sum(factor[c['status']] for c in q['verdict']['manual_claims']) * .6 / 4
            manual += sum(factor[c['status']] for c in q['verdict']['illustration_checks']) * .8 / 4
            target['scores']['manual'] = manual
            target['score'] = target['scores']['qa'] + target['scores']['evidence'] + manual
            target['page_numbers'] = sorted({int(n) for group in ['manual_claims', 'illustration_checks']
                for row in q['verdict'][group] for n in row.get('pages', [])
                if str(n).isdigit() and 1 <= int(n) <= item['delivery']['pages']})
        item['document_checks'] = review['document']
        item['scoring'].update(manual_judge=final['judge'], manual_judge_reasoning_effort='high',
            manual_scoring_version=final['version'], manual_scoring_rules='STRICT_MANUAL_RUBRIC.zh-CN.md',
            manual_judgments_blinded_to_old_scores=True)
        probe = page_builder.load(OUT / key / 'edit-probe/result.json')
        assert probe['original_docx_unchanged'] and probe['edited_text_present_in_exported_pdf']
        item['document_checks']['edit_probe'] = probe
        for group in ['qa_semantic', 'qa_evidence']:
            assert item['result']['groups'][group] == original['systems'][key]['result']['groups'][group]
        for q in item['result']['questions']:
            previous = next(p for p in original['systems'][key]['result']['questions'] if p['id'] == q['id'])
            for group in ['qa_claims', 'qa_evidence']:
                assert q['checks'][group] == previous['checks'][group]
        assert item['delivery'] == original['systems'][key]['delivery']
        assert abs(sum(g['score'] for g in item['result']['groups'].values()) - review['total']) < 1e-7
    for key in data['systems']:
        if key not in final['systems']:
            assert data['systems'][key] == original['systems'][key]
    data = page_builder.clean_tree(data)
    comparison = page_builder.compare(data['systems']).replace(
        '主评：Sol默认与Luna默认使用GPT-6-Astra；xhigh运行使用GPT-6.1-Sol。评委不同，分差不能单独归因于推理强度。',
        '手册20分与设计10分统一采用v3标准，由GPT-6.1-Sol验收；问答50分与时间证据20分保留各组原裁定，默认运行使用GPT-6-Astra，xhigh运行使用GPT-6.1-Sol。问答评委不同，分差不能单独归因于推理强度。')
    template = (Path(__file__).parent / 'luna-xhigh-template/index.html').read_text(encoding='utf8')
    html = template.replace('{{SYSTEM_COMPARISON}}', comparison)
    html = html.replace('三组独立交付', '四组独立交付').replace('app.js?v=xhigh-2', 'app.js?v=manual-v3')
    html = html.replace('Sol xhigh与Luna xhigh由GPT-6.1-Sol主评问答、画面、截图标注和手册；原Sol默认与Luna默认结果由GPT-6-Astra主评。',
        '四组手册20分与美观引导10分统一由GPT-6.1-Sol按v3标准验收。问答及时间证据保留原裁定：两组xhigh由GPT-6.1-Sol主评，两组默认由GPT-6-Astra主评。')
    assert '{{SYSTEM_COMPARISON}}' not in html
    if args.check_only:
        print(json.dumps({'scores': {k: v['result']['score_display'] for k, v in data['systems'].items()},
                          'qa_and_evidence_preserved': True, 'delivery_preserved': True}, ensure_ascii=False))
        return
    page_builder.dump(PAGE / 'data.json', data)
    (PAGE / 'index.html').write_text(html, encoding='utf8')
    shutil.copyfile(RULES, PAGE / RULES.name)
    rules = (PAGE / 'SCORING.zh-CN.md').read_text(encoding='utf8')
    rules = re.sub(r'Sol默认与Luna默认的语义、图文及文档由.*?脚本负责时间格式换算、文件检查、字段校验和固定权重汇总。',
        '问答50分与时间证据20分：Sol默认、Luna默认由GPT-6-Astra裁定，两个xhigh运行由GPT-6.1-Sol裁定。手册20分与美观引导10分：四组统一由GPT-6.1-Sol按v3标准验收，逐条核对原始交付，评委不接收旧分数和旧评语。pass全分、partial半分、fail零分；设计五项分别按0—4级换算成2分。脚本负责时间换算、文件检查、字段校验和固定权重汇总。', rules)
    extra_rules = ('\n手册与设计的等级门槛和逐项要求见[完整验收标准](STRICT_MANUAL_RUBRIC.zh-CN.md)。'
              '实际编辑抽查在交付副本中修改原生正文与SVG文字/图形，保存重开并用Word重导出，确认修改出现在PDF中；原封存文件保持不变。抽查不能替代全册内容核验。\n')
    if extra_rules.strip() not in rules:
        rules += extra_rules
    rules = rules.replace('Luna xhigh的Q07、Q10由同一主评按问答、证据、手册事实、图示四类条目分别裁定；各请求提供相同完整证据，随后由固定脚本汇总。其余题目逐题裁定。',
        'Luna xhigh的问答与时间证据Q07、Q10按条目类别独立裁定后脚本汇总。手册各题的事实与图示逐题裁定，全局组织、编辑性及设计分别验收。')
    (PAGE / 'SCORING.zh-CN.md').write_text(rules, encoding='utf8')
    app = (PAGE / 'app.js').read_text(encoding='utf8')
    app = app.replace('主评 ${data.scoring.judge} · Gemini核听音频',
        '问答 ${data.scoring.judge} · 手册 ${data.scoring.manual_judge} · Gemini核听音频')
    (PAGE / 'app.js').write_text(app, encoding='utf8')
    catalog = REPO / 'docs/index.html'
    names = {'sol': 'Sol 默认', 'luna': 'Luna 默认', 'sol-xhigh': 'Sol xhigh', 'luna-xhigh': 'Luna xhigh'}
    status = ' · '.join(names[k] + ' ' + v['result']['score_display'] for k, v in data['systems'].items()) + ' · 同页查看手册与评分'
    text, count = re.subn(r'(<a class="case-card" href="assembly-manual/".*?<div class="status"><span class="status-dot"></span>).*?(</div>)',
                         lambda m: m[1] + status + m[2], catalog.read_text(encoding='utf8'), count=1, flags=re.S)
    assert count == 1
    catalog.write_text(text, encoding='utf8')
    case = REPO / 'cases/assembly-manual'
    shutil.copyfile(RULES, case / RULES.name)
    source = Path(__file__).read_text(encoding='utf8').replace('ROOT = Path(__import__('os').environ['OMNIALE_ORGANIZER_ROOT']).resolve()',
        "ROOT = Path(__import__('os').environ['OMNIALE_ORGANIZER_ROOT']).resolve()")
    (case / Path(__file__).name).write_text(source, encoding='utf8')
    page_builder.audit_public_text([PAGE / n for n in ['data.json', 'index.html', 'app.js', 'SCORING.zh-CN.md', RULES.name]])
    print(json.dumps({'published_files_built': True, 'scores': {k: v['result']['score_display'] for k, v in data['systems'].items()},
                      'preserved_fixed_70_points': True, 'preserved_all_deliveries': True}, ensure_ascii=False))

if __name__ == '__main__':
    main()
