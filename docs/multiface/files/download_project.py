"""Download and reconstruct the original sealed Multiface GPU delivery, unchanged."""
from pathlib import Path
import hashlib,json,os,urllib.request
MANIFEST = json.loads("{\"archive\":\"sealed-delivery.tar.gz\",\"bytes\":258091190,\"sha256\":\"6d96ff7663e4ec9d860e3ce092ba1f79394be04acc24bf7abe44fb21c07cce8d\",\"parts\":[{\"name\":\"sealed-delivery.tar.gz.part01\",\"bytes\":67108864,\"sha256\":\"021f3fe2e9d023143f3ed39c219d425591ef403937134dd8f081562d8fdca1e6\",\"url\":\"https://github.com/vibrant700/omniale/releases/download/multiface-scene-astra62-xhigh-gpu-fresh01-v2/sealed-delivery.tar.gz.part01\"},{\"name\":\"sealed-delivery.tar.gz.part02\",\"bytes\":67108864,\"sha256\":\"e00bdec97c7e7b9a45e69c7d0bd09ee0511d1d54d1b3d92662094a62471bea80\",\"url\":\"https://github.com/vibrant700/omniale/releases/download/multiface-scene-astra62-xhigh-gpu-fresh01-v2/sealed-delivery.tar.gz.part02\"},{\"name\":\"sealed-delivery.tar.gz.part03\",\"bytes\":67108864,\"sha256\":\"290e5dd78dbb456bc1f828b6fea7d6f286632edb169222cc681fb51fdee75d0d\",\"url\":\"https://github.com/vibrant700/omniale/releases/download/multiface-scene-astra62-xhigh-gpu-fresh01-v2/sealed-delivery.tar.gz.part03\"},{\"name\":\"sealed-delivery.tar.gz.part04\",\"bytes\":56764598,\"sha256\":\"11604f85b407976cf31702b3034992ff6a0ba88c67dbeba120e9e960b0e99d45\",\"url\":\"https://github.com/vibrant700/omniale/releases/download/multiface-scene-astra62-xhigh-gpu-fresh01-v2/sealed-delivery.tar.gz.part04\"}],\"url\":\"https://github.com/vibrant700/omniale/releases/tag/multiface-scene-astra62-xhigh-gpu-fresh01-v2\",\"original_delivery_files\":119}")
folder=Path('multiface-astra62-gpu');folder.mkdir(exist_ok=True)
def digest(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
 return h.hexdigest()
for part in MANIFEST['parts']:
 p=folder/part['name']
 if p.exists() and p.stat().st_size==part['bytes'] and digest(p)==part['sha256']:continue
 temp=p.with_suffix(p.suffix+'.download')
 print('Downloading',part['name'],flush=True)
 with urllib.request.urlopen(part['url'],timeout=300) as response,temp.open('wb') as out:
  for block in iter(lambda:response.read(1024*1024),b''):out.write(block)
 assert temp.stat().st_size==part['bytes'] and digest(temp)==part['sha256'],'Part hash mismatch'
 os.replace(temp,p)
archive=folder/MANIFEST['archive']
if not archive.exists() or digest(archive)!=MANIFEST['sha256']:
 temp=archive.with_suffix(archive.suffix+'.joining')
 with temp.open('wb') as out:
  for part in MANIFEST['parts']:
   with (folder/part['name']).open('rb') as f:
    for block in iter(lambda:f.read(1024*1024),b''):out.write(block)
 assert temp.stat().st_size==MANIFEST['bytes'] and digest(temp)==MANIFEST['sha256'],'Archive hash mismatch'
 os.replace(temp,archive)
print('Verified original archive:',archive.resolve())
print('Extract this tar.gz, keep scene.blend, build.py and assets together, then open scene.blend in Blender 5.3.')
