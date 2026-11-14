# 整局游戏证据审计与配音复盘

展示页：https://vibrant700.github.io/omniale/coach-review/

基于OmniGame-Bench game_moba_lol_fp_001，公开题包v5，问答50＋实际解说20＋实际成片音频20＋剪辑10。受测系统为指定模型＋官方Codex CLI 0.142.4。

展示Astra与Sol延长预算后的真实完成成片，不作同预算排名。Astra为截止后执行原渲染命令；Sol首轮未完成，文件接手后经环境中断与原生恢复完成。原正式超时结果不被覆盖。

公开数据：docs/coach-review/data.json。仅导出审核后的题面、封存答案与解说稿、裁判观察、分项和媒体哈希；不发布密钥、宿主会话、完整工具轨迹或私有原始标注。原片在GitHub Release，网页预览为960px宽/30fps，时长完整，原AAC音轨直接复制，未替模型修正内容。

评分器的原始分与复核分见页面；复核不重新评音频，不设目标分或答案上限。内容裁判为GPT-6.1-sol，听评为Gemini3.1ProPreview。内容裁判与Sol受测模型同系列，非人工盲评。

前端是静态HTML/CSS/JS，无构建依赖；本地可在docs目录运行python -m http.server。设计参考：https://huayuankou333.github.io/omniale/voice-reconstruction/ 。素材原有权利与条件不因本页面改变。
