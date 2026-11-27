# 凤凰飞行 / T1

播放 `T1.mp4`。画面为 1280 × 720、30 fps、180 帧；音画共用 0–6 秒时间轴。第 0 帧是第一个采样，6 秒处不另加一帧。

## 画面工程

用 Blender 4.5.3 LTS 打开 `scene.blend`。活动相机为 **T1**，I1、I2、I3 留作视角核对。网格、动作、材质和四张图像纹理都在文件内，无需链接参考视频。按部位分组的集合可以单独隐藏和检查。

`Flight study | power strokes to glide` 是主骨架动作。`Flight` 管整体位移，`Humerus` 和 `Carpus` 管双侧翼根与腕折，`Train` 骨链分别控制六枚眼斑尾翎及中央长翎。翼面另有 Lift、Drive 两个形态键，参与极值姿态的弯曲校正。轮廓与飞羽尖按三视图估测；遮挡处的形体、朝向和羽层是重建解释。

在 Blender 中选择 **Render → Render Animation**，即可把第 0–179 帧写入相邻的 `frames/`。或从本目录运行：

```sh
blender -b scene.blend -o //frames/T1_ -a -- --cycles-device CUDA
```

## 声音工程

用 REAPER 7.86 打开 `Foley/Phoenix.rpp`，保持其与 `Foley/Media/` 的相对位置。四条轨道含 44 个片段，保留了源片段偏移、变速、淡化、声像、增益和 ReaEQ。工程标记对应主要下拍和滑翔转换。

| 轨道 | `Prints/` 输出 | 声部 |
|---|---|---|
| 01 Pressure | `01_Pressure.wav` | 下拍排开的低频气压，随振幅缩短 |
| 02 Primaries | `02_Primaries.wav` | 扑翼瞬态、飞羽尖的掠风与回翼 |
| 03 Quills | `03_Quills.wav` | 起势、换向及尾翎滞后的细碎摩擦 |
| 04 Slipstream | `04_Slipstream.wav` | 随翼速变化的连续气流，收至滑翔 |

**File → Render** 的预设范围是 0–6 秒，输出为 48 kHz、双声道、32-bit float WAV。直接渲染主输出得到 `Prints/Phoenix_Full.wav`；要重印单轨，保持主输出、声像与 FX 不动，每次独奏一轨并更改文件名。不要归一化，也不附加效果尾时。

四个分轨均已包含各自的混音处理。**从采样 0 对齐，以 0 dB 相加**即可重构总混；不要再叠加 `Phoenix_Full.wav`。交付检查：每个文件每声道 288,000 个采样，总混与分轨和的最大绝对差约 `3.17e-8`。

重新合成有声视频：

```sh
ffmpeg -framerate 30 -start_number 0 -i frames/T1_%04d.png \
  -i Prints/Phoenix_Full.wav -map 0:v -map 1:a \
  -vf scale=out_color_matrix=bt709 -c:v libx264 -crf 15 -preset slow \
  -pix_fmt yuv420p -color_primaries bt709 -color_trc bt709 -colorspace bt709 \
  -c:a aac -b:a 320k -movflags +faststart T1-remix.mp4
```

## 素材与许可

**视觉观察来源：** *phoenix bird*，NORBERTO-3D（Sketchfab），[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)。使用委托方提供的三个观察视频及相机、灯光和时间配置；翼纹从观察画面的可见羽区取色并重投影。网格、其余羽纹、骨架和动作在本次制作中重建，未使用原模型、原贴图或原动画。

**短音源：** 来自 *The Battle for Wesnoth* 的 [`data/core/sounds/`](https://github.com/wesnoth/wesnoth/tree/master/data/core/sounds)，逐文件署名和许可依据上游 [`copyrights.csv`](https://github.com/wesnoth/wesnoth/blob/master/copyrights.csv)。以下原文件随工程提供；截取、变速和叠层均在 RPP 内可编辑。三项均为 **GNU GPL v2 或更高版本**，许可文本见 `Foley/Licenses/GPL-2.0.txt`。

| 本地源文件 | 上游文件 | 作者 |
|---|---|---|
| `Bat-flapping.wav` | [bat-flapping.wav](https://raw.githubusercontent.com/wesnoth/wesnoth/master/data/core/sounds/bat-flapping.wav) | Richard Kettering (Jetrel)、Lari Nieminen (zookeeper) |
| `Miss-1.ogg` | [miss-1.ogg](https://raw.githubusercontent.com/wesnoth/wesnoth/master/data/core/sounds/miss-1.ogg) | Lari Nieminen (zookeeper) |
| `Net.wav` | [net.wav](https://raw.githubusercontent.com/wesnoth/wesnoth/master/data/core/sounds/net.wav) | 上游署名为 unknown |

`Air displacement 01–03.wav` 与 `Laminar flow.wav` 为本次以分频噪声、包络和立体声相关性合成的气流素材，无外部采样。声音工程及其混音改编以 GPL v2 或更高版本提供。无音乐、对白或旁白。
