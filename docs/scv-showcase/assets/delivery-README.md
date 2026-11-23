# FIELD REGISTER № 007 · SCV

一台红氧化漆工业步行机的资产登记片。镜头从正面移向三分之四视角，依次检查开放座舱、右臂长叉和背部双动力舱，最后回到另一侧的整机与材质表。

**播放 `showcase.mp4`；复用模型打开 `asset.blend`；改镜头打开 `stage.blend`；改声音与剪辑打开 `edit.blend`。**

## 交付物

| 文件 | 用途 |
|---|---|
| `showcase.mp4` | 网页成片。16:9，1280 × 720，24 fps，438 帧 / 18.25 秒；H.264 视频、AAC 立体声，MP4 快速起播。 |
| `asset.blend` | 独立资产库。全机网格、曲线、倒角、材质和四张打包贴图；不包含摄影棚或音轨。 |
| `stage.blend` | 摄影棚：链接整机集合、地面、四盏面光、五台动画相机及切换标记。Cycles / AgX。 |
| `edit.blend` | 剪辑母版：画面、图版、两次扫页转场、片尾淡出、配乐与分立音效。 |
| `inspection.png` / `poster.jpg` | 同尺度六向重建核对图，以及可用作网页视频封面的成片静帧。 |
| `media/` | 不带字幕和声音的已渲染画面 `lighting.mp4`、四个原始 WAV、透明图版、贴图源图和排版字体。 |
| `source/` | 建模、材质图制作、灯光与镜头搭建、图版生成、剪辑与导出脚本。 |

制作版本为 **Blender 5.3.0**。建议使用同版本打开。整个交付目录可以搬动；请保持三个 `.blend` 和 `media/` 的相对位置不变。不需要安装 Blender 插件或联网。

## 模型复用

在另一个工程中选择 **File → Append → `asset.blend` → Collection → `SCV  •  FIELD UNIT 07`**。集合已标为资产。移动或旋转 `SCV | assembly datum` 即可定位整机。材质预览或渲染模式可查看完整磨损、色标、白星与垂布徽记；实体模式主要用于分件编辑。

采用右手系：**+Z 朝上，−Y 为正面，机甲自身左侧为 +X**。包围盒中心在原点附近；外廓约为 **X 2.000 × Y 1.841 × Z 1.643**，单位只是规范化场景单位。左右臂分别为短行程夹持器和三齿长叉。子集合按座舱、双散热立柱、动力舱、左右腿、肩架、工具及回流管分组。液压管线保留为有截面的可编辑曲线；本资产不含骨骼绑定。

材质以 Principled BSDF 为基础。`rolled_sheet.png` 的 R/G/B 分别控制剥落、漆面亮度和粗糙度；采用盒式投影。服务铭文、篷顶星徽与布标另用 UV 贴图。材质节点中的颜色、金属度、粗糙度范围及凹凸强度均可修改。单独移出 `asset.blend` 不会丢贴图。

## 镜头与声音

| 帧（含首尾） | 画面 | 过渡 |
|---|---|---|
| 1–96 | 总装登记；从近正面绕至机甲右前侧 | 低音冲击入场 |
| 97–168 | 橙色顶篷、驾驶位、双列散热百叶 | 扫页随 whoosh 掠过 |
| 169–240 | 长叉工具、护轨与三枚锻造齿 | hit 对齐硬切 |
| 241–330 | 从后侧绕向双叶轮、管路及后支撑 | 第二次 whoosh 扫页 |
| 331–438 | 左前侧整机与材质索引，缓停淡出 | drop 下沉，轻击锁定 |

配乐取 `industrial_pulse.wav` 的 **4.00–22.25 秒**。在 `edit.blend` 的第 6 通道可移动、裁剪配乐，或编辑 Volume 关键帧；第 7、8 通道分别放冲击、扫过和下沉音效。第 3–5 通道是图版、扫页与片尾，均独立于画面缓存。时间线以 24 fps 计时。

## 重新输出

**只改剪辑或音频：** 打开 `edit.blend`，修改并保存，选择 **Render → Render Animation**。默认目标在同级 `exports/` 中。为便于流式播放，也可在此目录运行下面命令；需能在命令行找到 Python 3、Blender 和 FFmpeg：

