# 声音制作环境约定

本文件随题提供。REAPER 属于出题方预先配置的软件工具，不是需要 agent 自行安装的任务内容。声音素材仍由 agent 自主检索和制作。

当前 V3 实验已在 Linux GPU 主机配置 REAPER 7.86、独立虚拟显示与原生 Lua 入口，通过 WAV 导入、内置 ReaEQ、工程保存／重开及六秒浮点 WAV 输出检查。实验实际使用的入口说明由页面构建器直接复制冻结输入中的 `ENVIRONMENT.md`。下文的 Windows 预检与安装步骤保留为出题方准备环境的记录，不替代实验主机的实际配置。

## 环境组成

- Blender：重建与渲染角色。
- REAPER：素材试听、多轨剪辑、变速、滤波、效果处理、包络自动化、混音与分轨导出。
- REAPER 随附的效果器及 ReaScript Lua／EEL2 支持：允许通过脚本制作并保存原生工程，不强制界面操作。不要求额外安装 ReaPack、SWS 或第三方音频插件。
- FFmpeg：音视频检查及最终封装。
- 网络检索、素材下载、文件读写及声音试听入口：供 agent 寻找并判断录音素材。只有软件名而没有可访问的执行入口，不算完成环境准备。

## 出题方在实验前完成

1. 在 agent 实际执行的主机安装 REAPER，使用官方来源：https://www.reaper.fm/download.php 。Windows 使用 64 位安装包；可采用普通安装或独立的 Portable install。REAPER 提供 60 天完整功能评估期，实验部署须满足软件许可条件。
2. 测试主机与 GPU 主机不同时，明确声音工程运行的位置及音视频传输目录，不能把出题方电脑上的安装视为远程 agent 已可使用的软件。
3. 在发给 agent 的本文件中补全实际操作系统、REAPER 版本、可执行文件绝对路径、启动与脚本执行方法、试听方式、可写工作目录，以及 Blender／FFmpeg 的使用入口。所有被测模型使用相同环境版本。
4. 用独立的临时素材验证：能启动软件、播放声音、导入片段、运行一段 ReaScript、保存并重新打开 `.rpp`、导出 48 kHz 立体声 WAV。该检查素材和示范工程不放入正式任务包。
5. 完成必要的首次启动设置，核验内置效果器和输出设备可用，保存软件版本、官方安装包哈希及实际启动／导出记录，然后冻结实验环境。

2026-11-26 本机 Windows CLI 预检已通过：REAPER **7.86/x64**，可执行文件为 `C:/Program Files/REAPER (x64)/reaper.exe`。在独立配置中实测 Lua 执行、WAV 导入、内置 ReaEQ、保存及重新打开 `.rpp`、命令行离线渲染。输出已解码核验为 48 kHz、双声道、32 位浮点 WAV，288,000 个采样帧，恰好 6 秒，含非零有效音频。

本机实际扬声器试听尚未验证。Linux GPU 主机的离线制作入口已另行验证，实际实验使用 Linux 配置；Windows 预检结果仅对应本机环境。

## 已验证的 CLI 方式

Windows 下通过 REAPER 自身的命令行入口运行 Lua；使用独立 `-cfgfile` 避免与交互工作配置混用。下面的工作目录和文件名需替换为实际路径，配置文件须预先准备。

```powershell
& 'C:\Program Files\REAPER (x64)\reaper.exe' -newinst -nosplash -cfgfile 'D:\work\reaper-agent.ini' 'D:\work\build_audio.lua'
& 'C:\Program Files\REAPER (x64)\reaper.exe' -newinst -nosplash -cfgfile 'D:\work\reaper-agent.ini' -renderproject 'D:\work\foley.rpp'
```

第一种方式可以调用 ReaScript API 导入素材、调整轨道及效果器并保存工程；第二种方式根据 `.rpp` 中保存的渲染设置输出音频。两者均已实测，不依赖鼠标点击。

32 位浮点 WAV 的 sink 配置已验证为 `RENDER_FORMAT = "ZXZhdyAAAA=="`，通过 `reaper.GetSetProjectInfo_String` 设置；采样率、声道、起止时间仍须通过相应 `RENDER_*` 参数设置。不能只凭文件名或配置意图声称格式正确，输出后须解码核验。

## Agent 使用范围

请使用 REAPER 制作并交付可编辑的 `.rpp` 工程。可通过界面、ReaScript 或生成工程后在 REAPER 中打开验证的方式完成工作；工程必须保留真实可编辑的片段、声部和处理设置。工程命名及声音分组由制作方自行决定，并在交付说明中标明。素材源文件与工程采用可重定位的相对路径。

使用提供的内置效果器。脚本可以随交付保留，但不能以脚本或一条混音文件代替 `.rpp`。拟音设计、素材选择、对齐与动态处理由 agent 自行完成，环境不提供声音答案或预先排好的动作音轨。
