# SCV 机甲资产重建与有声展示片

根据六方向彩色参考图，使用 Blender 重建可编辑机甲资产，并将指定配乐、whoosh／hit／drop 编排为有声作品集展示片。

- 展示页：https://vibrant700.github.io/omniale/scv-showcase/
- 题面：[TASK.md](./TASK.md)
- 计分说明：[SCORING.md](./SCORING.md)
- 评分复核：[使用说明与源码](./verification-v3/README.md) · [下载复核包](../../docs/scv-showcase/assets/scoring-verification-v3.zip)
- 公开输入包：[agent-input.zip](../../docs/scv-showcase/assets/agent-input.zip)
- 模型交付与成绩：[results.json](../../docs/scv-showcase/results.json)

当前同时展示 Astra 6.2 与 Sol 6.2 的独立 GPU 从头实验，均为 xhigh＋官方 Codex＋RTX 4090 D。成绩表始终展示两者，切换模型可同步查看各自成片、工程下载、运行信息、执行过程、六视图与失败分析。默认展示 Astra。

| 模型 | 结构／30 | 外观／30 | 关键细节／30 | 音乐／5 | 音效／5 | 总分／100 |
|---|---:|---:|---:|---:|---:|---:|
| Astra 6.2 xhigh | 19.85 | 5.54 | 0 | 5 | 5 | **35.38** |
| Sol 6.2 xhigh | 16.78 | 6.12 | 0 | 5 | 5 | **32.90** |

Astra：42分31秒、152次工具调用、71次模型响应，交付27秒、1600×900、24fps有声片。Sol：37分16秒、194次工具调用、112次模型响应，交付28.58秒、1920×1080、24fps有声片。关键细节与音画由 Gemini 4 Neon 评定。

`gpu-page.html` 保留 Astra 单模型内容作为构建输入；当前页面由 `build_comparison_page.py --sol-run <本地Sol实验目录>` 整理两模型内容，交互与样式源文件为 `comparison-app.js`、`comparison.css`。需要 Pillow。该脚本不调用被测模型；原始私有请求、会话与服务器信息不公开。`build_gpu_page.py` 是单模型准备入口，检测到双模型页面时会拒绝覆盖。

Sol 原成片、资产、工程与 ZIP 位于 `docs/scv-showcase/assets/models/sol62-xhigh/`，Astra 原有下载路径保留。`?model=sol62-xhigh` 可直接打开 Sol 内容；切换后所有镜头定位使用对应成片的时间轴。

外观30分按 `30×clip(六视图平均SSIM,0,1)` 约定换算，不代表外观还原百分比。当前评分协议为 `scv-showcase-ssim-v3`。历史 `verification/`、`verification-v2/` 及旧下载包保留原规则和原分数，不用于当前结果。

参考资产：JohnMesplay，SCV，CC BY 4.0。六向参考图经过坐标和摄影机／灯光规范化。配乐与三种音效为题目原创合成音频，CC0。页面使用的客户端交付保留其原始署名。
