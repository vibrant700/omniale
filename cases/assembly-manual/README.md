# 装配录像核查与图解手册

展示页：https://vibrant700.github.io/omniale/assembly-manual/

输入：HoloAssist公开变调版推车装配录像，18分31秒，英文指导与第一人称画面；十题中文核查单。Sol输出：问答、9页Word/PDF手册、26张原始截图与26份SVG标注源。

受测：gpt-6.1-sol＋Official Codex CLI 0.142.4，累计模型与工具运行约103分15秒，无人为总时长和工具次数限制。本地Whisper辅助转写，无原生音频输入；交付封存后评价。

结果：63.11/100。问答31.25/50、证据9.333333/20、手册14.525/20、设计8/10。事实按原数据集标注；GPT-6-astra评审，Gemini核听音频，脚本汇总。

Sol与Luna共用上述展示页，点击模型卡片或选择“查看交付”，同步切换手册、问答、逐题评分和下载文件。Luna可直接定位：https://vibrant700.github.io/omniale/assembly-manual/?model=luna#systems

新增受测：gpt-6-luna＋Official Codex CLI 0.142.4，独立初始上下文，问答后在同一会话中制作手册；累计模型与工具运行约32分35秒，81次工具调用、15次本地Whisper调用，无人为总时长和工具次数限制。实际交付为6页Word/PDF手册、7组原图／标注PNG／SVG源，共21份配图素材。

Luna结果：54.64/100。问答26.25/50、证据7.666667/20、手册12.725/20、设计8/10。两系统的输入、Codex二进制、容器及Whisper权重哈希相同。分别由GPT-6-astra验收交付，复用相同源音频的Gemini观察，事实以原标注为准。推理强度采用模型目录默认值：Sol为low、Luna为medium；原生会话记录未独立声明该参数，不将其描述为经过请求级验证的相同推理设置。

公开内容仅为审核后的题面、实际交付、展示用评分依据与哈希；不包含API凭据、宿主路径、原始运行记录或私有原始标注。视频许可CDLA-Permissive-2.0，不表示由数据集作者审核。

静态页面无需构建依赖，在docs目录启动HTTP服务即可预览。页面生成工具位于build_case_page.py及build_luna_page.py，原Sol模板位于site-template/，合并展示模板位于comparison-template/；生成工具需要组织者本地封存资料，不包含在公开输入中。先构建Sol，再构建Luna以生成合并页。data.json的systems字段包含两份独立结果，资源位于results/sol/及results/luna/；旧luna/地址仅跳转到合并页。媒体由页面相对路径及GitHub Release提供。
