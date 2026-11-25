# SCV-07｜机甲资产与展示片

使用 **Blender 5.3.0**（Cycles / AgX）制作。资产基于提供的六张正交图从零建模，未下载或导入原模型。展示片以工业检修台为背景，从全身进入驾驶舱、双侧工具、后部动力包和足部，再回到整机巡检与结尾定帧。

| 交付物 | 用途 |
| --- | --- |
| `asset.blend` | 单独复用的无动画资产。装甲、液压件、线缆、舱罩、夹爪和垂布可分别编辑。 |
| `showcase.mp4` | 28.58 秒，1920 × 1080，24 fps，H.264 / AAC 48 kHz 立体声。适合网页播放。 |
| `showcase.blend` | 完整展示制作工程；包含独立的画面场景和音频剪辑场景，不依赖预渲染视频。 |
| `poster.jpg` | 可用于网页视频封面的成片画格。 |
| `media/` | 音频原文件、贴图、字体及其许可、参考相机与灯光规格。 |
| `source/` | 建模、贴图、展示工程生成脚本，以及可独立运行的重导出脚本。 |

## 打开与编辑

**复用资产。** 在 Blender 中打开 `asset.blend`，或用 **File → Append → Collection** 追加 `SCV-07 | Mobile Service Chassis`。`Studio` 和 `Reference` 收藏集不属于资产；后者包含匹配六视图的正交相机。资产根控制器为 `CTRL / SCV master`。静态包围盒以原点为中心，最大尺寸为 2 个场景单位；右手坐标，`+Z` 向上、机甲朝 `−Y`、机甲左侧为 `+X`。磨漆、钢材和橡胶使用程序节点；标记与垂布徽记的 UV 贴图已打包。磨边节点在 Cycles 中可完整显示。

**改镜头。** 打开 `showcase.blend`，在场景 `01 | PICTURE` 的时间线上拖动，使用相机标记跳转镜头。镜头位置和朝向由关键帧控制；`SHOT` 收藏集存放相机，`GFX` 存放各镜头可编辑的文字与图形；机甲的活动部件是 `CTRL / Canopy` 和 `CTRL / Jaw`。标题是相机子对象：移动相机会跟随；若大幅改焦距或画幅，请重新调整对应图形的大小与位置。移动切点时，一并调整图形的显隐关键帧，并检查声音落点。

**改声音。** 在顶部场景选择器切到 `02 | EDIT & MIX`，把下方时间线切换成 **Video Sequencer**（编辑器类型选择 `Video Sequencer`，也可按 `Shift+F8`）。第 1 轨是指向画面场景的条带，2–5 轨分别为配乐、掠过、冲击与低频落点。可在条带属性中调整位置、音量和关键帧。关键落点包括 4.00 秒进入驾驶舱、9.00 秒切换夹爪、19.50 秒切入整机环绕，以及 26.96 秒切入片尾。

工程目录可整体移动。请保留两个 `.blend` 与 `media/` 的相对位置；音频从 `media/audio/` 读取，展示字体和机身贴图已打包。

## 重新输出

需要 Blender 5.3、Python 3 和含 `libx264` 的 FFmpeg。保存编辑后的 `showcase.blend` 后，在本目录执行：

```bash
python3 source/export.py --blender /path/to/blender --device CUDA \
  --work ./renders --output ./showcase_reexport.mp4
```

如果 `blender` 已在 `PATH` 中，可以省略 `--blender`。没有 CUDA 时用 `--device CPU`，也可选择系统支持的其他 Cycles 后端。脚本会渲染 `01 | PICTURE` 的绑定相机及画面图形，从 `02 | EDIT & MIX` 混出 WAV，最后编码成带快速起播索引的 MP4。画面、声音两个场景必须保持相同帧率，剪辑帧区间须落在画面场景范围内。脚本以画面场景的相机剪辑为准；如自行在视频序列编辑器中加入额外视频或画面效果，需在 Blender 中另行渲染该编辑时间线。

- 低分辨率短测：对上述命令追加 `--frames 1 96 --scale 50`，并使用单独的 `--work` 目录。
- 渲染被中断：工程、分辨率和采样不变时，使用相同缓存目录和 `--resume` 补齐缺帧。
- 只改音频：使用已有完整画面缓存的目录并追加 `--audio-only`。更换镜头、光照或渲染规格后，不要沿用旧画面缓存。
- 网页封面来自第 57 帧；例如可用 FFmpeg 从画面缓存将 `picture_0057.png` 转成 `poster.jpg`。

生成源码仅用于重新构建初始交付，不是日常编辑的前置要求。`source/make_decals.py` 需要 Pillow；`source/build_asset.py` 和 `source/build_showcase.py` 在 Blender 中运行，会写出同名工程，重新构建前请另存手工修改：

```bash
python3 source/make_decals.py
blender -b --python source/build_asset.py
blender -b asset.blend --python source/build_showcase.py
```

如需换掉 Asset Browser 的嵌入缩略图，可用 `blender -b asset.blend --python source/set_asset_preview.py -- preview.png`。

## 署名

- **SCV 参考**：JohnMesplay，《[SCV](https://sketchfab.com/3d-models/scv-a310221f274b4189901f165731939ec1)》，原作页面标注 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)。委托方提供的参考经过坐标规范化、相机及灯光设置和六视图渲染；本交付据此重新建模，并重新制作材质、图案、展示场景和动画。
- **音频**：委托附件 `industrial_pulse.wav`、`whoosh.wav`、`hit.wav`、`drop.wav`，依附件说明为合成创作，[CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/)。文件未改写，成片进行了裁剪、叠放和音量自动化。见 `media/audio/LICENSE.txt`。
- **字体**：DejaVu Sans / Sans Mono，许可证和版权信息见 `media/fonts/LICENSE.txt`。
