"""Acquire the public game-one broadcast, retaining public provenance only."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import time
import urllib.parse
import urllib.request

HERE = Path(__file__).resolve().parent
ARCHIVE = HERE / 'grade/commentary'
BVID, CID = 'BV1tyH76XEgz', 42460709754


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--extract', nargs=2, type=float, metavar=('START', 'DURATION'))
    parser.add_argument('--ffmpeg', default='ffmpeg')
    args = parser.parse_args()
    ARCHIVE.mkdir(parents=True, exist_ok=True)
    target = ARCHIVE / 'official-g1-full.mp4'
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    headers = {'User-Agent': 'Mozilla/5.0', 'Referer': 'https://www.bilibili.com/'}
    if not target.exists():
        params = urllib.parse.urlencode(dict(bvid=BVID, cid=CID, qn=16, fnval=0, platform='html5'))
        with opener.open(urllib.request.Request('https://api.bilibili.com/x/player/playurl?'+params, headers=headers), timeout=35) as response:
            data = json.load(response)
        assert data['code'] == 0
        info = data['data']
        assert len(info['durl']) == 1
        media = info['durl'][0]
        urls = [media['url'], *(media.get('backup_url') or [])]
        partial = target.with_suffix('.partial')
        with partial.open('wb') as writer:
            for start in range(0, media['size'], 4*2**20):
                end = min(media['size']-1, start+4*2**20-1)
                for attempt in range(6):
                    try:
                        request = urllib.request.Request(urls[attempt % len(urls)], headers={**headers, 'Range': f'bytes={start}-{end}'})
                        with opener.open(request, timeout=35) as response:
                            assert response.status == 206
                            chunk = response.read()
                        assert len(chunk) == end-start+1
                        writer.write(chunk)
                        break
                    except Exception:
                        if attempt == 5:
                            raise RuntimeError('Public media range could not be downloaded') from None
                        time.sleep(1)
                print(json.dumps({'downloaded_bytes': end+1, 'total_bytes': media['size']}), flush=True)
        partial.replace(target)
    with target.open('rb') as reader:
        digest = hashlib.file_digest(reader, 'sha256').hexdigest()
    receipt = {'source_url': f'https://www.bilibili.com/video/{BVID}/?p=1', 'bvid': BVID,
               'cid': CID, 'part': 1, 'file': target.name, 'bytes': target.stat().st_size, 'sha256': digest}
    if args.extract:
        start, duration = args.extract
        (HERE / 'input').mkdir(exist_ok=True)
        output = HERE / 'input/commentary.m4a'
        command = [args.ffmpeg, '-y', '-hide_banner', '-loglevel', 'error', '-ss', str(start),
                   '-i', str(target), '-t', str(duration), '-vn', '-map', '0:a:0', '-c:a', 'copy', str(output)]
        subprocess.run(command, check=True)
        receipt['extraction'] = {'source_start_s': start, 'duration_s': duration, 'codec': 'AAC stream copy',
            'file': 'input/commentary.m4a', 'bytes': output.stat().st_size,
            'sha256': hashlib.sha256(output.read_bytes()).hexdigest()}
    (ARCHIVE / 'source.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(receipt), flush=True)


if __name__ == '__main__':
    main()
