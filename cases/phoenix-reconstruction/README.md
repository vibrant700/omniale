# 凤凰角色重建与新机位有声动画

展示页：../../docs/phoenix-reconstruction/ 。此案例沿用同仓库 SCV 页的章节、播放和下载布局。

`index.html`、`style.css`、`app.js` 是页面源文件。构建依赖 Python 3 与 Pillow：

```sh
python cases/phoenix-reconstruction/build.py --source /path/to/phoenix-multiview-v1
```

`models.json` 只登记已完成并已评分的运行。总览表读取按当前协议生成的 `score.json`；选择模型后，成片、评分文件、执行过程与十帧分析共同切换。每个模型的文字记录放在 `models/<模型ID>/{results,execution,analysis}.html`，逐帧分析放在同目录的 `observations.json`。后续模型沿用该结构添加登记与真实记录，不加入未测模型占位。

各模型的交付和评分位于 `docs/phoenix-reconstruction/results/<模型ID>/`，其对比图和逐帧数据放在 `comparison/`。参考录像、目标参考与题目配置共用。添加模型时，填写其实际运行目录、交付 ZIP 名称及独立记录中的资源路径；构建器检查模型身份、十帧列表与分数汇总，并给新模型的片段生成独立 DOM ID。

计分协议为 `phoenix-ten-frames-iou-f1-ssim-audio-v2`：机位二维覆盖度（四机位轮廓 IoU）30 分、三维几何 F1 30 分、成片外观（RGB SSIM）30 分、音效 10 分。`scoring.py` 从十帧与四机位测量结果计算均值和分数；构建时生成当前 `score.json`、`PROTOCOL.json` 和只保留当前图像指标的 `image_metrics.json`，记录输入文件哈希与协议版本。原始测量及旧协议评分在本地归档保留，不覆盖。

构建只发布明确列出的实际输入包、原始交付、当前评分 JSON 和可公开媒体。所有 JSON 下载入口位于页面 Astra 实际评分区；前 90 分按十帧计算，音效采用委托方提供并确认的 Gemini 4 Neon 原始报告。公开文件 SHA-256 见页面 `manifest.json`。

原始 GLB、参考 Blender 工程、凭据、远程入口、未审查的原始运行记录均不发布。输入与交付 ZIP 保留原始字节；对比图仅做等尺度显示裁切，不参与计算。

浏览器核验需要 Playwright 和 Chromium，使用独立的本地静态服务器检查相对资源、十帧切换与键盘操作、图像放大、全部音视频解码播放、桌面及 390/375 像素手机布局，并保存截图与 JSON 报告：

```sh
python cases/phoenix-reconstruction/check_page.py --serve --output /path/to/qa
```
