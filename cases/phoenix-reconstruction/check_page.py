"""Check the published case's resources, media and narrow-screen interactions."""
import argparse
import atexit
from functools import partial
import hashlib
from html.parser import HTMLParser
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import threading
from urllib.parse import unquote, urlsplit
import zipfile

from playwright.sync_api import sync_playwright


class Links(HTMLParser):
    def __init__(self):
        super().__init__(); self.refs = []; self.ids = set()

    def handle_starttag(self, tag, attrs):
        row = dict(attrs)
        if 'id' in row:
            assert row['id'] not in self.ids, f'Duplicate ID: {row["id"]}'
            self.ids.add(row['id'])
        for key in ['src', 'href', 'poster']:
            if row.get(key): self.refs.append(row[key])


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--url', default='http://127.0.0.1:8897/phoenix-reconstruction/')
    p.add_argument('--output', required=True, type=Path)
    p.add_argument('--browser', type=Path)
    p.add_argument('--serve', action='store_true', help='Start a quiet local HTTP server on port 8897')
    args = p.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    site = Path(__file__).resolve().parents[2] / 'docs/phoenix-reconstruction'
    if args.serve:
        class QuietHandler(SimpleHTTPRequestHandler):
            def log_message(self, *args): pass
        server = ThreadingHTTPServer(('127.0.0.1', 8897), partial(QuietHandler, directory=str(site.parent)))
        threading.Thread(target=server.serve_forever, daemon=True).start()
        atexit.register(server.server_close)
        atexit.register(server.shutdown)
    parser = Links(); parser.feed((site / 'index.html').read_text(encoding='utf-8'))
    for ref in parser.refs:
        u = urlsplit(ref)
        if u.scheme or u.netloc: continue
        if not u.path:
            assert not u.fragment or u.fragment in parser.ids, ref
        else:
            assert (site / unquote(u.path)).exists(), ref
    manifest = json.loads((site / 'manifest.json').read_text(encoding='utf-8'))
    for row in manifest['files']:
        assert hashlib.sha256((site / row['file']).read_bytes()).hexdigest() == row['sha256'], row['file']
    score = json.loads((site / 'results/astra62-xhigh/score.json').read_text(encoding='utf-8'))
    audio = json.loads((site / 'results/astra62-xhigh/gemini-neon-audio/audio-score.json').read_text(encoding='utf-8'))
    assert score['scores']['audio'] == audio['total'] == 9
    assert round(score['scores']['full_total_100'], 2) == 34.43
    assert score['maxima'] == {'view_coverage': 30, 'geometry': 30, 'appearance': 30, 'audio': 10, 'non_audio_subtotal': 90, 'full_total_100': 100}
    assert 'LPIPS' not in (site / 'index.html').read_text(encoding='utf-8')
    with zipfile.ZipFile(site / 'assets/agent-input.zip') as z:
        assert len(z.namelist()) == 15
        assert not any(n.endswith(('.png', '.glb', '.blend')) for n in z.namelist())
    report = {'relative_links': 'pass', 'sha256_manifest': 'pass', 'input_boundary': 'pass',
              'scores': 'pass', 'media': [], 'viewports': [], 'console_errors': []}
    with sync_playwright() as pw:
        launch = {'headless': True}
        if args.browser: launch['executable_path'] = str(args.browser)
        browser = pw.chromium.launch(**launch)
        page = browser.new_page(viewport={'width': 1440, 'height': 1000}, device_scale_factor=1)
        page.on('pageerror', lambda e: report['console_errors'].append(str(e)))
        bad = []
        page.on('response', lambda r: bad.append({'status': r.status, 'url': r.url}) if r.status >= 400 else None)
        page.goto(args.url, wait_until='networkidle')
        assert page.title() == '凤凰角色重建与新机位有声动画 · OmniALE'
        page.wait_for_function("document.querySelector('#frame-metrics').textContent.includes('I1')")
        assert page.locator('#scoring').get_by_text('例如', exact=False).count() == 0
        assert page.locator('#astra-score-files a[download]').count() == 6
        assert page.locator('#task-context li').count() == 6
        assert page.locator('#task-context h3').all_text_contents() == ['难点', '可解性']
        assert page.evaluate("document.querySelector('#task-context').previousElementSibling.matches('details')")
        assert page.locator('#task-context li').nth(5).inner_text().startswith('针对本题目标机位的重建，三个参考机位的覆盖是充分的')
        assert page.locator('.leaderboard tbody tr').count() == 1
        assert page.locator('.leaderboard tbody tr td').all_text_contents() == ['xhigh', 'Codex', '15.73', '7.66', '2.03', '9.00', '34.43']
        assert page.locator('#model-select').input_value() == 'astra62-xhigh'
        for button in page.locator('[data-frame]').all():
            button.click()
            frame = int(button.get_attribute('data-frame'))
            assert page.locator('#frame-title').inner_text().startswith(f'帧 {frame:02d}')
            page.wait_for_function("document.querySelector('#frame-image').complete && document.querySelector('#frame-image').naturalWidth > 0")
            assert button.get_attribute('aria-pressed') == 'true'
        page.locator('[data-frame="99"]').focus(); page.keyboard.press('ArrowRight')
        assert page.locator('[data-frame="0"]').get_attribute('aria-pressed') == 'true'
        page.locator('#frame-link').click()
        assert page.locator('dialog').is_visible()
        page.keyboard.press('Escape'); assert not page.locator('dialog').is_visible()
        # Every actual media file must decode and advance; no autoplay is enabled on the page.
        for index in range(page.locator('video,audio').count()):
            state = page.evaluate('''async index => {
                const m = document.querySelectorAll('video,audio')[index];
                m.muted = true; m.load();
                await Promise.race([
                  new Promise((ok, fail) => {
                    if (m.readyState >= 2) return ok();
                    m.addEventListener('loadeddata', ok, {once:true});
                    m.addEventListener('error', () => fail(new Error(m.src + ': media error ' + m.error?.code)), {once:true});
                  }),
                  new Promise((_, fail) => setTimeout(() => fail(new Error('media timeout: '+m.src)), 12000))
                ]);
                await m.play();
                await new Promise((resolve, reject) => {
                    if (m.currentTime > 0) return resolve();
                    const timer = setTimeout(() => reject(new Error('Playback did not advance: '+m.src)), 4000);
                    const advanced = () => {
                        if (m.currentTime > 0) {
                            clearTimeout(timer);
                            m.removeEventListener('timeupdate', advanced);
                            resolve();
                        }
                    };
                    m.addEventListener('timeupdate', advanced);
                });
                const result = {file: new URL(m.src).pathname, duration:m.duration, advanced:m.currentTime > 0,
                  width:m.videoWidth || null, height:m.videoHeight || null};
                m.pause(); m.currentTime = 0;
                return result;
            }''', index)
            assert state['advanced'], state
            if state['width']: assert (state['width'], state['height']) == (1280, 720), state
            report['media'].append(state)
        for width, height in [(1440, 1000), (390, 844), (375, 812)]:
            page.set_viewport_size({'width': width, 'height': height})
            page.goto(args.url, wait_until='networkidle')
            overflow = page.evaluate('document.documentElement.scrollWidth > window.innerWidth')
            assert not overflow, width
            page.screenshot(path=str(args.output / f'page-{width}.png'), full_page=True)
            report['viewports'].append({'width': width, 'horizontal_overflow': False})
        page.set_viewport_size({'width': 1440, 'height': 1000})
        page.locator('#results').scroll_into_view_if_needed()
        page.screenshot(path=str(args.output / 'results-desktop.png'))
        page.goto(args.url.rsplit('phoenix-reconstruction/', 1)[0], wait_until='networkidle')
        assert page.locator('a.case-card[href="phoenix-reconstruction/"]').count() == 1
        assert '06 CASES' in page.inner_text('body')
        # Exercise two independent model states in a browser-only fixture. Never publish it.
        page.goto(args.url, wait_until='networkidle')
        fixture = page.evaluate('''base => {
            for (const original of [...document.querySelectorAll('[data-model-panel]')]) {
                const clone = original.cloneNode(true);
                clone.dataset.modelPanel = 'fixture-second';
                clone.id = original.id === 'model-astra62-xhigh' ? 'model-fixture-second' : original.id + '-qa';
                for (const element of clone.querySelectorAll('[id]')) element.id += '-qa';
                const inspector = clone.querySelector('[data-frame-inspector]');
                if (inspector) {
                    inspector.dataset.modelId = 'fixture-second';
                    inspector.dataset.label = 'Browser fixture';
                    inspector.dataset.frameRoot = 'results/fixture-second/comparison/';
                }
                original.parentElement.append(clone);
            }
            const option = document.createElement('option');
            option.value = 'fixture-second'; option.textContent = 'Browser fixture';
            document.querySelector('#model-select').append(option);
            const baseElement = document.createElement('base'); baseElement.href = base;
            document.head.prepend(baseElement);
            return '<!doctype html>' + document.documentElement.outerHTML;
        }''', args.url)
        fixture_url = args.url + 'model-switch-fixture.html'
        page.route('**/model-switch-fixture.html', lambda route: route.fulfill(body=fixture, content_type='text/html'))
        page.route('**/results/fixture-second/comparison/*', lambda route: route.fulfill(
            path=str(site / 'results/astra62-xhigh/comparison' / Path(urlsplit(route.request.url).path).name)))
        page.goto(fixture_url, wait_until='networkidle')
        page.select_option('#model-select', 'fixture-second')
        assert page.locator('[data-model-panel="fixture-second"]:visible').count() == 3
        assert page.locator('[data-model-panel="astra62-xhigh"]:visible').count() == 0
        second = page.locator('[data-model-panel="fixture-second"] [data-frame-inspector]')
        second.locator('[data-frame="55"]').click()
        assert '帧 55' in second.locator('[data-frame-title]').inner_text()
        assert 'fixture-second/comparison/frame-55.webp' in second.locator('[data-frame-image]').get_attribute('src')
        page.select_option('#model-select', 'astra62-xhigh')
        first = page.locator('[data-model-panel="astra62-xhigh"] [data-frame-inspector]')
        first.locator('[data-frame="22"]').click()
        page.select_option('#model-select', 'fixture-second')
        assert '帧 55' in second.locator('[data-frame-title]').inner_text()
        page.evaluate("location.hash = 'model-astra62-xhigh'")
        page.wait_for_function("document.querySelector('#model-select').value === 'astra62-xhigh'")
        assert '帧 22' in first.locator('[data-frame-title]').inner_text()
        report['multiple_model_selection'] = 'pass: independent panels, frame assets, frame state, hash navigation'
        assert not bad, bad
        assert not report['console_errors'], report['console_errors']
        browser.close()
    (args.output / 'checks.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
