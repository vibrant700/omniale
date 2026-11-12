# 可用工具

工作目录是本轮 workspace，公开题包在 candidate/，最终写到 output/，中间文件写 scratch/。runtime/profile.json 给出本机通用运行时路径，不包含凭据。run 工具会将 python、ffmpeg、ffprobe、melt 映射到对应可执行文件。

## 离线普通话 TTS

`python candidate/input/tools/speak.py --text scratch/words.txt --out scratch/voice.wav --length-scale 1.0`

输入 UTF-8 文本文件，支持中文标点；只有固定 huayan 中文音色，无需网络或密钥。length-scale 越大越慢，必须为正数。初始输出是模型原生单声道 WAV；你需要将最终交付转换成 48k 双声道、安排位置及留白并处理响度。可以按句合成、修改断句、试听后重做，没有额外调用次数收费；总运行预算适用。

## 视频观察和音频检查

Python 可用 OpenCV、Pillow、numpy、PyAV、faster-whisper。FFmpeg 可以逐帧提取画面；view_image 发送实际图片给你。listen_audio 将本地音频无损发送给音频观察工具，返回听到的文本及声音问题，用于检查听到的内容和声音表现。可以用工具提取短音频检查，不提供现成解说答案。

## Shotcut / MLT

已提供官方 Shotcut 26.9.27 Windows 便携版，melt 为原生 MLT 渲染器。`melt input.mlt -consumer avformat:output.mp4 vcodec=libx264 crf=20 preset=fast acodec=aac ab=192k ar=48000 channels=2 threads=4 real_time=-4`。用完整路径或包内相对路径；输出工程必须在交付包内可移植。运行原生导出前自行设好 MLT 中的视频、音频及字幕轨，勿只导入最终 MP4。

MLT 的时间单位可用整数帧，60 帧为 1 秒；entry 的 in/out 包括端点。初始工程总长159秒，只有中性章节、原速视频、空配音/字幕轨。你可以自行改轨道、切片、旁白、字幕、暂停和回放。dynamictext filter 参数包括 argument、family、size、geometry、fgcolour、bgcolour、outlinecolour、outlinewidth。字体 Microsoft YaHei 可用于中文。音频 playlist 与画面轨需保持正确混合/隐藏设置。

FFmpeg 可供分析、抽帧、转码、音量处理和字幕生成。可直接使用 MLT 原生导出，也可以结合其他工具完成制作。请等待真实渲染完成，不提交仍在运行的文件。
