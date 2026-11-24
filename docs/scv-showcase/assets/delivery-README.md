# SCV · Machine Register 007

一台红漆工业步行机的资产研究。27 秒展示片从整机登记照切入，依次观察三齿工具、敞开式驾驶舱、后部双叶轮和步行机构，最后回到整机。制作版本：**Blender 5.3.0**，Cycles；本次三维画面使用 RTX 4090 D / CUDA 渲染。

## 交付物

| 文件 | 用途 |
|---|---|
| `showcase.mp4` | 网页播放版本。1600 × 900、24 fps、H.264、AAC 立体声；MP4 索引前置。 |
| `asset.blend` | 独立、静态的可编辑机甲，无摄影棚、相机或音轨。 |
| `survey.jpg` | 由交付模型重新渲染的六方向正交检视页。 |
| `production/photography.blend` | 三维摄影工程。相对链接 `../asset.blend`，包含摄影棚、地台、灯光、六台动画相机与工具开合、叶轮旋转的展示动作。 |
| `production/edit.blend` | Blender 视频序列编辑工程。包含画面、字幕、转场、音乐及三种音效，可直接重新输出。 |
| `production/media/` | 无字、无声的摄影母版 `photography.mp4`，四个原始 WAV，磨损贴图及音频许可。 |
| `production/graphics/`、`production/scripts/` | 字幕及片尾的透明图板、制作和导出脚本。 |

## 使用模型

直接打开 `asset.blend`，或在其他工程中使用 **File → Append → asset.blend → Collection → SCV • Unit 07**。该集合已标记为资产。子集合按躯干、冷却塔、驾驶舱、前围、动力舱、双腿、肩部、工具、管束拆分；曲线软管、文字、倒角等仍可编辑。磨损图已打包，单独复制此文件即可复用模型。

坐标遵循附件：右手系，**+Z 向上、−Y 向前、+X 为机甲自身左侧**。采用参考的 2.32 单位方形正交视野定标，不代表实际米数。重建模型的可见几何跨度约为 X 1.96、Y 1.80、Z 1.64，中心接近世界原点。漆层采用三向盒投影的磨损贴图与程序粗糙度、凹凸；工艺边缘、裸露合金、胶管和座椅分别赋材。无需外部 UV 图集或插件。

## 修改与输出

请保持整个 `submission/` 的相对目录结构。正常打开工程、调整镜头或混音，均**不需要重新运行建模脚本**。

**只改剪辑、图板或声音：** 打开 `production/edit.blend`。底层为无字母版，通道 2–4 为图板和转场，5–8 为音乐、扫过声、撞击声、低频下落声。音量和淡变均有可编辑关键帧。保存后可用 **Render → Render Animation** 输出；以下命令会进一步将 MP4 的索引移到文件头，适合网页播放。命令在 `submission/` 下执行：

```bash
python production/scripts/export.py film --output showcase-revised.mp4
```

**改镜头、灯光、部件或动作：** 在 `photography.blend` 的时间线标记上切换相机，编辑相机变换、镜头偏移或 `MOTION / actuator test` 集合内的驱动空物体。编辑模型本体请打开 `asset.blend`；重新打开摄影工程即可刷新链接。保存后，关闭占用母版文件的播放器或剪辑工程，执行：

```bash
python production/scripts/export.py all --output showcase-revised.mp4
```

`all` 会重渲画面，更新 `production/media/photography.mp4`，再使用已保存的 `edit.blend` 混音和压制。仅更新摄影母版可将 `all` 改成 `camera`。如需保留逐帧 PNG 以便检查，附加 `--frames <缓存目录>`。命令依赖 Python 3、Blender 5.3 和带 `libx264` 的 FFmpeg，均可由 PATH 查找；也可指定 `--blender`、`--ffmpeg` 的可执行文件路径。摄影脚本优先选择 CUDA，没有兼容设备时改用 CPU。上述命令默认保持原片的 24 fps；若改变帧率、时长或剪点，请同时调整剪辑工程及编码参数。

| 帧（从 1 起） | 镜头与声音 |
|---|---|
| 1–96 | 整机登记照；开场淡入，音乐进入。 |
| 97–192 | 宽臂工具近景；扫过转场与撞击落在工作齿开合前。 |
| 193–288 | 驾驶舱上移镜头；短撞击标记切换。 |
| 289–379 | 背部双叶轮及供能管束；扫过声配合索引线穿屏。 |
| 380–469 | 低机位斜看腿部油缸与支撑脚；切换落在鼓点。 |
| 470–648 | 环绕回到整机；低频下落与曝光压暗衔接，末段转署名板并淡出。 |

## 制作源

`build_asset.py` 调用 `hull.py`、`drive.py`、`tools.py`，从几何截面、旋转体、曲线和节点材质生成静态资产；`surface_map.py` 生成磨损图。`build_photography.py` 搭建摄影工程，`graphics.py` 排印图板，`build_edit.py` 生成剪辑工程。这些是**重建设定**的脚本，会覆盖同名源文件，不用于导出已手动修改的工程。运行 Blender 脚本的方式为 `blender -b -P production/scripts/脚本名.py`。图板脚本使用 Pillow、NumPy 和 DejaVu 字体；可通过 `SCV_FONTS` 指定字体目录。成片重新输出使用随包 PNG，无字体依赖。

`render_survey.py` 在打开 `asset.blend` 后运行，按六个校准视角生成透明背景 PNG；`survey_sheet.py` 将它们排为检视页。可用 `SCV_SURVEY` 指定这两个脚本共用的图片目录。

## 署名

参考角色：**SCV**，作者 **JohnMesplay**，原作见 [Sketchfab](https://sketchfab.com/3d-models/scv-a310221f274b4189901f165731939ec1)，原作许可为 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)。委托提供的六视图经过坐标规范化、相机与灯光设置及渲染。本交付使用这些参考重新建模、制作材质与标记，并另行完成灯光、动画、摄影和剪辑；未导入原作网格。

配乐 `industrial_pulse.wav` 与音效 `whoosh.wav`、`hit.wav`、`drop.wav` 为委托提供的原创合成音频，许可 [CC0 1.0 Universal](https://creativecommons.org/publicdomain/zero/1.0/)。成片对音频作了选段、定位、音量自动化与混音。原始说明保留于 `production/media/LICENSE.txt`。
