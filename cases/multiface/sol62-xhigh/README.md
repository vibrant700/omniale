# Multiface 人像补拍 · T1 / T2

`T1.mp4`、`T2.mp4` 是同一 Blender 场景切换标定机位后的渲染。两支均为 **668 × 1024、30 fps、104 帧**，视频为 H.264，声音为源 `speech.wav` 编码成的 48 kHz 单声道 AAC。首帧对应源帧 `040434`，末帧对应 `040743`。画面帧时间为 `(帧号 − 1) / 30` 秒，原声从 0 秒开始，未加变速、淡入或淡出。

## 打开与编辑

在 Blender 5.3 打开 `scene.blend`，保持 `assets/` 与工程相邻。工程默认相机为 `T1`；`02 TARGET CAMERAS` 中也有 `T2`，`03 SOURCE CAMERAS` 则保留 `I1`、`I2`、`I3` 以便检查。可在场景属性中切换相机并渲染；需要按每台相机的精确像素比例设置输出时，使用下方脚本。

`01 PERFORMANCE` 中的头、颈、肩是同一连续三维网格。数据属性里从 `Capture 001` 开始的形态键逐一对应素材帧；`Performance atlas` 材质节点读取 `assets/atlas/` 的同步 UV 序列。不需要插件或自动执行脚本。可编辑几何、相机、材质和椅背；修改网格后，贴图仍随其 UV 移动。在视频序列编辑器中可找到原声条带。渲染图像序列时关闭了 VSE 画面合成，编码时再按时间戳复用 WAV。

## 后台重渲染

以下命令从 `submission/` 运行。依赖 Blender 5.3（自带 Python / NumPy、Cycles CPU）和含 `libx264` 及 AAC 编码器的 FFmpeg。重渲染只需要交付目录，不依赖 `candidate/`。

```bash
blender -b -t 4 --python-exit-code 2 --python build.py -- check

blender -b -t 4 --python-exit-code 2 --python build.py -- render --camera T1 --out ../scratch/T1
blender -b -t 4 --python-exit-code 2 --python build.py -- render --camera T2 --out ../scratch/T2

blender -b -t 4 --python-exit-code 2 --python build.py -- encode --camera T1 \
  --frames ../scratch/T1 --out ../scratch/T1.mp4
blender -b -t 4 --python-exit-code 2 --python build.py -- encode --camera T2 \
  --frames ../scratch/T2 --out ../scratch/T2.mp4
```

抽查单帧时，向 `render` 传入例如 `--start 25 --stop 25`。`check` 重新打开工程，检查五台相机对标定点的投影、三个时间点的几何求值，以及完整的相对资源路径。交付前已在另一目录独立重开并重渲染 T2 第 25 帧，像素与成片编码前的同帧一致。

## 重建入口

用已交付的资源重建 `.blend`：

```bash
blender -b -t 4 --python-exit-code 2 --python build.py -- build
```

也可由原始素材重新生成资源。另需系统 Python 3、NumPy 和 Pillow：

```bash
OPENBLAS_NUM_THREADS=1 python reconstruct.py --source ../candidate \
  --assets ../scratch/rebuilt/assets --jobs 3
blender -b -t 4 --python-exit-code 2 --python build.py -- build \
  --assets ../scratch/rebuilt/assets --blend ../scratch/rebuilt/scene.blend
```

`assets/performance.npz` 保存用于构建的三维顶点序列，另外提供原始标定、WAV、逐帧纹理及素材许可说明。渲染时 Blender 从 `.blend` 内部读取形态键，无需读 `.npz`。

## 重建范围

从三路同步素材提取轮廓，三角定位可对应的脸部特征，拟合逐帧变形的闭合头颈与肩部表面，并将三路像素投影至共享 UV。保留采集时的暗场和人物光色，椅背为依据可见轮廓建立的近似几何。两个成片是对该场景的透视渲染，未使用目标实拍帧。

三个大夹角视图不能唯一确定所有深度。后脑、裁切后不可见的领口区域及部分耳侧几何采用延拓；可见口腔保留实拍纹理并局部加深，不是完整的牙齿或舌头模型。未对不能可靠定位的背景亮点补画。贴图含原始布光，适合这段表演和给定机位附近的使用，不是用于任意大角度或重新布光的角色资产。

源素材：Meta **Multiface**，CC BY-NC 4.0。见 `assets/SOURCE.txt`。
