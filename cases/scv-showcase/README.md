# SCV 机甲资产重建与有声展示片

根据六方向彩色参考图，使用 Blender 重建可编辑机甲资产，并将指定配乐、whoosh／hit／drop 编排为有声作品集展示片。

- 展示页：https://vibrant700.github.io/omniale/scv-showcase/
- 题面：[TASK.md](./TASK.md)
- 计分说明：[SCORING.md](./SCORING.md)
- 评分复核：[使用说明与源码](./verification-v3/README.md) · [下载复核包](../../docs/scv-showcase/assets/scoring-verification-v3.zip)
- 公开输入包：[agent-input.zip](../../docs/scv-showcase/assets/agent-input.zip)
- 模型交付与成绩：[results.json](../../docs/scv-showcase/results.json)

当前展示 Astra 6.2 xhigh＋官方 Codex 的 GPU 从头实验：RTX 4090 D、Cycles CUDA，42分31秒、152次工具调用、71次模型响应；交付27秒、1600×900、24fps有声片与独立资产。得分 **35.38 / 100**：结构19.85、外观5.54、关键细节0、音乐5、音效5。关键细节与音画由 Gemini 4 Neon 评定。

`gpu-page.html` 为当前页面模板；`build_gpu_page.py --run <本地实验目录>` 整理已完成交付、固定六视图及经接受的评分结果，生成页面媒体、数据与下载包，不调用被测模型。需要 Pillow。原始私有请求、会话与服务器信息不公开。

外观30分按 `30×clip(六视图平均SSIM,0,1)` 约定换算，不代表外观还原百分比。当前评分协议为 `scv-showcase-ssim-v3`。历史 `verification/`、`verification-v2/` 及旧下载包保留原规则和原分数，不用于当前结果。

参考资产：JohnMesplay，SCV，CC BY 4.0。六向参考图经过坐标和摄影机／灯光规范化。配乐与三种音效为题目原创合成音频，CC0。页面使用的客户端交付保留其原始署名。
