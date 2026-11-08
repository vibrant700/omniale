# OmniALE 案例仓库

统一构建和展示专业音视频智能体评测案例。

- 案例目录：https://vibrant700.github.io/omniale/
- 采样率与混叠：https://vibrant700.github.io/omniale/sampling/

GitHub Pages发布目录为main分支的/docs。每个Case使用独立子目录，在docs/index.html维护案例入口。页面使用原生HTML/CSS/JavaScript，无构建依赖。

公开内容仅包含题面、原创候选素材、候选包、评分结构和真实测试状态。已公开gpt-6-luna新上下文制作的101秒原片、技术外评暂计74/100、问题证据与审核后的31条工具记录；正式成绩仍待复核。两次开发流程自测不参与排名。不包含私有参考成片、答案目录或评分器。

本地预览：python -m http.server 8765 --directory docs

页面波形演示是额外的科普交互，不是受测模型答卷或实验结果。示例声音为程序合成；来源和方法随候选包提供。

当前题面为0.3.1-draft，仅清理面向模型的出题说明和版本修订措辞，任务要求、评分权重和锚点含义与0.3保持一致，尚未重测。按“提出问题、用可检查的例子演示、说明结论”组织教学片，示例参数自主选择，要求双成分对照、连续条件变化与实际声音对应。基础动画模板源码在 cases/sampling/tools/，候选ZIP中包含相同工具。正式教师审核和统一受测环境预检仍待完成。

Luna实际测试版本为0.3-draft。其原题面与候选包保存在 docs/sampling/results/luna-v03/TASK.md 和 candidate-v03.zip，已与本地运行归档逐文件核对；原视频、轨迹和74分技术暂评未改写。页面将当前题包与实测题包分别标注。
