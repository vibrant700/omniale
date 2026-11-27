# 本次可用环境

你在 Linux 工作目录中执行任务，`candidate/` 是只读输入，`scratch/` 用于中间文件，`submission/` 用于最终交付。

- Blender 4.5.3 LTS：`blender`。RTX 4090 D，24GB 显存，支持 Cycles CUDA；可通过脚本访问。
- REAPER 7.86 Linux x86_64：`reaper`。包装器自动启动独立虚拟显示，可运行原生 Lua ReaScript、保存和重新打开 `.rpp`，并使用内置效果器。已实测音频导入、ReaEQ 和六秒 WAV 离线导出。
- Python 3（NumPy、Pillow、SciPy、SoundFile）、FFmpeg、ffprobe、curl、wget。
- 可访问公共互联网，自行检索、下载声音素材并记录来源与许可。不得检索或获取本题原始模型和动画。

REAPER 执行入口（路径按实际工作目录替换）：

```sh
reaper -newinst -nosplash -cfgfile "$HOME/reaper-agent.ini" /absolute/path/to/script.lua
reaper -newinst -nosplash -cfgfile "$HOME/reaper-agent.ini" -renderproject /absolute/path/to/project.rpp
```

`$HOME/reaper-agent.ini` 已准备好。请保持工程、源素材和导出结果可重定位。支持使用界面或脚本，不限定操作方式；软件入口不提供声音答案。

可利用 REAPER 或 FFmpeg 解码、分段、导出，检查波形和频谱，使用系统提供的媒体入口检查可支持的媒体。当前 Codex CLI 的原生媒体工具以实际工具清单为准，不声称具有未提供的音频感知工具。
