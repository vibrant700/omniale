"""Offline Mandarin voice; each invocation writes a real mono Piper WAV."""
from pathlib import Path
import argparse,os,subprocess,sys
p=argparse.ArgumentParser();p.add_argument('--text',required=True);p.add_argument('--out',required=True);p.add_argument('--length-scale',type=float,default=1.0);a=p.parse_args()
if a.length_scale<=0:raise SystemExit('length-scale must be positive')
home=Path('C:/Users/Public/omniale_tts');out=Path(a.out).resolve();out.parent.mkdir(parents=True,exist_ok=True)
env=os.environ.copy();env.update(PYTHONPATH=str(home/'runtime'),PYTHONIOENCODING='utf-8',PYTHONDONTWRITEBYTECODE='1',ESPEAK_DATA_PATH=str(home/'runtime/piper/espeak-ng-data'),OMNIALE_TTS_TEXT=str(Path(a.text).resolve()),OMNIALE_TTS_OUT=str(out),OMNIALE_TTS_MODEL=str(home/'voice/zh_CN-huayan-medium.onnx'),OMNIALE_TTS_CONFIG=str(home/'voice/zh_CN-huayan-medium.onnx.json'),OMNIALE_ESPEAK_DATA=str(home/'runtime/piper/espeak-ng-data'),OMNIALE_TTS_LENGTH_SCALE=str(a.length_scale))
subprocess.run([sys.executable,str(Path(__file__).with_name('speak_local.py'))],env=env,check=True)
print('TTS_OK',out)
