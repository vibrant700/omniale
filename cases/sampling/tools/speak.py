"""Explicit network-backed TTS entry point; preflight before assessment."""
import argparse
import asyncio
from pathlib import Path

async def main():
    import edge_tts
    p=argparse.ArgumentParser()
    p.add_argument('--text',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--voice',default='zh-CN-XiaoxiaoNeural')
    a=p.parse_args()
    a.out.parent.mkdir(parents=True,exist_ok=True)
    await edge_tts.Communicate(a.text.read_text(encoding='utf-8'),a.voice).save(str(a.out))

if __name__=='__main__':asyncio.run(main())
