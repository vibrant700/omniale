"""Check V2 resource paths, input contents, metadata and absence of private reference data."""
from html.parser import HTMLParser
import hashlib
import json
from pathlib import Path
from urllib.parse import unquote,urlparse
import zipfile

ROOT=Path(__file__).resolve().parents[3]
SITE=ROOT/'docs/phoenix-reconstruction/v2'
class Page(HTMLParser):
    def __init__(self):super().__init__();self.links=[];self.ids=[];self.videos=[];self.audio=[]
    def handle_starttag(self,tag,attrs):
        data=dict(attrs)
        if 'id' in data:self.ids.append(data['id'])
        for attr in ['href','src','poster']:
            if attr in data:self.links.append(data[attr])
        if tag=='video':self.videos.append(data)
        if tag=='audio':self.audio.append(data)
p=Page();text=(SITE/'index.html').read_text(encoding='utf-8');p.feed(text)
assert '<!--' not in text and len(p.ids)==len(set(p.ids))
assert len(p.videos)==3 and len(p.audio)==5
for link in p.links:
    url=urlparse(link)
    if url.scheme or not url.path:continue
    path=(SITE/unquote(url.path)).resolve()
    assert path.is_relative_to(ROOT.resolve()) and path.exists(),link
for v in p.videos:
    assert all(key in v for key in ['controls','playsinline','poster','src'])
assert '新版尚未运行模型实验' in text and '34.43' not in text and '100 帧' not in text and '3.33 秒' not in text
protocol=json.loads((SITE/'assets/protocol.json').read_text(encoding='utf-8'))
assert protocol['frames']==[0,20,40,60,80,99,119,139,159,179] and protocol['frame_count']==180
assert protocol['weights']=={'view_coverage':30,'geometry':30,'appearance':30,'audio':10}
with zipfile.ZipFile(SITE/'assets/agent-input.zip') as z:
    assert z.testzip() is None and len(z.namelist())==15
    assert len([n for n in z.namelist() if n.endswith('.mp4')])==3
    assert not any(n.lower().endswith(('.blend','.glb','.png','.jpg','.npz')) or 'T1.mp4' in n for n in z.namelist())
    timeline=json.loads(z.read('timeline.json'));assert timeline['frame_count']==180 and timeline['duration_s']==6
    assert len(timeline['frames'])==180 and all(set(row)=={'index','blender_frame','time_s'} for row in timeline['frames'])
    assert not any(any(word in n.lower() for word in ['private','motion-profile','evaluation','credentials']) for n in z.namelist())
manifest=json.loads((SITE/'manifest.json').read_text(encoding='utf-8'))
for row in manifest['files']:
    file=SITE/row['path'];assert file.stat().st_size==row['bytes'] and hashlib.sha256(file.read_bytes()).hexdigest()==row['sha256']
assert 'phoenix-reconstruction/v2/' in (ROOT/'docs/index.html').read_text(encoding='utf-8')
print(json.dumps({'resource_paths_valid':True,'input_files':15,'private_truth_absent':True,'video_players':3,'audio_players':5,'manifest_files':len(manifest['files']),'V2_model_runs':0},indent=2))
