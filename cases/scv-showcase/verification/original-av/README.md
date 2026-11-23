# 原音画评测材料

本目录收录案例作者提供的 `scv-av-review-v3-original-files.zip` 中的原件。七份提示词／规则／结果文件及导出说明按原字节保存，长度与 SHA-256 见 `source-manifest.json`。公开索引略去了导出清单中的本机绝对路径。

- `prompts/music-frozen-prompt.md`：音乐编排原提示词。导出说明记录，反重力会话读取了该文件；保留原有 `videoMetadata fps=8`、JSON 字段和示例文字，不改写成建议模板。
- `prompts/AV-MATCH-RUBRIC-v1.md`：会话读取的音画规则原件，保留其草案标题。音乐逐项定义以音乐提示词及最终结果中的 M1–M5 为准。
- `results/music-review-gemini.json`：原音乐结果 JSON，`items` 为 M1–M5 对象。
- `results/AV-REVIEW-v3-REPORT.md`：原音乐／音效报告。
- `results/SCORE-30-30-30-10.*`、`results/USER-ACCEPTANCE.json`：后续分数汇总及确认记录。
- `EXPORT-README.md`：作者提供的导出说明，记载反重力会话与读取／写入步骤的来源。

该导出包未包含完整反重力会话、完整接口请求或单独保存的原始音效评审提示词。`fps=8` 是提示词中的要求，不能仅凭该文件证明原会话的实际采样配置或上下文隔离。音效复核可参考原规则及报告；`../prompts/sfx-review.md` 仍仅为助手整理的新复核建议，不视为原调用原文。来源事实以作者提供的材料为依据，不声称本包独立核验过完整会话。

`../results/` 中另保留便于汇总的规范化结果；原件与规范化音乐逐项分数及总分已核对一致。

原文件的路径文字保留原样，阅读本包时可按下表定位：

| 原记录中的名称 | 本目录对应文件 |
|---|---|
| `music/frozen-prompt.md` | `prompts/music-frozen-prompt.md` |
| `music/music-review-gemini.json` | `results/music-review-gemini.json` |
| `AV-MATCH-RUBRIC-v1.md` | `prompts/AV-MATCH-RUBRIC-v1.md` |
| `AV-REVIEW-v3-REPORT.md` | `results/AV-REVIEW-v3-REPORT.md` |
| `USER-ACCEPTANCE.json` | `results/USER-ACCEPTANCE.json` |
| `SCORE-30-30-30-10.*` | `results/SCORE-30-30-30-10.*` |

原件提及的其他运行目录不随本导出包提供；对应指标、动态证据及原声窗口见本复核包的 `../results/`、`../evidence/`。
