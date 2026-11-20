# 装配录像理解与图解手册

展示页：https://vibrant700.github.io/omniale/assembly-manual/

培训部门委托智能体观看一段18分31秒的远程指导录像，回答十个问题，再制作带关键截图与可编辑标注的操作手册。输入包括 HoloAssist 公开变调版录像、十题问题、空白回答模板及来源许可；实际交付包括回答、Word/PDF手册、原截图与标注源文件。

## 当前公开结果

当前页面只展示 **GPT-6.2-Sol · xhigh + Codex，60.88／100**。

| 项目 | 结果 |
|---|---:|
| 十题回答 | 39.375／50 |
| 时间与结论证据 | 14／20 |
| 手册质量 | 7.5／30 |
| 原始总分 | 60.875／100 |
| 展示总分 | 60.88／100 |

受测框架为 Official Codex CLI 0.142.4；单个连续任务运行55分11秒，235次工具调用、73次本地 Whisper 调用。78次模型请求均验证为显式 xhigh。未设置人为总时长或工具调用次数限制；本地 Whisper base.en 辅助理解音频，无原生音频输入。封存交付为8页手册、29张原截图和29份SVG标注。

评分采用 `2.4-four-dimensions`：回答50分，时间与结论证据20分，手册30分。手册包含内容完整性、操作可执行性、标注教学价值、过程表达清晰度四维，各7.5分；先记录独立错误、严重性与唯一归属，再按错误单位换算0／1／2／3等级和权重。主评为 GPT-6.1-Sol high；Gemini 3.1 Pro Preview 对源音频的听音观察作辅助，事实真值以原数据集标注为准。可编辑、正常导出与基本可读性单独检查，不占30分。

## 当前页面与数据

发布文件位于 `docs/assembly-manual/`。当前布局名为 report-v2，页面URL不变。页面按委托、输入资料、评分规则、受测结果与实际交付组织；交付、十题评分和手册错误清单在同一结果区域内查看。

- `index.html`、`case.css`、`app.js`：当前展示界面与交互。`report-v2-20261120` 是资源缓存版本标记。
- `data-v2.json`：当前内容与评分数据，`schemaVersion` 为2。顶层包含 `source`、`scoring`、`defaultSystem` 和 `systems`；目前 `defaultSystem` 为 `sol62-xhigh`。
- `systems[systemId]`：独立模型结果，含 `meta`、`result`、`qa`、`manual`、`delivery` 与 `deliveryChecks`。`qa` 包含逐题回答、C1–C4裁定和两项证据分；`manual` 包含四维结果与去重错误依据；`delivery` 引用实际交付和页面图像。
- `execution-v2.json`：真实执行节选，按同样的 `systems[systemId]` 键组织运行统计和步骤。每条节选保留原始 `itemId`，不公开未审核的原始运行日志。
- `TASK.zh-CN.md`、`questions.md`、`answers-template.md`：公开委托与模板。`SCORING.zh-CN.md` 为完整评分说明。
- `public-task.zip`：题面、问题、空白模板、录像下载说明及来源许可，不含标答、评分材料或大体积录像。
- `results/sol62-xhigh/`：原始 `manual.pdf`、`manual.docx`、`answers.md`、`editable-delivery.zip`，以及 `pages/` 页面预览和 `review/` 评分用图组。

`docs/assembly-manual/` 中的数据是公开展示的权威来源，不在 `cases/` 内重复存放另一份公开数据。当前界面源文件位于本目录的 `report-v2-template/{index.html,case.css,app.js}`；`build_report_v2.py` 用于恢复界面，并验证已发布的两个v2数据文件及下载资产哈希。

静态页面无需前端构建依赖。在 `docs/` 下启动HTTP服务后访问 `/assembly-manual/` 即可预览；直接使用 `file://` 打开会影响JSON和Markdown加载。页面相对路径用于交付与预览，完整录像通过GitHub Release提供。

## 增加后续模型

新增模型时保留当前结果，以新且稳定的 `systemId` 增加 `data-v2.json.systems` 条目，并在 `execution-v2.json.systems` 下增加相同键。将该模型实际交付、页面预览与评分图组放在独立的 `results/<systemId>/` 目录，再在该条目的 `delivery` 等字段引用它们。

每个结果应使用同一当前评分协议，保留原始精度的分数、逐条裁定和实际资产，不从模型名称推断结果。仅在运行与评分均完成后加入公开结果。界面从 `systems` 自动生成结果表、模型选择和对应交付；需要改变默认展示时显式更新两个数据文件的 `defaultSystem`。不要用空卡片或虚构分数占位。

## 构建与发布注意

本目录中的 `build_case_page.py`、`build_luna_page.py`、`build_xhigh_page.py`、`build_strict_manual_page.py`、`keep_xhigh_results.py`，以及 `site-template/`、`comparison-template/`、`xhigh-template/`、`luna-xhigh-template/` 属于历史页面构建记录。它们对应不同的数据结构、旧模型和旧评分，**不能运行后覆盖当前 report-v2 页面或 data-v2 数据**。当前生成、复制和部署以 `report-v2-template/`、`build_report_v2.py` 及两个v2数据文件为准。

发布前检查JSON结构、固定权重汇总、所有相对资源路径、录像播放、模型切换、PDF与Word下载，以及桌面和移动布局。公开内容只包含审核后的题面、实际交付、评分依据与执行节选，不包含API凭据、宿主路径、私有原始标注或未审核日志。

录像许可为 CDLA-Permissive-2.0，来源声明和许可随题包保留；本案例不表示经过原数据集作者审核。当前质量判断由模型对照材料完成，未进行真人跟做实验。
