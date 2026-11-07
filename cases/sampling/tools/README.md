# 基础动画模板
这是可替换的通用 Python/Pillow 动画模板，不含采样、混叠、完整分镜或时间轴。可自由修改或改用其他工具。

安装 requirements.txt 后运行：
python example.py
输出 preview.mp4，示范文字、坐标转换、曲线与移动标记。默认画布和帧率只是模板设置，不是题目硬性规格。中文字体使用 Windows 微软雅黑；其他系统通过 CASE_FONT 指定合法中文字体文件，不随包分发字体。图标可用基础几何形状自行绘制，不强制使用固定图标。

制作时在自己的工程中使用 animation.py 的 render 函数，编写 draw_frame(t, canvas)；t 是视频秒数。使用 polyline 将数据坐标映射到绘图区。渲染函数负责帧编码；compose 将画面、实际音轨与可选SRT合并，字幕同时作为独立文件交付。

配音入口：
python speak.py --text narration.txt --out narration.mp3
配音使用 edge-tts，需联网；voice 可通过 --voice 修改。主办方须在实际测试环境预检服务可用性。网络服务当前状态不由模板保证，不可将服务不可用计为模型能力错误。也可使用主办方已验证的其他配音引擎。

模板不自动生成教学内容、示例结果、旁白或素材与事实对应表。现有音频可用也可不用。
