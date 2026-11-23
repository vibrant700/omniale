# 测试与评分运行说明

## Agent 测试

受测模型为 gpt-6.2-astra，推理强度为 xhigh，使用官方 Codex CLI 0.142.4。运行从空会话开始。

在隔离工作区中挂载只读 candidate/，内含题面和五路录像。scratch/ 和 submission/ 可写。把 prompt.txt 原样交给 Codex。成片和时间轴分别保存在 submission/dashboard.mp4 与 submission/timeline.json。

原始启动脚本 bootstrap.py 依赖本次的容器环境。容器内 Codex 在 /opt/codex，启动资源在 /runtime，模型经 BENCH_GATEWAY 提供的 Responses 接口访问。BENCH_LOCAL_TOKEN 在运行时注入。原环境还提供 FFmpeg、ffprobe、Python、NumPy、Pillow 和中文字体。

## 评分

将 evaluate.py 与 grade/reference.json 按下载路径放在同一目录结构中。使用 Python 3.11+、FFmpeg 和 ffprobe，在 evaluate.py 所在目录运行：

    python evaluate.py submission --inspection inspection.json --output score.json

inspection.json 记录原始成片 SHA‑256、五路跳秒帧的时间戳、片尾两张榜的读数和三个成片质量分项。脚本校验记录与待评分成片的哈希，再计算终场输出、终场承伤、同步和成片质量的得分。直接运行 evaluate.py submission 可先查看数值预评。

### inspection.json 字段

- video_sha256 是原始成片的 SHA‑256。
- clock_transition_s 是五个同步抽查点的数组，按照 grade/reference.json 的顺序记录。每项以 xuanran、zhongyi、changsheng、yinuo、dashuai 为键，值为成片中的秒数。缺失的机位使用 null。
- terminal_boards 以 damage_dealt 和 damage_taken 为键。每个榜单按画面从上到下记录五行，每行包含 player、value 和 share_pct。
- visual 的 layout、motion、audio_readability 分别对应布局与信息避让、动态榜流畅度、音轨处理与可读性。

## 文件来源

prompt.txt、bootstrap.py、evaluate.py 与 grade/reference.json 均取自本次测评的归档，文件字节与运行记录中保存的哈希一致。网页预览经过转码，评分基于原始提交文件。
