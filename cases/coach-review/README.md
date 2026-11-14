# 整局游戏证据审计与配音复盘

展示页：https://vibrant700.github.io/omniale/coach-review/

基于OmniGame-Bench game_moba_lol_fp_001，公开题包v5，问答50＋实际解说20＋实际成片音频20＋剪辑10。受测系统为指定模型＋官方Codex CLI 0.142.4。

累计运行时长：Astra约60分34秒，GPT-6.1-sol约138分20秒，GPT-6-luna约36分35秒。统计模型与工具的累计运行时间，含渲染，不含暂停间隔与评分时间。

公开数据：docs/coach-review/data.json。仅导出审核后的题面、封存答案与解说稿、裁判观察、分项和媒体哈希；不发布密钥、宿主会话、完整工具轨迹或私有原始标注。原片在GitHub Release，网页预览为960px宽/30fps，时长完整，原AAC音轨直接复制，未替模型修正内容。

最终分数与分项见页面，不设目标分或答案上限。内容裁判为GPT-6.1-sol，听评为Gemini3.1ProPreview。内容裁判与Sol受测模型同系列，非人工盲评。

前端是静态HTML/CSS/JS，无构建依赖；本地可在docs目录运行python -m http.server。设计参考：https://huayuankou333.github.io/omniale/voice-reconstruction/ 。素材原有权利与条件不因本页面改变。

Luna最终得分32.84/100：问答6.5、解说9、音频11.7962、剪辑5.5477。成片约172.79秒，部分问题未回答或证据事件不对应。H07提交端点B已复活，尽管局部链有效，端点错误仍按原问答规则扣分。
