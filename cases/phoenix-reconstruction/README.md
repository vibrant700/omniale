# 凤凰角色重建与新机位有声动画

展示页：../../docs/phoenix-reconstruction/ 。此案例沿用同仓库 SCV 页的章节、播放和下载布局。

`index.html`、`style.css`、`app.js` 是页面源文件。构建依赖 Python 3 与 Pillow：

```sh
python cases/phoenix-reconstruction/build.py --source /path/to/phoenix-multiview-v1
```

构建只复制明确列出的实际输入包、原始交付、最终 JSON 和可公开媒体。所有 JSON 下载入口位于页面 Astra 实际评分区；前 90 分按十帧计算，音效采用委托方提供并确认的 Gemini 4 Neon 原始报告。公开文件 SHA-256 见页面 `manifest.json`。

原始 GLB、参考 Blender 工程、凭据、远程入口、未审查的原始运行记录均不发布。输入与交付 ZIP 保留原始字节；对比图仅做等尺度显示裁切，不参与计算。

浏览器核验需要 Playwright 和 Chromium，使用独立的本地静态服务器检查相对资源、十帧切换与键盘操作、图像放大、全部音视频解码播放、桌面及 390/375 像素手机布局，并保存截图与 JSON 报告：

```sh
python cases/phoenix-reconstruction/check_page.py --serve --output /path/to/qa
```
