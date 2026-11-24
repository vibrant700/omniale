# SCV GPU 实验评分复核包

对应实验 `astra62-xhigh-gpu-fresh01`：Astra 6.2 xhigh，官方 Codex，RTX 4090 D。

当前评分为结构30、外观30、关键细节30、音乐5、音效5，总分 **39.14 / 100**。固定指标脚本保持原算法；关键细节、音乐与音效由 Gemini 4 Neon 评定。工程检查不计分。

- `SCORING.md`：当前完整评分规则。
- `results/`：固定六视图指标、公开评审结论与预期汇总值。
- `scripts/aggregate_score.py`：只核对评分记录与算术，不执行媒体评审。
- 其他 `scripts/`：冻结的几何、图像、渲染及音效定位脚本；依赖与使用约定沿用原工具，运行前按本地资源配置路径。
- `config/`：固定机位、渲染及音效定位参数。

```bash
python scripts/aggregate_score.py
```

成片、参考图、GPU 重建六视图与资产下载见[展示页](https://vibrant700.github.io/omniale/scv-showcase/)。评分使用原始1280²图像，网页缩略对照仅供浏览。

本包为经整理的公开评分记录，不包含私有请求封装、凭据、服务器路径、原始会话或隐藏参考工程。历史 `verification/` 与 `scoring-verification-v1.zip` 对应旧CPU实验及旧动态规则，不用于当前结果。
