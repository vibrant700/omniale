# Multiface · 双机位重建

`T1.mp4` 和 `T2.mp4` 是同一份 `scene.blend` 在两个标定机位下的 Cycles 渲染。画面从第 1 帧到第 104 帧，对应素材 `040434` 到 `040743`；Blender 帧 `f` 的时刻为 `(f-1)/30` 秒。没有插帧、变速或裁掉首尾。

| 交付项 | 规格 |
|---|---|
| 画面 | 668 × 1024，30 fps，104 帧，H.264 / yuv420p |
| 声音 | 随题 `speech.wav` 编码为 AAC，48 kHz，单声道；从 0 秒开始 |
| 时长 | 视频 3.466667 秒；原 WAV 及成片音轨 3.466000 秒 |

## 打开与编辑

请让 `scene.blend`、`build.py` 和 `assets/` 保持同级，整个目录可搬移。打开工程默认是 T1 的第 1 帧。材质依赖 `assets/radiance/` 内连续编号的 104 张 UV 图，**不是**将两个目标视频贴到平面上。工程不引用 `candidate/`、`scratch/` 或联网资源。

- **01 | Performance**：头、耳、颈、肩共用 44,544 个顶点的固定拓扑。对象数据内的绝对形态键按帧存储表面，键名含素材帧号；顶点组用于选取眼区、口颌、颈肩等区域。材质节点中的序列使用共享 UV，保留原拍摄的阴影、皮肤细节和眼部反光。
- **02 | Capture stage**：独立可编辑的椅背头枕、支撑和背景灯面。背景使用深色 World。
- **03 / 04 | Cameras**：T1、T2 为成片相机，I1、I2、I3 为采集相机。每台相机的自定义属性保存源内外参。世界单位为米；原标定坐标（毫米）到 Blender 的映射为 `(X, Z-1065, -Y) / 1000`。
- **声音**：序列编辑器中有从第 1 帧开始的原声条带。画面直接渲染三维场景；成片入口将原 WAV 单独编码复用，不经过二次混录。

## 重渲染

需要 Blender 5.3（含 Cycles 和内置 NumPy）及 PATH 中带 `libx264`、AAC 编码器的 FFmpeg。命令在本交付目录执行；将 `blender` 替换为实际可执行文件路径即可。本环境为 `/opt/phoenix-runtime/blender-5.3.0-linux-x64/blender`。

```bash
blender -b scene.blend --python-exit-code 1 -P build.py -- render T1 --output renders/T1.mp4
blender -b scene.blend --python-exit-code 1 -P build.py -- render T2 --output renders/T2.mp4
```

入口会切换活动相机及其像素纵横比，把源 `K` 分别按 `668/1334`、`1024/2048` 缩放，对应各自的焦距和主点偏移；编码时输出方形像素。默认优先使用 CUDA，不可用时使用 CPU。可在命令末尾加 `--device CPU` 或 `--device CUDA`，也可用 `--tmp /已有临时目录` 指定中间 PNG 的暂存位置。临时帧在合片后自动清除。

只看某一帧，例如张口的第 25 帧：

```bash
blender -b scene.blend --python-exit-code 1 -P build.py -- render T2 --frame 25 --output renders/T2_0025.png
```

## 重建工程

随包的 `assets/performance.npz` 包含基准坐标和精度为 0.01 mm 的逐帧位移，`assets/cameras.json` 保存标定，`assets/radiance/` 为外观缓存。以下命令使用这些资源重建材质、绝对形态键、布景、声音条带和全部相机，**会覆盖本目录的 `scene.blend`**，不需要原图或 OpenCV：

```bash
blender -b --python-exit-code 1 -P build.py -- build
```

如需从原始三路 PNG 重新拟合缓存，另提供 `assets/recovery/recover.py`。这是可选步骤，额外依赖 Linux、Python 3、NumPy、SciPy、Pillow、g++、pkg-config 及 OpenCV 4 开发库。例：

```bash
python3 assets/recovery/recover.py ../candidate ../scratch/refit ../scratch/new_project/assets
cp build.py ../scratch/new_project/
blender -b --python-exit-code 1 -P ../scratch/new_project/build.py -- build
```

第三个参数须为新的或空的输出目录。重拟合只读取输入，在工作目录编译重采样、光流及深度测试算子；输出新缓存后，即可独立构建新工程。

## 恢复方法与边界

先利用三个前景轮廓约束头颈体积，再在环形截面上做局部深度扫描，用跨视图归一化纹理相关性细化基准表面，并回投轮廓校正。逐帧位移由三路稠密光流加权求解，使用前后向一致性、遮挡与轮廓约束。同期三路颜色经深度测试和入射角加权，烘焙为每帧一张共享图集。

此工程恢复的是**所给镜头覆盖的表演**，适合重渲染、邻近视角调整和局部修形。后脑及画幅以外的肩衣依靠连续曲面与材质延伸；头枕和灯的纵深是估计值。口内及眼部结合浅表几何与逐帧观测外观，并非可独立驱动的牙齿、眼球或面部骨骼。原光照已烘入材质，不等同于可任意重打光的皮肤着色模型。

**素材署名**：Multiface，Meta，CC BY-NC 4.0。成片、网格及外观缓存均由随题素材派生；来源说明见 `assets/SOURCE.txt`。
