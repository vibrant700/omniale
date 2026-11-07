# OmniALE 案例仓库

统一构建和展示专业音视频智能体评测案例。

- 案例目录：https://vibrant700.github.io/omniale/
- 采样率与混叠：https://vibrant700.github.io/omniale/sampling/

GitHub Pages发布目录为main分支的/docs。每个Case使用独立子目录，在docs/index.html维护案例入口。页面使用原生HTML/CSS/JavaScript，无构建依赖。

公开内容仅包含题面、原创候选素材、候选包、评分结构和真实测试状态。没有受测模型成绩或运行轨迹；不包含私有参考成片、答案目录或评分器。

本地预览：python -m http.server 8765 --directory docs

页面波形演示是额外的科普交互，不是受测模型答卷或实验结果。示例声音为程序合成；来源和方法随候选包提供。
