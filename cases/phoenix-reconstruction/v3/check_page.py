"""Verify public-file boundaries, media playback, model controls and mobile layout."""
import argparse
import atexit
from functools import partial
import hashlib
from html.parser import HTMLParser
from http.server import SimpleHTTPRequestHandler,ThreadingHTTPServer
import json
from pathlib import Path
import re
import sys
import threading
from urllib.parse import unquote,urlsplit
import zipfile


class Links(HTMLParser):
    def __init__(self):super().__init__();self.refs=[];self.ids=set()
    def handle_starttag(self,tag,attrs):
        row=dict(attrs)
        if row.get('id'):
            assert row['id'] not in self.ids,row['id'];self.ids.add(row['id'])
        self.refs += [row[k] for k in ['href','src','poster'] if row.get(k)]


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--url',default='http://127.0.0.1:8898/phoenix-reconstruction/')
    p.add_argument('--repo',type=Path,default=Path(__file__).resolve().parents[3])
    p.add_argument('--output',required=True,type=Path)
    p.add_argument('--playwright-runtime',type=Path)
    p.add_argument('--browser',required=True,type=Path)
    p.add_argument('--serve',action='store_true',help='Serve this checkout on an automatically selected local port')
    args=p.parse_args();args.output.mkdir(parents=True,exist_ok=True)
    if args.serve:
        class QuietHandler(SimpleHTTPRequestHandler):
            def log_message(self,*args):pass
        server=ThreadingHTTPServer(('127.0.0.1',0),partial(QuietHandler,directory=str(args.repo/'docs')))
        threading.Thread(target=server.serve_forever,daemon=True).start()
        atexit.register(server.server_close);atexit.register(server.shutdown)
        args.url=f'http://127.0.0.1:{server.server_port}/phoenix-reconstruction/'
    if args.playwright_runtime:sys.path.insert(0,str(args.playwright_runtime))
    from playwright.sync_api import sync_playwright
    site=args.repo/'docs/phoenix-reconstruction';text=(site/'index.html').read_text(encoding='utf-8')
    assert not (site/'v2').exists() and not (site/'v3/assets').exists() and not (site/'v3/results').exists()
    assert all(v not in text for v in ['V1','V2','V3'])
    assert 'location.replace' not in text
    assert 'location.replace' in (site/'v3/index.html').read_text(encoding='utf-8')
    links=Links();links.feed(text)
    for ref in links.refs:
        u=urlsplit(ref)
        if u.scheme or u.netloc:continue
        if u.path:assert (site/unquote(u.path)).exists(),ref
        else:assert not u.fragment or u.fragment in links.ids,ref
    manifest=json.loads((site/'manifest.json').read_text(encoding='utf-8'))
    for row in manifest['files']:
        path=site/row['file'];assert path.stat().st_size==row['bytes'] and hashlib.sha256(path.read_bytes()).hexdigest()==row['sha256'],row['file']
    score=json.loads((site/'results/astra62-xhigh/score.json').read_text(encoding='utf-8'))
    assert score['task_weights']=={'view_coverage':30,'geometry':30,'appearance':20,'audio':20}
    assert score['result_scope']=='objective_metrics_and_user_supplied_audio_review'
    assert set(score['scores'])=={'view_coverage','geometry','appearance','non_audio_subtotal','audio','full_total_100'}
    assert round(score['scores']['non_audio_subtotal'],2)==25.25
    assert score['scores']['audio']==14 and round(score['scores']['full_total_100'],2)==39.25
    assert sum(score['scores'][k] for k in ['view_coverage','geometry','appearance','audio'])==score['scores']['full_total_100']
    audio_dir=site/'results/astra62-xhigh/gemini-neon-audio'
    audio=json.loads((audio_dir/'audio-score.json').read_text(encoding='utf-8'))
    original=json.loads((audio_dir/'audio-review-original.json').read_text(encoding='utf-8'))
    assert original['total']==7 and audio['total']==sum(x['score'] for x in audio['items'])==14
    assert hashlib.sha256((audio_dir/'audio-review-original.json').read_bytes()).hexdigest()==audio['original_report_sha256']
    assert audio['human_review_confirmed'] is False and audio['calibration_check']['controls_run'] is False
    assert not any(s in text for s in ['初评','待定','二次重测','尚未运行模型实验'])
    assert not list(site.rglob('*.glb'))
    for path in site.rglob('*'):
        if path.suffix.lower() in ['.json','.md','.html','.js','.css','.txt']:
            body=path.read_text(encoding='utf-8',errors='replace')
            assert not re.search(r'\bsk-[A-Za-z0-9_-]{20,}|connect\.cqa1|ssh -p\s*\d+|BEGIN (?:RSA |OPENSSH )?PRIVATE KEY',body),path
    inputs=json.loads((site/'assets/input-manifest.json').read_text(encoding='utf-8'))
    with zipfile.ZipFile(site/'assets/agent-input.zip') as z:
        assert len(z.namelist())==10 and set(z.namelist())==set(inputs['files'])
        for name in z.namelist():
            assert not name.endswith(('.wav','.blend','.glb','.png','.npz'))
            assert hashlib.sha256(z.read(name)).hexdigest()==inputs['files'][name]['sha256']
    with zipfile.ZipFile(site/'results/astra62-xhigh/delivery.zip') as z:
        assert len(z.namelist())==17
        for name,digest in score['submission_files_sha256'].items():assert hashlib.sha256(z.read(name)).hexdigest()==digest
    report={'links':'pass','file_hashes':'pass','input_boundary':'pass','original_delivery':'pass','score_scope':'pass','media':[],'viewports':[],'console_errors':[]}
    with sync_playwright() as pw:
        browser=pw.chromium.launch(headless=True,executable_path=str(args.browser))
        page=browser.new_page(viewport={'width':1440,'height':1000},device_scale_factor=1)
        page.on('pageerror',lambda e:report['console_errors'].append(str(e)))
        bad=[];page.on('response',lambda r:bad.append({'status':r.status,'url':r.url}) if r.status>=400 else None)
        page.goto(args.url,wait_until='domcontentloaded')
        assert page.title()=='凤凰角色重建与自主拟音 · OmniALE'
        page.wait_for_function("document.querySelector('[data-frame-metrics]').textContent.includes('I1')")
        assert page.locator('#task-context li').count()==6
        assert page.evaluate("document.querySelector('#task-context').previousElementSibling.matches('details')")
        assert page.locator('#task-context li').nth(5).inner_text().startswith('针对本题目标机位的重建，三个参考机位的覆盖是充分的')
        assert page.locator('.leaderboard tbody tr td').all_text_contents()==['xhigh','Codex','15.75','7.95','1.55','14.00','39.25']
        assert page.locator('#model-select option').count()==1
        page.select_option('#model-select','astra62-xhigh')
        assert page.locator('[data-model-panel]:visible').count()==3
        for button in page.locator('[data-frame]').all():
            button.click();frame=int(button.get_attribute('data-frame'))
            assert page.locator('[data-frame-title]').inner_text().startswith(f'帧 {frame:02d}')
            page.wait_for_function("document.querySelector('[data-frame-image]').complete && document.querySelector('[data-frame-image]').naturalWidth>0")
            assert button.get_attribute('aria-pressed')=='true'
        page.locator('[data-frame="179"]').focus();page.keyboard.press('ArrowRight')
        assert page.locator('[data-frame="0"]').get_attribute('aria-pressed')=='true'
        page.locator('[data-frame-link]').click();assert page.locator('dialog').is_visible()
        page.keyboard.press('Escape');assert not page.locator('dialog').is_visible()
        assert page.locator('.result-downloads a[download]').count()==6
        assert page.locator('#results').get_by_text('音效逐项评分 · 14 / 20',exact=True).count()==1
        assert page.locator('.result-scope').inner_text().endswith('声音报告未执行同步对照校准，未经人工复核。')
        for index in range(page.locator('video,audio').count()):
            state=page.evaluate('''async index => {
              const m=document.querySelectorAll('video,audio')[index];m.muted=true;m.load();
              await Promise.race([new Promise((ok,fail)=>{if(m.readyState>=2)return ok();m.addEventListener('loadeddata',ok,{once:true});m.addEventListener('error',()=>fail(new Error(m.src+': '+m.error?.code)),{once:true})}),new Promise((_,fail)=>setTimeout(()=>fail(new Error('media timeout '+m.src)),15000))]);
              await m.play();await new Promise((ok,fail)=>{const deadline=setTimeout(()=>fail(new Error('not advancing '+m.src)),5000);const advance=()=>{if(m.currentTime>0){clearTimeout(deadline);m.removeEventListener('timeupdate',advance);ok()}};m.addEventListener('timeupdate',advance);advance()});
              const result={file:new URL(m.src).pathname,duration:m.duration,advanced:m.currentTime>0,width:m.videoWidth||null,height:m.videoHeight||null};m.pause();m.currentTime=0;return result;
            }''',index)
            assert state['advanced'] and abs(state['duration']-6)<0.05,state
            if state['width']:assert (state['width'],state['height'])==(1280,720),state
            report['media'].append(state)
        for width,height in [(1440,1000),(390,844),(375,812)]:
            page.set_viewport_size({'width':width,'height':height});page.goto(args.url,wait_until='domcontentloaded')
            assert not page.evaluate('document.documentElement.scrollWidth>window.innerWidth'),width
            page.screenshot(path=str(args.output/f'page-{width}.png'),full_page=True)
            report['viewports'].append({'width':width,'horizontal_overflow':False})
        page.set_viewport_size({'width':1440,'height':1000});page.goto(args.url,wait_until='domcontentloaded')
        page.locator('#results').scroll_into_view_if_needed();page.screenshot(path=str(args.output/'results-desktop.png'))
        root_url=args.url
        page.goto(root_url+'v3/',wait_until='domcontentloaded')
        page.wait_for_url('**/phoenix-reconstruction/',wait_until='domcontentloaded')
        page.wait_for_function("document.querySelector('.score-display strong')?.textContent==='39.25'")
        assert page.locator('.site-return a').count()==1
        assert page.request.get(root_url+'v2/index.html').status==404
        assert page.request.get(root_url+'v3/assets/TASK.md').status==404
        report['current_only_entry']='pass'
        assert not report['console_errors'],report['console_errors'];assert not bad,bad
        browser.close()
    (args.output/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'media_played':len(report['media']),'viewports':report['viewports'],'console_errors':report['console_errors'],'status':'passed'},ensure_ascii=True))

if __name__=='__main__':main()
