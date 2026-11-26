# OmniALE

## 案例目录

| 案例 | 任务 | 主要交付 |
| --- | --- | --- |
| [采样率与混叠](https://vibrant700.github.io/omniale/sampling/) | 将数字音频知识制作成中文教学短片，用动画和试听解释采样与混叠 | 教学视频、音轨、字幕与可重建工程 |
| [AG 五人第一视角战术大屏](https://vibrant700.github.io/omniale/coach-review/) | 同步五路选手录像，估算对敌方英雄的输出与承伤，制作动态复盘大屏 | 双榜视频与累计时间轴 |
| [装配录像理解与图解手册](https://vibrant700.github.io/omniale/assembly-manual/) | 理解远程指导录像，回答操作问题，并整理带截图标注的手册 | 问题回答、Word／PDF 手册与可编辑标注 |
| [Multiface 动态三维重建](https://vibrant700.github.io/omniale/multiface/) | 根据三个同步视角及原声重建动态场景，在目标机位渲染视频 | 三维工程与目标视角有声视频 |
| [SCV 机甲重建与展示片](https://vibrant700.github.io/omniale/scv-showcase/) | 根据六方向参考图重建机甲，结合指定配乐和音效制作展示片 | 可编辑三维资产与有声展示视频 |
| [凤凰角色重建与新机位有声动画](https://vibrant700.github.io/omniale/phoenix-reconstruction/v3/) | 根据三个同步参考录像重建变速拍翼动画，自主寻找声音素材并使用 REAPER 拟音 | Blender 与 REAPER 工程、有声视频、无损混音与分轨 |

## 仓库结构

```text
docs/
├── index.html          # 案例目录
├── sampling/           # 采样率与混叠
├── coach-review/       # 比赛复盘大屏
├── assembly-manual/    # 装配理解与操作手册
├── multiface/          # 动态三维重建
├── scv-showcase/       # 机甲重建与展示片
└── phoenix-reconstruction/ # 凤凰角色重建与新机位有声动画

cases/
└── <案例目录>/          # 可公开的构建源码、工具与说明
```
