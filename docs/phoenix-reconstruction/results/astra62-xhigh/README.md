# 凤凰飞行 · T1

`T1.mp4` 为有声交付片。镜头使用附件中的 T1 相机矩阵，不含推拉、裁切或片头片尾。画面为 1280 × 720、30 fps，取样帧 **0–99**；第 100 帧不输出。

## 打开与修改

使用 **Blender 5.3.0** 打开 `scene.blend`。默认视图为 T1 相机；小键盘 `0` 进出相机视图，`F12` 检查当前帧的最终光照。时间线由第 0 帧开始，声音参考轨使用相对路径 `sound/flight.wav`。移动工程时请保留 `sound/` 目录。

角色根据三个同步参考视角重建。翼面基准网格由跨视角对应点和前景轮廓确定，羽纹取自参考画面中可见的翼面，经整理成为固定 UV 色图；躯干、冠饰、足爪、眼斑长羽及其余纹样为重新建模和绘制。遮挡区域和羽片厚度为近似重建。工程不需要原录像、原角色或外部几何缓存。

| 要修改的部位 | 工程入口 |
| --- | --- |
| 整体位置、头颈、扑翼 | `01 \| Flight rig` 中的 `Phoenix \| Flight controls`。打开视图叠加层，进入姿态模式，在 Action Editor 中修改 `Flight study` 动作。左右翼各有 `Humerus`、`Ulna`、`Manus` 三段。 |
| 翼面轮廓与抬翼扭转 | `04 \| Remiges` 中的 `Wing.L`、`Wing.R` 网格。顶点组控制各段影响范围；`Apex \| torsion & fan` 形态键修正上止点的扭转与羽扇形状。 |
| 头冠、覆羽与爪 | 分别在 `03 \| Face & crown`、`02 \| Silhouette & plumage`、`06 \| Talons` 中选择对应网格。材质可在 Shader Editor 修改。 |
| 尾羽与眼斑 | `05 \| Train & streamers` 包含六枚眼斑长羽和一枚中央绿焰长羽；骨架的 `Train` 骨骼集合中，每枚长羽均有独立的八段骨链。三张羽纹色图都已内嵌于 `.blend`。 |
| 镜位与布光 | `07 \| Calibrated cameras` 保留 I1、I2、I3、T1。输出相机为 T1，水平适配，50 mm 镜头、36 mm 传感器。`08 \| Studio lighting` 为三盏区域灯。 |

渲染使用 Cycles、64 采样、固定种子 17、降噪；不使用运动模糊。色彩管理为 AgX / Medium High Contrast。可在交互视图中用材质预览检查羽纹；实体视图不代表最终色彩。

## 声音

混音以四次下扑为重拍。宽扫风叠加低频空气声形成下压重量；上抬时改用较轻的扫风，翻羽和回收处加入短促摩擦声。`sound/cues.json` 中 `down_frame`、`up_frame`、`fold_frame` 表示**声音重心对应的画面帧**，不是素材起始帧。可逐拍调整时间、速度、声像与增益，也可调整五组总线电平。

在本目录执行以下命令，依赖 Python 3、NumPy、SciPy：

```bash
python3 sound/mix.py
```

脚本会使用 `sound/sources/` 中的五个立体声 WAV 重新生成 `sound/flight.wav`（48 kHz、PCM16、每声道 160000 个采样）。另加 `--stems /输出目录` 可生成对齐的五轨分轨。工程的 Video Sequencer 只放置这条声音作为试听参考；**Render → Post Processing → Sequencer 保持关闭**，以输出三维相机画面。更新 WAV 后可重新打开工程刷新试听。

## 重新输出

Linux / Bash，需 Blender 5.3.0、上述 Python 依赖及带 libx264、AAC 编码器的 FFmpeg：

```bash
bash rebuild.sh
```

输出到 `render_work/T1.mp4`，中间 PNG 在 `render_work/frames/`。不覆盖交付片。`render.py` 自动选择可用 Cycles 设备，无可用 GPU 时使用 CPU。可指定 Blender 可执行文件及工作目录：

```bash
BLENDER=/path/to/blender WORK=/path/to/output bash rebuild.sh
```

只改声音时无需重渲染。在重新生成 `sound/flight.wav` 后执行：

```bash
ffmpeg -i T1.mp4 -i sound/flight.wav -map 0:v:0 -map 1:a:0 \
  -c:v copy -c:a aac -b:a 256k -t 3.333333333 -movflags +faststart T1-remix.mp4
```

## 署名

- 视觉参考：**“phoenix bird” by NORBERTO-3D**，Sketchfab，[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)。本片为依据委托方提供的标准化三机位录像制作的新机位重建；形体、材质、骨架及动作均有重建或改编，未使用原模型或原动画文件。
- 音效：委托方提供的五段原创程序合成素材，由确定性噪声和基础振荡器生成，无第三方采样，[CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/)。原始说明保存在 `sound/sources/SOURCE.txt`。本片对素材进行了变速、滤波、分层、声像处理及混音。
