# PL-NBA 中文篮球解说制作

展示页：https://vibrant700.github.io/omniale/plnba/

将12段无声比赛片段与含部分错误的引导稿，制作成带普通话旁白、中文字幕的复盘短片。实际题面见TASK.md；完整候选输入包在同仓库Release中。工具只提供制作能力，不提供事实答案、修订稿、配音或最终时间轴。

tools/speak.py与speak_local.py为实际试测提供的离线Piper入口，依赖已准备好的Piper运行时及huayan中文音色。默认部署路径C:/Users/Public/omniale_tts，跨环境复用时应调整为本机已安装的运行时位置。

数据来源：https://github.com/holhouse/PL-NBA-Dataset 。视频素材原有权利与使用条件不因本展示页而改变。公开候选包不含私有参考答案、评分事实单元、评委密钥或模型运行日志。当前是一次Astra试测及用户授权的Qwen重测，不代表多模型统计结果。
