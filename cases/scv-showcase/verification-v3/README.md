# SCV SSIM 外观评分复核包 v3

对应 Astra 6.2 与 Sol 6.2 的独立 xhigh GPU 实验，总分分别为 **35.38 / 100**、**32.90 / 100**。结构30、外观30、关键细节30、音乐5、音效5。

外观分＝`30 × clip(六视图平均 SSIM, 0, 1)`。这是本案例约定映射，不是还原百分比、正确率或经专家标定的主观质量分。原始六视图、SSIM算法及各机位平均方式不变；关键细节与音画沿用已完成的Gemini4Neon裁定。

- `SCORING.md`：完整现行规则。
- `results/`：Astra 的SSIM与轮廓数值、几何指标及已完成评审；`results/sol62-xhigh/` 保存 Sol 的对应记录。历史距离指标不参与本版计算。
- `scripts/aggregate_score.py`：核对分项与总分，无需媒体模型。
- `scripts/evaluate_images.py`：对既有统一六视图重算SSIM与轮廓IoU；不加载感知距离模型或权重。
- `scripts/evaluate_asset.py`：需要重新核验资产时使用，几何与渲染条件沿用冻结规则。
- `config/`：参考机位、渲染和音效定位参数。

```bash
python scripts/aggregate_score.py --model astra62-xhigh
python scripts/aggregate_score.py --model sol62-xhigh
```

[展示页](https://vibrant700.github.io/omniale/scv-showcase/)提供原成片、资产与六视图。历史v1/v2包保留各自旧版规则与成绩，不用于现行总分。
