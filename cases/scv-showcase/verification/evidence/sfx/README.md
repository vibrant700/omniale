# 音效定位与定点评审材料

本目录保存已发布成片的候选定位结果与原混音评审窗口。候选检索只用于寻找值得听看的位置，不直接生成音效语义、音画对齐或混音可辨度的分数。

## 文件与时间映射

- `candidates.json`：18 个波形候选，5 个 high、4 个 medium、9 个 low；置信等级描述模板身份的检索证据，不能当作已确认的音效使用次数。
- `judge-windows.json`：窗口与原片帧号、时间和 48 kHz 音频采样点的映射。
- `judge-media/window-01.mp4` 和 `.flac`：原片 0–11.583333 秒，对应原片帧 `[0,278)`。
- `judge-media/window-02.mp4` 和 `.flac`：原片 12.625–18.25 秒，对应原片帧 `[303,438)`。
- `bgm-alignment.json`：原 BGM 与成片的候选偏移及最终选择，保留重复乐句造成的偏移别名。
- `controls.json`：纯 BGM 假候选对照与独立合成插入回收对照。
- `media-validation.json`：窗口帧数检查，以及 FLAC 解码 PCM 与原混音精确采样切片的一致性校验。

窗口 MP4 保留成片原混音，音频仅作 AAC 编码；FLAC 保留相同原混音切片的无损 PCM。分析残差不作为评审听音轨。候选可能与 BGM 鼓点混淆，也可能漏掉经过变速、移调或处理的声音；完整成片始终是回看依据。

## 重新生成

在复核包根目录安装 `requirements.txt` 中的依赖，并安装 FFmpeg/ffprobe。命令中的音频来自解压后的输入包：

```sh
python scripts/localize_sfx.py --video work/submission/showcase.mp4 --bgm work/agent-input/audio/industrial_pulse.wav --sfx-dir work/agent-input/audio --output work/sfx
```

可用 `--ffmpeg`、`--ffprobe` 指定程序路径；`--skip-media` 只计算候选与窗口映射。固定 v3 窗口协议使用原片 24 fps 帧网格，遇到其他帧率会明确报错，不会静默转换。源音效起点、峰值、有效区间在 `config/sfx-source-annotations.json`，这些是声音素材自身的标注，不是成片的放置答案。

## 方法与记录

`config/sfx-method.frozen.json` 保存冻结的方法定义，SHA256 为 `2bf2d883e212cc4db25e379dd818be7d69d4149660d6d419a3937853f8c702f9`。便携脚本保留其相关、消除背景音乐、排序、置信阈值、去重和窗口算法，改用命令行传入素材与工具路径。原记录里的机器绝对路径已替换为文件名或本目录相对路径；数值、候选、帧号、采样点及媒体内容未变。`candidates.json` 的 `script_sha256` 记录原定位脚本；重新运行时输出当前便携脚本的哈希。

评分时将候选和原混音窗口交给独立的音效对应提示词；音乐编排用另一份提示词观察完整成片与原 BGM，不输入这些候选或音效分数。
