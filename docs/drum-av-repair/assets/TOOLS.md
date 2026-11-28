# 可用工具

- `ffmpeg`, `ffprobe`, `python`：PATH 可直接使用。
- Python：NumPy、SciPy、Pillow、soundfile；可用标准库 wave/json。
- 原生 `view_image`：先抽帧或制作联系表，再打开真实图像。
- 固定媒体 MCP `listen_audio(path)`：传入公开素材或 `scratch/`、`submission/` 中实际音频的路径。长音轨自行截短到 30 秒以内，观察器只收到此片段。观察输出不是标签真值，不应当作绝对准确。
- `/opt/reaper/reaper -help` 查看官方 CLI；`reaper-headless -nosplash -newinst -cfgfile /workspace/scratch/reaper/reaper.ini your_script.lua` 在 Xvfb 下运行 Lua ReaScript。REAPER 可用评估模式，未修改许可系统。用 `reaper.GetAppVersion()` 核实版本。
- ReaScript 可以 `InsertMedia`、设置 item 位置和长度、插入 track、保存 RPP、渲染并退出。项目素材放相对路径，离线渲染前核验输出。

REAPER 项目也可先用文本生成，再由 REAPER 实际加载/渲染校验。FFmpeg 与 Python 可辅助剪切、合成，选择工作路线由你决定。没有预先安装可以从无声视频直接生成鼓声的专用模型。
