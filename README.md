# OmniALE 案例仓库

统一构建和展示专业音视频智能体评测案例。

- 案例目录：https://vibrant700.github.io/omniale/
- 采样率与混叠：https://vibrant700.github.io/omniale/sampling/

GitHub Pages发布目录为main分支的/docs。每个Case使用独立子目录，在docs/index.html维护入口。页面使用原生HTML/CSS/JavaScript，无构建依赖。本地预览：python -m http.server 8765 --directory docs。

当前题面0.4-draft，已完成一次GPT-6-luna独立制作及GPT-6.1独立部分评审。已审42/83，17分因无可用听觉接口待审，formal_score=null，关键图示、动态及必要内容门槛失败。结果见页面#results-v04。围绕“采样不足怎样改变声音，事后提高文件采样率能否补救”制作60—120秒教学片；例子、参数和动画方式自主选择，不再强制双成分或连续扫描。候选包只提供知识、两段原始声音、风格参考及通用工具，处理结果由模型制作。基础模板源码在cases/sampling/tools/。

被测模型负责制作与交付，评测侧负责评分。grade.py仅生成文件清单及空评分，finalize.py仅汇总评审；知识与音画质量需外部评审依据成片判断。私有评测材料不在公开仓库。新版教师审核、环境预检与质量标准校准仍待完成。

Luna实际测试版本为0.3-draft。其101秒原片、原题包、74分临时评审与31条审核后的工具记录保留在docs/sampling/results/luna-v03/。74分不是脚本自动评分，正式成绩仍待复核，不能代表0.4。两次同会话流程自测不参与排名。0.3.1题包与评测材料另在本地private/versions/归档。

页面的3 kHz／1 kHz波形交互是保留的原理演示，不属于0.4候选输入，也不是模型答卷。当前题面可以在页面内展开阅读；历史题面与结果独立标明。
