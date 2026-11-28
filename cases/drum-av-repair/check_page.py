"""Verify public references, score wiring, packages and media metadata."""
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import urlsplit,unquote
import argparse
import json
import re
import subprocess
import zipfile

HERE=Path(__file__).resolve().parent;REPO=HERE.parents[1];SITE=REPO/'docs/drum-av-repair'

class Links(HTMLParser):
    def __init__(self):super().__init__();self.targets=[];self.ids=set();self.text=[]
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if a.get('id'):self.ids.add(a['id'])
        for k in ['href','src','poster']:
            if a.get(k):self.targets.append(a[k])
    def handle_data(self,data):self.text.append(data)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--ffprobe',type=Path,required=True);args=ap.parse_args()
    doc=(SITE/'index.html').read_text(encoding='utf-8');links=Links();links.feed(doc)
    for target in links.targets:
        u=urlsplit(target)
        if u.scheme:continue
        if not u.path:assert not u.fragment or u.fragment in links.ids,target
        else:assert (SITE/unquote(u.path)).exists(),target
    assert doc.index('本题难点')<doc.index('可解性')<doc.index('id="scoring"')
    assert not re.search(r'重建.{0,12}90|待人工|有待.{0,8}复核|待定|@@',doc)
    data=json.loads((SITE/'assets/case-data.json').read_text(encoding='utf-8'))
    assert data['total']==57.02 and len(data['regions'])==5
    for r in data['regions']:
        assert abs(sum(r['scores'][k] for k in ['correspondence','blending','quality'])-r['scores']['total'])<.001
        for p in r['media'].values():assert (SITE/p).exists(),p
    with zipfile.ZipFile(SITE/'assets/candidate.zip') as z:
        assert set(z.namelist())=={'candidate/TASK.md','candidate/TOOLS.md','candidate/media/test_corrupted.mp4','candidate/media/test_corrupted.wav'}
    with zipfile.ZipFile(SITE/'assets/reaper-project.zip') as z:
        project=z.read('repair.rpp').decode('utf-8');names=set(z.namelist())
        refs=re.findall(r'^\s*FILE\s+"([^"]+)"',project,re.M)
        assert len(refs)==173
        for ref in refs:assert ref in names and not ref.startswith(('/', '\\')) and not re.match('^[A-Za-z]:',ref),ref
    media=[]
    for p in [SITE/'assets/input.mp4',SITE/'assets/repaired-preview.mp4',*sorted((SITE/'assets/clips').glob('*.mp4'))]:
        cp=subprocess.run([str(args.ffprobe),'-v','error','-show_entries','format=duration:stream=codec_type,codec_name,sample_rate,channels','-of','json',str(p)],capture_output=True,check=True)
        info=json.loads(cp.stdout);streams=info['streams'];audio=[s for s in streams if s['codec_type']=='audio']
        assert len(audio)==1 and audio[0]['codec_name']=='aac' and audio[0]['sample_rate']=='48000' and audio[0]['channels']==2,p
        media.append(dict(file=p.name,duration=info['format']['duration'],audio='48k stereo AAC'))
    assert len(media)==17
    assert all(p.stat().st_size<100*1024**2 for p in SITE.rglob('*') if p.is_file())
    print(json.dumps(dict(passed=True,relative_targets=len(links.targets),project_references=173,candidate_files=4,browser_videos=media),ensure_ascii=False,indent=2))

if __name__=='__main__':main()
