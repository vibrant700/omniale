# 双机位动态人脸重建

## 交付

- `scene.blend`：同一套动态头部、颈部及肩部表面，104 个原生绝对形态键；`T1`、`T2` 两个场景共享网格、动画和材质，仅使用各自的标定相机。
- `T1.mp4`、`T2.mp4`：668×1024，30 fps，104 帧，H.264 / AAC，48 kHz 单声道原声。
- `assets/surface_animation.npz`：可重新构建网格和动画的浮点表面缓存。
- `assets/appearance/`：104 张共享 UV 外观纹理，不是目标机位成片或平面背景。
- `assets/cameras.json`、`assets/speech.wav`：完整标定与未经改动的原始音频。

## 构建与重渲染

依赖：后台 Blender 5.3（自带 Python、NumPy），FFmpeg（含 libx264、AAC）。普通 Python 3 仅用于启动脚本；无需插件、模型下载、GPU或网络。

在本目录执行：

```bash
# 从随附缓存与纹理重新生成 scene.blend
python build.py

# 从已交付工程重渲染两支完整视频
python build.py --reuse --render --camera both --work-dir ../scratch/rerender

# 只重渲染 T2
python build.py --reuse --render --camera T2 --work-dir ../scratch/rerender

# 检查单帧，不编码视频
python build.py --reuse --render --camera T1 --frames 52:52 --no-encode --work-dir ../scratch/check
```

也可直接运行：

```bash
blender -b --python build.py -- --reuse --render --camera both --work-dir ../scratch/rerender
```

若 `blender` 不在 PATH，设置环境变量 `BLENDER`。`--output-dir` 指定 MP4 输出目录，`--samples` 指定采样数（默认 8），`--threads` 指定 CPU 线程数（默认 8）。所有工程资源使用相对路径；移动时保留 `scene.blend` 与 `assets/` 的相对位置。重新构建不读取 `candidate/`，已有工程的渲染也不需要任何中间文件。

## 时间轴与标定

Blender 帧 1 对应源帧 `040434`、0 秒；帧 104 对应 `040743`、103/30 秒。视频覆盖 104/30 秒，不加片头、不变速、不删帧。源 WAV 为 166368 个采样；导出末尾仅补 32 个静音采样以填满视频时间，声音内容不作其他处理。

原图 1334×2048。内参分别按 `668/1334`、`1024/2048` 缩放，不裁切。相机外参按 OpenCV 的右、下、前轴转换为 Blender 的右、上、后轴。焦距、主点偏移及像素纵横比共同实现非完全相等的 fx/fy。几何沿用标定单位，工程显示为毫米。

打开工程后选择 `T1` 或 `T2` 场景、进入相机视图并切换材质预览/渲染模式。时间轴 1–104 驱动原生形态键和图像序列，声音轨从帧 1 开始。可编辑网格、形态键、UV、相机及独立头枕代理；无需启用自动运行 Python。

## 重建方法与边界

仅使用随题的三个同步视角。表面由前景轮廓约束、圆柱参数化多视角光度匹配、五官三角测量校正及空间/时间平滑估计；逐帧纹理经可见性判断与线性颜色融合，两个目标机位使用同一外观。环境用黑色背景与头枕代理近似；输入侧视图中无法跨视角可靠定位的离散背景灯点未单独重建。

这是基于有限观测的近似动态表面重建，不是原始扫描网格的恢复。眼睛、牙齿和口腔主要保留在随帧外观中，没有独立的眼球、牙列或表情骨骼；不可见后脑、画外肩部延伸及头枕背面为推断形状。耳缘、鼻翼、眼角与下颌的遮挡处仍可能有纹理拉伸和几何偏差。材质保留了拍摄光照，使用发光着色重现原观感，不是可任意重新布光的分离反照率资产。未声称逐像素复现未知目标画面。

## 来源与授权

输入素材：Multiface (Meta)，CC BY-NC 4.0。来源记录随附于 `assets/SOURCE.txt`。本交付中的派生纹理和表面遵循素材的署名及非商业使用限制；未获取隐藏机位、原始网格或外部人物素材。

## 验收记录

`assets/validation.json` 记录视频规格、逐帧变化、原声音频相关性和视频校验值；`assets/project_validation.json` 记录共享网格、闭合拓扑、104 个形态键、相机投影误差及本地资源路径检查。`assets/relocation_validation.json` 记录独立目录重开后第 52 帧的双机位重渲染对照结果。
