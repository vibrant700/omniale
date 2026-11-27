# Phoenix：角色重建与自主拟音

使用六秒变速拍翼视觉参考，取消随题音效，新增自主检索录音、可编辑多轨工程、分轨与来源说明。由 agent 自行决定声源、层次与分组，不在题面预设声音类别、分轨数量或制作步骤。音效采用十项二元 checklist，每项 2 分，总权重为 30／30／20／20。

- `TASK.md`：面向被测 agent 的任务委托。
- `SCORING.md`：视觉计分、音效 checklist、评审有效性及工程验收约定。
- `index.html`、`style.css`、`models.json`、`build_page.py`：公开页模板、样式、模型登记与允许清单构建器。新增模型使用独立 run，配置其 REAPER 工程、混音和分轨路径，结果区与逐帧对照随模型选择切换。
- `check_page.py`：检查文件哈希、原始输入和交付边界、分项计分、九路媒体播放、十帧交互和手机布局。本次根据委托方明确要求，将其提供的 Gemini 4 Neon 报告作为页面声音评分；原始报告的校准与人工复核标记如实保留。
- `ENVIRONMENT.md`：由出题方提供 REAPER、内置效果器、FFmpeg 及软件使用入口的环境准备约定。声音交付为可编辑 `.rpp`；CLI 与自动化方式只在环境说明中提供，不写进任务委托。
- Astra 6.2 xhigh + Codex 已完成一次实验；本地记录位于 api-nju 项目的 `outputs/phoenix-multiview-v3/`。历史实验成绩不移用。当前权重为实验后按委托方要求调整的计分修订，保留原始协议和评审，不冒充实验前冻结权重。
- 参考视频和相机、时间轴、场景配置保留实验输入的原始字节，评测端原始资产与真值不分发。
- 最新权重说明审阅包位于被忽略的 `private/phoenix-v3-audio20-draft/`；此前各草案原样保留。此包是题目审阅包，不是已完成实验的原始冻结输入。尚未更新展示页或发布。
- 本机 REAPER 7.86/x64 已通过隔离配置下的 Lua、内置效果器、工程保存／重开及 6 秒浮点音频导出预检。内部证据位于 `private/reaper-preflight/2026-11-26-setup01/verification.json`，不分发测试音频或示范工程。
- 运行前须固定执行环境、评委及复核者身份，核验声音软件与网络检索工具可用，并将输入清单和评审版本冻结归档。

公开页构建：

```sh
python cases/phoenix-reconstruction/v3/build_page.py --archive /path/to/phoenix-multiview-v3 --reference-archive /path/to/visual-reference --repo /path/to/omniale
```

构建直接核验实验冻结输入及原始交付 SHA-256，仅发布允许清单中的资料。输入包保留实验原始十个文件；当前计分说明单独提供。修改权重不改写历史输入，公开目录只保留当前任务，历史页面和构建源码已移至本地私有归档。