```bash
python source/export.py --output exports/revised.mp4
```

**改模型、材质、灯光或镜头：** 在 `asset.blend` 或 `stage.blend` 中修改并保存。舞台帧 1、97、169、241、331 的时间标记分别绑定五台相机；位置、旋转及正交宽度均有关键帧。然后运行：

```bash
python source/export.py --refresh --output exports/revised.mp4
```

`--refresh` 会逐帧使用 Blender 重新渲染舞台，更新 `media/lighting.mp4`，再用剪辑母版合成带声音的成片。请先关闭正在读取该视频的播放器。建议为临时帧预留至少 2 GB；`--work 路径` 可指定临时目录，`--blender 路径` 和 `--ffmpeg 路径` 可指定程序位置。默认不覆盖已交付的 `showcase.mp4`。若改变总时长，还需同步调整 `edit.blend` 的片段端点、音轨和结束帧。

**纯 Blender 路径：** 保存舞台修改，重新打开 `edit.blend`，静音第 2 通道的 `CACHE` 片段，取消第 1 通道 `LIVE` 场景片段的静音，然后 Render Animation。该模式直接调用链接舞台；要严格保留舞台的 AgX 显示变换与母版图版颜色，优先使用上面的 `--refresh` 路径。

## 制作脚本

日常修改无需重跑建模脚本。以下脚本用于从源重建，运行时会覆盖对应的工程或素材，建议在交付目录的副本中使用。

| 脚本 | 作用 |
|---|---|
| `surfaces.py` | Python + NumPy + Pillow；生成多通道磨损图、服务铭文和两张徽记。 |
| `build_asset.py` / `build_stage.py` | 依次用 `blender -b -P source/脚本名.py` 生成模型库、链接舞台及摄影机动画。 |
| `render_plates.py` | 在舞台中渲染 Cycles 光照采样帧，并导出求值后的三角面与相机投影矩阵。 |
| `reproject.py` | 制作缓存的可选加速路径。用相邻光照采样投影至实际三角面，每个输出帧按该帧相机独立进行深度测试和可见性混合。适合本片静态机体与运动相机；改变几何动画后请使用 `--refresh`。 |
| `graphics.py` | Pillow 排版；正投影图取自模型深度与轮廓。再次排版可直接运行脚本，使用 `media/graphics/` 中已有的线图。 |
| `build_edit.py` | `blender -b -P source/build_edit.py`，将画面缓存、图版及声音装配为 VSE 母版。 |
| `inspection.py` / `contact_sheet.py` | 按参考正交尺度渲染六向核对图，再合成独立检视页。 |

本片制作所用的缓存命令如下。加速路径使用 Linux、Mesa/EGL、OpenGL、Python 3、NumPy、Pillow 及 FFmpeg；**常规重输出不依赖 EGL 或这些 Python 扩展**。

```bash
blender -b stage.blend -P source/render_plates.py -- /path/to/cache 7
python source/reproject.py /path/to/cache media/lighting.mp4
python source/graphics.py /path/to/cache/triangles.npy
blender -b -P source/build_edit.py
```

## 素材署名

- **SCV 参考设计与原模型：JohnMesplay**，[SCV（Sketchfab）](https://sketchfab.com/3d-models/scv-a310221f274b4189901f165731939ec1)，原作品页面标注 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)。委托附件对参考进行了坐标规范化、摄影机与灯光设置和六向渲染。本交付依据这些图像重新建立几何、分件、材质、贴图及展示动画，未导入原网格。
- **配乐及音效：** 委托附带的原创合成音频 `industrial_pulse.wav`、`whoosh.wav`、`hit.wav`、`drop.wav`，以基础波形及确定性噪声合成，按 [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) 提供。原始说明见 `media/LICENSE.txt`。本片进行了截取、编排与音量自动化。
- **字体：** DejaVu Sans、DejaVu Sans Mono、DejaVu Serif，DejaVu / Bitstream Vera 字体许可，详见 `media/type/LICENSE.txt`。图版线图、登记页排版、磨损图及标记为本重建制作。
