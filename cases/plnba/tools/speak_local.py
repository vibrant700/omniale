"""Piper bridge using environment variables so Windows Unicode paths are not CLI arguments."""
import os
import wave
from piper import PiperVoice
from piper.config import SynthesisConfig

text_path = os.environ["OMNIALE_TTS_TEXT"]
out_path = os.environ["OMNIALE_TTS_OUT"]
model_path = os.environ["OMNIALE_TTS_MODEL"]
config_path = os.environ["OMNIALE_TTS_CONFIG"]
espeak_path = os.environ["OMNIALE_ESPEAK_DATA"]
length_scale = float(os.environ.get("OMNIALE_TTS_LENGTH_SCALE", "1.0"))

with open(text_path, "r", encoding="utf-8-sig") as text_file:
    text = text_file.read().strip()
if not text:
    raise SystemExit("TTS input text is empty")

voice = PiperVoice.load(model_path, config_path=config_path, espeak_data_dir=espeak_path)
with wave.open(out_path, "wb") as wav_file:
    voice.synthesize_wav(text, wav_file, syn_config=SynthesisConfig(length_scale=length_scale))
