# Multiface 动态三维头部重建案例

展示页： https://vibrant700.github.io/omniale/multiface/

已完成实验：gpt-6.1-sol / xhigh / Codex CLI 0.142.4。CPU 4 核、8 GB，后台 Blender 5.3。
Agent 自行完成，累计 107 次工具调用；无外部墙钟时限。时长 3047.39 秒。

`docs/multiface/` 包含可直接播放的三个输入视角、原声、两个保留视角的真值与提交对照、指标与分数记录。
`build.py`、`render.py` 等是封存提交中的实际代码；完整 Blender 工程及依赖见页面链接的 Release 附件。
`evaluate_visual.py`、`evaluate_avsync.py` 为实际评测入口，保留当时目录约定，需按本地素材、运行时与缓存目录适配后使用。
图像/视频原始指标与合成分分别保留；合成分是事后约定、未经专家校准的换算，不是准确率。
`task-original.txt` 为冻结题面原文，其原始试跑评分段落已由页面中的视觉60＋同步40协议替代，未修改历史题面。

素材来源：Multiface, Meta / Facebook Research, https://github.com/facebookresearch/multiface 。
素材及衍生媒体按 CC BY-NC 4.0 使用：https://creativecommons.org/licenses/by-nc/4.0/ 。
网页预览将原始无声画面缩小到 668×1024 并附加题目原声；Agent 的两支 MP4 保持封存字节不变。
评测使用原始无损帧，不使用页面压缩预览。保留视角在本次求解时完全隔离，现在仅为结果分析公开。
本案例只有一段约3.47秒的短表演和一次有效提交，不能据此推断长序列或整个模型的能力。
