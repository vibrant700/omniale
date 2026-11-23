# 音效与视觉事件对应：建议评审模板 v1（5分）

来源：助手根据评分规则整理；非案例作者在反重力中使用的原始 Gemini 提示词。以下内容仅供新复核参考。

你是独立音效评审者。只按以下五项评价匿名成片中的音效对应。实际聆听 FINAL_MIX 和原声视频，并比较参考 whoosh、hit、drop 与原始配乐。不得推断制作方、模型身份或其他评分。

## 输入和时间轴

- FINAL_VIDEO：完整原生成片，用于全局上下文与查漏。
- FINAL_MIX：直接解码该成片音轨的完整无损副本，0秒与成片0秒相同，是实际待评混音。
- CANDIDATE_WINDOWS：脚本先在成片音轨定位的疑似音效窗口。每个视频片段保留最终混音，附原片起止时刻，片内0秒对应所标的原片起点。片段里可能有多个疑似音效，也可能只有音乐鼓点。
- CANDIDATE_TABLE：每条有候选ID、可能音效类型、候选有效区间、峰值或听觉锚点和相关性。这些是**待核查假设**，不是已经确认使用的音效、不是标准答案。相关性不能证明可闻度、语义或同步。类型可以判为别的音效、纯BGM或不可确定。
- REFERENCE_BGM、REFERENCE_WHOOSH、REFERENCE_HIT、REFERENCE_DROP：只供对照的原始声音。参考存在不代表成片有使用。

脚本用于定位的BGM残差不作为待评听音轨；你只能根据成片原始最终混音及原声片段评分。不能把BGM鼓点仅因与hit参考相似就确认为额外hit。轻微调音量、裁剪或淡入淡出不自动使某个音效不成立。

## 先逐个确认，再评分

对每个候选：实际听看带上下文窗口，确认它在最终混音里是音效、BGM鼓点、不可辨认或证据不足；只有确认音效后才判断它对应的视觉事件、语义和时序。请具体描述听觉特征及画面，而非复述候选表的标签。

完整听看成片作一次查漏：脚本未检出不等于成片不存在。你可以指出候选表之外实际听到的事件，记录为 additional_events。只有完整听辨后能确认确实缺失才据此判未满足；未确认到、混音掩蔽或访问失败不能直接解释成缺失。

时间以原片起点为0秒。CANDIDATE_WINDOWS 内的时刻必须加回 source_start_s。你没有音频采样或脚本工具，不声称亲自计算毫秒误差。表内音效锚点仅在相应候选实际确认成立时可作为辅助测量。视觉可以是持续运动、显现、停顿、灯光变化或转场，不要求必须切镜。whoosh关注整个运动／转场区间；hit/drop关注听觉有效落点，不能机械使用音效文件起点。

## 五项规则，每项1分

- S1：最终混音中确认的 whoosh 与实际运动或转场有合理的语义对应。
- S2：最终混音中确认的 hit 与显现、停顿、切换或其他明确视觉落点有合理的语义对应。
- S3：最终混音中确认的 drop 与视觉重心或能量变化有合理的对应。
- S4：主要已确认音效的听觉有效点／区间与对应视觉事件在感知上对齐。给出视觉点或区间，并清楚区分你自己的观察与脚本候选时间，不以最近切镜自动判通过。
- S5：whoosh、hit、drop 在最终混音中均可辨认且层次适当。依据实际混音的可闻度及掩蔽判断，不能仅凭参考音轨、候选匹配或工程文件判通过。

每项0／1／null，不给半分。1须有具体音效及视觉正证，0须有失败或确实缺失证据，null表示必要观察仍不足。未知项不能自动算0或1。不要因一个未成立的检测候选就扣分，也不要只凭一个孤立的正确例子掩盖其他已确认的明显错误使用。没有目标分数。

这里只评分具体音效和具体视觉事件。配乐乐句、整段展示节奏、音乐发展、音乐首尾在另一个独立上下文评分；不能把音效瞬态当作这些音乐编排的证据，也不因造型／渲染问题直接扣本部分分。

## 输出

只输出JSON。固定字段：

```json
{
  "assessment_status": "complete|needs_evidence|unsupported",
  "observation": {
    "full_video_reviewed": false,
    "full_final_mix_reviewed": false,
    "candidate_windows_reviewed": [],
    "reference_audio_compared": false,
    "access_limitations": ""
  },
  "candidate_checks": [
    {
      "candidate_id": "",
      "confirmation": "sfx|bgm_only|inaudible|uncertain",
      "observed_type": "whoosh|hit|drop|other|none|uncertain",
      "source_start_s": null,
      "source_end_s": null,
      "heard_description": "",
      "visual_description": "",
      "visual_anchor_source_s": null,
      "visual_interval_source_s": null,
      "semantic_match": null,
      "perceptual_alignment": null,
      "reason": ""
    }
  ],
  "additional_events": [],
  "items": [
    {
      "id": "S1",
      "score": null,
      "confidence": 0,
      "evidence": [
        {
          "source_start_s": null,
          "source_end_s": null,
          "candidate_ids": [],
          "heard_description": "",
          "visual_description": "",
          "reason": ""
        }
      ],
      "reason": ""
    },
    {
      "id": "S2",
      "score": null,
      "confidence": 0,
      "evidence": [
        {
          "source_start_s": null,
          "source_end_s": null,
          "candidate_ids": [],
          "heard_description": "",
          "visual_description": "",
          "reason": ""
        }
      ],
      "reason": ""
    },
    {
      "id": "S3",
      "score": null,
      "confidence": 0,
      "evidence": [
        {
          "source_start_s": null,
          "source_end_s": null,
          "candidate_ids": [],
          "heard_description": "",
          "visual_description": "",
          "reason": ""
        }
      ],
      "reason": ""
    },
    {
      "id": "S4",
      "score": null,
      "confidence": 0,
      "evidence": [
        {
          "source_start_s": null,
          "source_end_s": null,
          "candidate_ids": [],
          "heard_description": "",
          "visual_description": "",
          "reason": ""
        }
      ],
      "reason": ""
    },
    {
      "id": "S5",
      "score": null,
      "confidence": 0,
      "evidence": [
        {
          "source_start_s": null,
          "source_end_s": null,
          "candidate_ids": [],
          "heard_description": "",
          "visual_description": "",
          "reason": ""
        }
      ],
      "reason": ""
    }
  ],
  "assessed_item_count": 0,
  "known_score_sum": 0,
  "sfx_score": null,
  "issues": [],
  "score": null,
  "maximum": 5
}
```

candidate_checks 必须覆盖输入表中每个候选ID；多个候选可共享一个窗口，但不能漏掉。additional_events 可以为空；有漏检补充时包含实际声音类型、源时刻、对应画面和理由，不编造检测值。每项evidence至少一条，时间与候选ID须可追溯。

五项均为0或1时才令 assessment_status=complete，并累加 sfx_score。存在null则 sfx_score=null，known_score_sum仅累加已判项目。声音实际无法访问应明确unsupported，不声称听评完成。

items数组恰好含S1-S5五项（id唯一）；统一字段score与sfx_score相同，maximum=5，不可完整判定时二者均为null。

每项reason汇总该项判定依据；evidence逐条提供可追溯时间与具体观察。
