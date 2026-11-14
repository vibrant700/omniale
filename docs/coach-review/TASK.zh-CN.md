# 教练委托：整局证据审计与纠错复盘

你收到一局约42分钟的英雄联盟录像。教练需要一份可回查实战证据的纠错复盘，而非泛泛的战术总结。完成下列8项核查，交付结构化答案、证据剪辑和配音复盘。

## 交付

- submission/answers.json：按answers_template.json填写。时刻统一为原片播放秒，不是游戏内时钟。evidence中的每个t必须指向支持对应结论的代表性画面，observation写可见依据。H07的chain节点也必须填写这些信息。
- submission/review.mp4：实际剪出所用证据，配中文解说。章节标明H01—H08及原片时间；针对问题解释实际观察及纠错理由。可以合并共享片段，但每个结论与证据关系须清楚。
- submission/解说稿.md：与实际口播对应。
- 每题review_segments填写成片秒区间，例如[{"start":0,"end":12}]。H03需用对应片段展示本轮结果，不要求唯一的事件起止秒。

## 核查任务

### H01 同一建筑的跨阶段审计（8分）

找到早期对线时玩家在蓝方中路外塔旁打开商店的回城、后来该位置附近伴随建筑摧毁公告的回城，以及紫色远程对手带红方兵线经过这处位置的事件。跟踪同一座蓝方中路外塔，填写三次的建筑状态；另填写第二次回城时摧毁公告所指建筑的阵营。每个结论须有对应证据，不得把不同建筑当作同一对象。

答题字段：early_tower: ['standing', 'destroyed']；later_recall_tower: ['standing', 'destroyed']；enemy_push_tower: ['standing', 'destroyed']；announced_destroyed_tower_team: ['blue', 'red']

证据槽：early_recall、later_recall、enemy_push。

### H02 相似商店界面的本体状态（5分）

定位低血量中路交战之后的推荐商店画面，以及蓝色标记下方狼形营地事件之后的推荐商店画面。分别填写玩家本体是否存活，并为两次判断各写出实际画面依据。

答题字段：after_mid_alive: boolean；after_wolves_alive: boolean

证据槽：shop_after_mid、shop_after_wolves。

### H03 相似进攻的结果核验（5分）

审核两次进攻的直接结果：早期对线对手出现回城圆环之后的中路推塔，以及玩家随蓝方兵线和队友进行的侧路推塔。分别填写本轮进攻后目标塔的状态，提交能证明本轮结果的代表性画面和对应片段；不能用更晚另一轮进攻的结果代替。

答题字段：mid_push_result: ['standing', 'destroyed']；side_push_result: ['standing', 'destroyed']

证据槽：mid_push、side_push。

### H04 跨营地的目标对应（5分）

定位蓝色标记下方凹地的一次营地攻击，以及较晚侧路推塔区域外岩石营地的那次攻击。分别填写该事件被攻击营地中可见的目标组成（single或pack），并指出实际对应的攻击目标。不能把邻近营地、其他时刻或怪物消失后的画面代替被问事件。

答题字段：blue_mark_camp: ['single', 'pack']；rocky_camp: ['single', 'pack']

证据槽：blue_mark_attack、rocky_attack。

### H05 同一玩家在两处边界中的位置（5分）

定位大型紫色野怪可见的坑口事件，以及攻击绿色翅膀巨龙的事件。跟踪玩家本体，分别填写它相对两处坑体边界的位置（inside或outside），并在证据描述中指出你跟踪的是哪一个角色以及边界在哪里。

答题字段：purple_pit: ['inside', 'outside']；dragon_pit: ['inside', 'outside']

证据槽：purple_pit_event、dragon_pit_event。

### H06 远距离重现的对手身份（4分）

比较早期中路大型敌方角色加入的事件与后来裸露红色基地水晶旁的交战：早期紫色远程对线者是否在后者中再次出现？填写判断，并在两个事件中分别指认对应角色、给出同一对象或不同对象的核对依据。单独填写一个判断、只找到其中一次出现，均不能完成本项。

答题字段：same_ranged_opponent: boolean

证据槽：early_opponent、base_opponent。

### H07 无中间提示的本体状态轨迹（10分）

anchors/endpoint_A.jpg和endpoint_B.jpg来自原片同一有序区间的两个端点，A在B之前。请定位这两个画面，在其间自行寻找证据，恢复一条能证明玩家本体发生状态转变的时间链。每个节点填写时刻、alive布尔值和可见依据；按时间排序。根据所提交且被证据支持的链，填写复活次数下界和新增死亡次数下界，起点已发生的死亡不重复计入。无需证明链穷尽区间所有事件；连续相同状态不构成新转变。

答题字段：chain: array of {t:number, alive:boolean, observation:string}；min_respawns: nonnegative integer；min_new_deaths: nonnegative integer

证据槽：endpoint_A、endpoint_B。

### H08 后期复盘的多事实审核（8分）

核查教练草稿：“敌方四杀公告出现时，本体仍在行动；其后蓝方主基地防御塔附近的画面中，本体已经恢复行动，但主基地防御塔已全毁；较晚蓝色标记营地上方的冲突发生在基地外，本体当时仍未恢复行动。”逐项填写这些事件中玩家本体和建筑的实际状态，提供三处对应证据，并在解说中纠正草稿里的错误。不要假定草稿的所有句子都错，也不要把公告参与者等同于玩家本体。

答题字段：quadra_alive: boolean；base_alive: boolean；base_towers_standing: boolean；later_alive: boolean；later_outside_base: boolean

证据槽：quadra_event、base_event、later_camp_event。

## 作业条件

可使用本地代码、批量抽帧、剪辑和提供的语音合成工具。时间预算60分钟，最多240次工具调用。没有外网、私有标注或评分反馈。anchors两张图仅用于明确H07端点，不是中间状态提示。

答案与原片相矛盾时不得用推测补足。对没有证据的结论可以保留未知；不得虚构发生过的事件。没有要求统计整局全部事件。
