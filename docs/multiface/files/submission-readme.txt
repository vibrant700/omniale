# 动态三维头部重建交付

## 文件

- `scene.blend`：可独立重开的动态三维工程；相机严格命名为 `T1`、`T2`，另保留三个输入标定相机。
- `T1.mp4`、`T2.mp4`：各 104 帧，668×1024，恒定 30 fps，H.264 / AAC；第 1 帧和原声音轨起点对齐。
- `assets/reconstruction.npz`：世界坐标中的网格、104 组顶点位置、跨输入视角的表面纹理置信度。
- `assets/I1`、`I2`、`I3`：104 帧的输入观测纹理序列，使用工程相对路径；不是目标视角成片。
- `assets/cameras.json`、`speech.wav`：原始标定与未变速、未增益的原始录音。

## 方法与编辑

这是无预训练模型的近似多视图重建。先提取三个输入机位的头部轮廓；测量鼻尖、鼻梁、眼眶、嘴角、下颌和耳部的跨机位对应点，以标定光线三角化得到空间深度，用正则化薄板曲面拟合正面深度。曲面沿标定的正面相机光线采样，连接后脑和边界，形成有实际厚度的三维头颈网格。

使用多尺度 Lucas–Kanade 图像运动估计，将三个观测机位的位移通过投影雅可比和可见性权重求解为逐顶点三维位移。动画存为 104 个可编辑形态键，不依赖 Python 回调。材质在同一个世界坐标曲面上投射三个输入序列，以表面法线、前景及遮挡置信度混合；该权重不随 T1/T2 切换，不存在目标机位视频贴面或相机绑定背景。采用自发光材质保存已包含采集照明的观测颜色。

保持原始世界坐标和单位。相机使用 `R.T @ diag(1,-1,-1)` 转换到 Blender；K 横向按 668/1334、纵向按 1/2 缩放，使用镜头偏移和像素长宽比表达主点与 fx/fy 的微小差异。没有整体稳定、二次裁切或时间偏移。第 n 帧对应 `(n-1)/30` 秒。

## 重开与重渲染

将整个交付目录放在一起，打开 `scene.blend` 即可选择 T1/T2、任意帧直接渲染。不需要 candidate、scratch 或运行中的求解器。

```bash
blender -b -t 4 --python build.py
blender -b -t 4 --python render.py -- --camera both --frames-dir /path/to/temp/render
```

第一条仅使用交付的 assets 重建工程；第二条实际重新打开 scene.blend，渲染并用 FFmpeg 编码合入原声。也可只指定 `--camera T1` 或 `--camera T2`。需要 Blender 5.3、FFmpeg。

从公开原素材重新估计全部资产需要 Python3、NumPy、Pillow，目录布局为同级 `candidate/`、`scratch/`、`submission/`：

```bash
cd /path/to/workspace
python3 submission/reconstruct.py --source candidate --work scratch
python3 submission/fit_surface.py
python3 submission/animate.py --source candidate --work scratch
python3 submission/finalize_assets.py
blender -b -t 4 --python submission/build.py
blender -b -t 4 --python submission/render.py
```

`reconstruct.py` 也保留了轮廓外壳与切平面照片匹配的试验步骤；最终几何使用 fit_surface 的稳定约束曲面，而非不稳定的光度精修结果。

## 实际检查

已由 `render.py` 重新打开最终 `scene.blend`，实际完成 T1/T2 各 104 帧渲染和 MP4 编码。已查看两支编码成片的第 1、26、51、76、104 帧。ffprobe 确认两支均为 H.264、668×1024、30/1 fps、104 帧，视频时长 3.466667 秒；AAC 为 48kHz 单声道，音视频起点均为 0。解码音轨相对原 WAV 的零延迟相关系数均为 0.999947，信噪比约 39.61 dB。AAC 尾部含常规编码填充。

## 已知限制

这是有限三个视角下的近似曲面重建，不是扫描级结果。面部深度、耳部、后脑和裁边外区域有人工约束与补全；无独立牙齿、舌头和完整口腔拓扑，口内外观主要由观测纹理表达。光流在弱纹理和遮挡处可能产生误差，细微表情、眼球和口型的空间对应不能保证精确；侧面投影接缝和未观测区域仍可能失真。没有获得或使用目标画面、原始扫描或额外人物资产。

素材来源：Multiface (Meta)，CC BY-NC 4.0。仅使用题目提供的公开素材；输出及衍生纹理应遵守原素材的非商业授权。
