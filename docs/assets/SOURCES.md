# 素材来源

音频由本题 authoring/build_case.py 使用数学信号程序生成：48 kHz主时钟、3 kHz和1 kHz余弦、统一包络和短淡入淡出，不包含真人声音或商业音乐。

source_3000.wav是3 kHz原始试听。safe_1000.wav为1 kHz辅助试听。aliased_1000.wav先在4 kHz上采集3 kHz余弦的样本，再按离散信号重建到统一播放率；filtered.wav在降采样前用低通滤波抑制3 kHz。准确步骤与文件哈希见manifest.json。

动态风格参考为程序原创几何动画，不包含任务答案。知识参考链接见knowledge.md。自建输入素材允许在本Case中复制、编辑和再分发；外部文献保持各自版权，不随包分发。
