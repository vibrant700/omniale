"""Download and join the complete, sealed Multiface Blender submission (Python 3)."""
import hashlib,json,urllib.request,os
from pathlib import Path
BASE='https://github.com/vibrant700/omniale/releases/download/multiface-sol-xhigh-v1/'
MANIFEST={'archive': 'multiface-sol-xhigh-submission.zip', 'bytes': 444241281, 'sha256': '92fb19143da82f0ce7399e4c0bc78185e7e6e959611132a7667f90f678b2487e', 'parts': [{'name': 'multiface-sol-xhigh-submission.zip.part01', 'bytes': 67108864, 'sha256': '01f91573a6287cf98e528bc8d3f7a6dad80774630a3b363da16b4264248f6601'}, {'name': 'multiface-sol-xhigh-submission.zip.part02', 'bytes': 67108864, 'sha256': 'bb3548296413ef499579b236373ed2a35247dbea3d46c95299cfd42d40f4c256'}, {'name': 'multiface-sol-xhigh-submission.zip.part03', 'bytes': 67108864, 'sha256': 'd0ce485ff0cec846c1923625da70608ac7186f42b3deee166f6b22a0a0d969e0'}, {'name': 'multiface-sol-xhigh-submission.zip.part04', 'bytes': 67108864, 'sha256': '70b454df36942228890efd25ed6c6907412b7f269a38fb4c0841bc0ffd5e7058'}, {'name': 'multiface-sol-xhigh-submission.zip.part05', 'bytes': 67108864, 'sha256': '9f684ef1588110aa9b30a49ce78a0090e9511ab1ec115c0e1709b4fd27973720'}, {'name': 'multiface-sol-xhigh-submission.zip.part06', 'bytes': 67108864, 'sha256': 'c0c137c15fae7a75083608bcef914137a9c6fc31c611cd883ff64f64ed19cc16'}, {'name': 'multiface-sol-xhigh-submission.zip.part07', 'bytes': 41588097, 'sha256': '1968bda03683a90419c2bcc503fe2d086babfa231eb1e43dc40ac36f14a6ffcc'}]}
folder=Path('multiface-project-download');folder.mkdir(exist_ok=True)
def digest(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  while b:=f.read(1024*1024):h.update(b)
 return h.hexdigest()
for part in MANIFEST['parts']:
 p=folder/part['name']
 if p.exists() and digest(p)==part['sha256']:continue
 temp=p.with_name(p.name+'.download')
 print('Downloading',part['name'],flush=True)
 with urllib.request.urlopen(BASE+part['name'],timeout=120) as response,temp.open('wb') as f:
  while b:=response.read(1024*1024):f.write(b)
 if temp.stat().st_size!=part['bytes'] or digest(temp)!=part['sha256']:raise RuntimeError('Download hash mismatch: '+part['name'])
 os.replace(temp,p)
archive=folder/MANIFEST['archive']
if not archive.exists() or digest(archive)!=MANIFEST['sha256']:
 temp=archive.with_name(archive.name+'.assembling')
 with temp.open('wb') as out:
  for part in MANIFEST['parts']:
   with (folder/part['name']).open('rb') as f:
    while b:=f.read(1024*1024):out.write(b)
 if digest(temp)!=MANIFEST['sha256']:raise RuntimeError('Archive hash mismatch')
 os.replace(temp,archive)
print('Verified ZIP:',archive.resolve())
print('Extract the ZIP, then open submission/scene.blend with Blender 5.3.')
