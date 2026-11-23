# SCV 机甲展示片 · 评分复核包 v1

本包用于追溯和复算 OmniALE SCV 案例的评分。输入包供被测 agent 工作；本复核包供评测者使用，包含参考工程地址、评分脚本、作者提供的音乐原提示词与音画规则、建议复核模板、证据和逐项结果。不要把复核包或参考工程提供给被测 agent。

## 内容

| 文件或目录 | 用途 |
|---|---|
| `SCORING.md`、`PROTOCOL.json` | 30／30／30／10 的公式、阈值、采样、掩膜、版本与评委分工 |
| `scripts/`、`requirements.txt` | 几何／图像重算、音效候选定位、分数汇总、下载与校验 |
| `original-av/` | 作者导出包中的音乐原提示词、音画规则、原结果／报告、来源说明和原件哈希 |
| `prompts/`、`schemas/` | 助手整理的建议复核模板和规范化 JSON 结构，与原件分开标注 |
| `config/` | 固定机位与场景、源音效标注、定位参数、外部文件 URL／SHA-256 |
| `evidence/` | 动态帧证据、音效候选与原声窗口、时间映射及音频一致性检查 |
| `results/` | 几何／图像原始指标、逐项裁定和预期总分 |
| `manifest.json` | 包内文件字节数与 SHA-256 |

大文件按需下载，不重复塞入 ZIP。`asset` 下载组包含 297.2 MB 的参考 `.blend`；`weights` 组为 244.4 MB 的官方 AlexNet 权重。输入参考图保持原始 RGBA PNG，页面缩略图不用于评分。

## 1. 校验与总分复算

在解压后的本包根目录执行。只需 Python 3.10+ 标准库，不需要 Blender、GPU 或 Gemini：

```sh
python scripts/check_integrity.py
python scripts/aggregate_score.py --published
```

该命令检查已收录逐项结果的加和与既定公式，得到 `37.70 / 100`；它不重新判断媒体。任一评审项为 `null`、条目重复或加和不一致时，汇总器拒绝输出完整总分。

## 2. 复算六视图图像指标

安装 Python 依赖；原评测使用 Python 3.12.14、CPU 版 PyTorch，建议以 Python 3.12 建立独立环境。固定版本见 `requirements.txt`，Blender 5.3 和 FFmpeg／ffprobe 独立安装。

```sh
python -m pip install -r requirements.txt
python scripts/fetch_resources.py --group images --output work
python scripts/fetch_resources.py --group weights --output work
python scripts/evaluate_images.py --public-root work/agent-input --prediction work/submission/canonical_capture --torch-home work/model-cache --output work/recomputed-images.json
```

下载脚本逐个核对字节数与 SHA-256；输入 ZIP 校验后解压。图像组下载六张原始提交渲染及题目输入；权重组下载官方 AlexNet 检查点。已下载内容可用 `--verify-only` 校验。相机、背景、alpha 并集掩膜及 LPIPS 空间变体不能自行替换。

## 3. 从 Blender 工程重新计算结构与外观

```sh
python scripts/fetch_resources.py --group asset --output work
python scripts/evaluate_asset.py --reference-blend work/reference/reference-asset.blend --submission-blend work/submission/asset.blend --public-root work/agent-input --blender blender --torch-home work/model-cache --output work/recomputed-asset
```

`--blender` 可替换为可执行程序完整路径。输出目录须为空，且必须在提交目录之外。脚本复制完整提交目录后独立打开，提取世界坐标下的求值三角表面，重渲染六方向带材质图／白模图并计算指标；源提交保持原样。测试其他提交时，将 `.blend` 及其依赖放在独立目录，通过 `--submission-root` 指定该目录。几何采样种子和阈值固定；不进行 ICP 或尺寸拟合。光线采样、渲染器或依赖版本改变可能带来数值差异，应保存运行配置。

