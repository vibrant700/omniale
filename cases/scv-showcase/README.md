# SCV 机甲资产重建与有声展示片

根据六方向彩色参考图，使用 Blender 重建可编辑机甲资产，并将指定配乐、whoosh／hit／drop 编排为有声作品集展示片。

- 展示页：https://vibrant700.github.io/omniale/scv-showcase/
- 题面：[TASK.md](./TASK.md)
- 计分说明：[SCORING.md](./SCORING.md)
- 评分复核：[使用说明与源码](./verification-v2/README.md) · [下载复核包](../../docs/scv-showcase/assets/scoring-verification-v2.zip)
- 公开输入包：[agent-input.zip](../../docs/scv-showcase/assets/agent-input.zip)
- 模型交付与成绩：[results.json](../../docs/scv-showcase/results.json)

当前展示 Astra 6.2 xhigh＋官方 Codex 的 GPU 从头实验：RTX 4090 D、Cycles CUDA，42分31秒、152次工具调用、71次模型响应；交付27秒、1600×900、24fps有声片与独立资产。得分 **39.14 / 100**：结构19.85、外观9.29、关键细节0、音乐5、音效5。关键细节与音画由 Gemini 4 Neon 评定。

`gpu-page.html` 为当前页面模板；`build_gpu_page.py --run <本地实验目录>` 整理已完成交付、固定六视图及经接受的评分结果，生成页面媒体、数据与下载包，不调用被测模型。需要 Pillow。原始私有请求、会话与服务器信息不公开。

历史 `verification/` 及 v1 复核包对应旧CPU实验与旧动态规则，保留用于历史复核，不适用于当前结果。

参考资产：JohnMesplay，SCV，CC BY 4.0。六向参考图经过坐标和摄影机／灯光规范化。配乐与三种音效为题目原创合成音频，CC0。页面使用的客户端交付保留其原始署名。