几何计算使用完整求值网格，图像评分使用原始题面参考 PNG。两份 `.blend` 不需要具有相同拓扑或顶点编号。自动打开、资源解析与渲染检查只覆盖工程门槛的一部分；工程可编辑性与可重导同样按 `SCORING.md` 核查，不计入正式分数。

## 4. 音效定位与建议的 Gemini 复核流程

```sh
python scripts/fetch_resources.py --group av --output work
python scripts/localize_sfx.py --video work/submission/showcase.mp4 --bgm work/agent-input/audio/industrial_pulse.wav --sfx-dir work/agent-input/audio --output work/sfx
ffmpeg -i work/submission/showcase.mp4 -map 0:a:0 -vn -c:a pcm_s24le work/final-mix.wav
```

可用 `--ffmpeg`、`--ffprobe` 指定程序路径。固定定位器使用本例原生 24 fps 帧网格。`evidence/sfx/` 已提供对应成片的候选、原声 MP4＋FLAC 窗口和源时间映射，可直接复核；检测值不是音效实际使用的真值。残差仅用于定位，评分必须听原混音。

以下是助手建议的新复核流程，不代表原反重力评测实际采用的调用流程。建议使用两个独立的评审上下文：

1. **音乐编排**：使用作者提供的 `original-av/prompts/music-frozen-prompt.md`，附完整成片、同源完整无损混音、原 BGM；不附音效候选、已公布分数或制作过程。保留原提示词的采样与输出要求，另行记录实际接口配置。
2. **音效对应**：发送 `prompts/sfx-review.md`，附完整成片／混音、原 BGM、三种原音效、候选 JSON、窗口及时间映射；听看确认每个候选，并完整查漏。

实际评审需支持同时读取声音与画面。原生帧用于核对视觉锚点；模型听看判断不能代替毫秒测量。记录实际模型 ID、媒体／提示词哈希、视频采样和解码设置，并保存原始响应，记录模板见 `config/review-record.template.json`。包内不提供绑定某家接口的 API 调用器。

**原音画评测由案例作者在反重力（Antigravity）中进行。** 作者现已提供导出包，包含当时读取的音乐提示词、音画规则及结果原件，见 `original-av/`。导出包未包含单独保存的音效原提示词、完整会话或完整接口请求；音效建议模板及规范化 Schema 由助手整理，不能用其补作原调用记录。已公布音画成绩及模型身份由案例作者确认；`results/` 中音乐结果作字段规范化，音效结果由最终报告转录，来源见 `results/av-provenance.json`。新复核应先独立完成，再对照已公布结果，不能将结果作为提示答案。

## 5. 动态缺陷与新结果汇总

按 `prompts/dynamic-review.md` 观看完整成片，回到原生帧确认错误；同镜头、同部位的持续或反复错误合并计数。输出 `schemas/` 定义的逐项 JSON。浮片、重影和显隐连续性必须分别有成立的证据。

新的指标与完成评审可这样汇总：

```sh
python scripts/aggregate_score.py --surface work/recomputed-asset/surface_metrics.json --images work/recomputed-asset/image_metrics.json --dynamic work/dynamic-review.json --music work/music-review.json --sfx work/sfx-review.json --output work/score.json
```

几何／图像脚本计算与动态／音画判断是不同环节；提供脚本不代表后者可以自动客观复现。主观复核有随机性，不预设必须得到相同裁定。计分前保留条目证据；工程门槛单列，权重为零。

## 来源

- [案例展示页](https://vibrant700.github.io/omniale/scv-showcase/) · [代码](https://github.com/vibrant700/omniale/tree/main/cases/scv-showcase/verification)
- SCV：JohnMesplay，[原始模型](https://sketchfab.com/3d-models/scv-a310221f274b4189901f165731939ec1)，CC BY 4.0；坐标、相机与灯光经过规范化。详见 `ASSET-SOURCE.md`。
- 原创合成配乐与音效：CC0，见 `AUDIO-LICENSE.txt`。第三方软件及预训练权重遵循各自许可证。
