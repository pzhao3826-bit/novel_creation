# imagine 前置规程：调研驱动创意生成（执行指令）

> 本文件是 imagine 环节的**强制输入**。执行者（助手或管线）在生成任何故事/人物候选之前，必须先完整执行本规程 R0→R3，并让 R4/R5 受 R3 产物约束。
> 铁律：**没有调研支撑的创意不允许进入候选清单。** 跳过调研必须获得用户显式同意，且候选文件头部标注「未经市场调研」。

## 执行流程

```
spec → R0 检索规划 → R1 市场采集 → R2 爆款解析 → R3 市场报告(用户确认)
     → R4 故事候选(锚定缺口) → 用户挑选 → R5 阵容候选 → 用户挑选 → 正式管线
```

所有产物写入 `output/<name>/imagine/research/`，过程状态记入 `state.json` 的 `imagine.research` 段。已完成的步骤重入时跳过；R3 报告变更后，已生成的候选作废重发散。

## R0 检索规划

依据 spec 生成 `research_plan.json`，要求：

- 检索意图必须覆盖四路：**榜单（卖得好）／口碑（评分高）／讨论（声量大）／网文数据（追读强）**。四路交集才是真爆款，单路命中只算候选信号。至少覆盖三路。
- 平台面向：豆瓣读书、起点/番茄榜单、微信读书、小红书/知乎讨论；按题材酌情增删。
- 时间窗默认近 12 个月；主题材之外加 1~2 个相邻可借鉴题材轴。
- 每路至少 2 条具体检索词，写入 `queries: [{intent, query}]`。
- 有效信源下限 `min_sources = 8`。

## R1 市场采集

- 逐条执行检索（助手会话用可用的 web 搜索工具；管线用配置的搜索 API），结果落盘 `sources.json`：
  `{id, source_url, title, snippet, date, intent, fetched_at}`
- 高价值页面（榜单页、长书评）抓取全文补充 snippet。
- 信源分级：官方榜单 > 平台数据 > 媒体书评 > 社区讨论。同一作品多源合并，保留全部出处。
- **只增不改**：补查追加条目，不覆盖旧素材，保证可追溯。
- 有效信源 < 8 或意图覆盖 < 3 路时：换关键词扩查（最多 2 轮），仍不足则如实告知用户素材缺口，不得伪装调研完成。
- 外部素材可经用户提供的文件导入，格式同上，标注 `origin: "imported"`。
- 每轮补查在 `research_log.md` 记一行：时间、意图、新增条数。

## R2 爆款解析

从素材中选出证据最强的 8~12 部作品，逐部生成成功要素卡，写入 `hit_cards.json` 并渲染可读版 `hit_cards.md`：

```json
{
  "title": "作品名", "author": "作者", "year": "年份",
  "evidence": ["sources.json 中的条目 id，非空"],
  "heat_signals": {"榜单": "…", "口碑": "…", "讨论": "…"},
  "hook": "开篇钩子：前3章抓住读者的机制",
  "premise_type": "前提类型",
  "protagonist_archetype": "主角原型与反差感",
  "structure": "结构特征",
  "emotional_value": "核心情绪价值（爽/虐/治愈/智性快感…）",
  "spread_point": "读者愿意安利的传播点",
  "saturation_risk": "该套路是否已泛滥及依据"
}
```

约束：evidence 必须指向真实素材条目；作品信息以素材为准，素材不足以支撑的字段写"存疑"，禁止用先验知识补写成事实。

## R3 市场报告（用户确认门）

综合要素卡产出 `market_report.md` + 结构化镜像 `market_report.json`：

1. **热门要素矩阵**：钩子×人设×结构×情绪价值的共现统计，标出被反复验证的组合
2. **饱和套路清单**：已泛滥、必须避开或反转的桥段，每条附作品证据
3. **机会缺口**（核心产出，≥3 个）：缺口 = 已验证的需求 + 未被满足的角度

```json
{
  "validated_elements": ["要素及证据"],
  "saturated_tropes": ["套路及证据"],
  "opportunity_gaps": [
    {"id": "G1", "validated_need": "已验证需求", "unmet_angle": "空缺角度", "evidence": ["要素卡/素材引用"]}
  ],
  "risks": ["题材红线、审美疲劳周期"]
}
```

全部结论必须引用要素卡或素材，禁止无据断言。

确认门：向用户展示报告路径与缺口摘要。用户认可 → 记 `confirmed_report: true`；用户质疑/要求补查 → 回 R1 追加采集或重写 R3，循环直到确认。

## R4 故事候选（约束发散）

生成 N 个候选（默认 3），每个候选：

- **必须锚定一个机会缺口**，声明对标爆款与借用的已验证要素
- **禁止**直接使用饱和套路，除非写出明确反转方式
- 候选间在核心前提/主角处境/矛盾类型/结局落点上实质差异化，至少一个偏离俗套
- 输出完整故事设定结构（title/genre/logline/premise/theme/theme_motif/style/setting/world_rules/conflicts/ending_direction/seed_hooks/taboos），并附：

```json
"market_rationale": {
  "gap_id": "G1",
  "benchmarks": ["对标爆款，必须出现在 hit_cards 中"],
  "borrowed_elements": ["借用的已验证要素"],
  "innovation": "在缺口上的具体创新",
  "trope_avoidance": "避开/反转了哪些饱和套路"
}
```

发散前自检：`gap_id` 存在于 market_report；`benchmarks` 存在于 hit_cards；饱和套路未裸用。不通过就重新生成，不得放行。

渲染 `imagine/story_candidates.md`：每候选头部展示推荐语 + 市场依据摘要（锚定缺口、对标、创新点），再列完整设定。终端列编号与一句话卖点，用户输编号挑选，选中者写入 `state.story` 进入正式管线确认门。

## R5 人物阵容候选

针对选中故事发散 M 套阵容（默认 2），沿用完整深卡结构（want/need/fear/lie/secret/arc/psych_profile/relationship_web）。

- 参考 market_report 中的主角原型偏好，但不做枷锁：允许一套阵容故意反市场差异化，须在 pitch 中声明理由
- 各套在主角底色/对手类型/关系结构上实质不同
- 渲染 `imagine/cast_candidates.md`，用户挑选后写入 `state.characters`

## 降级通道（仅用户显式选择时）

无检索通道且用户不愿提供素材时，经用户明确同意方可降级为自由发散：

- 候选文件头部第一行强制写入：`> ⚠ 未经市场调研，以下候选无市场依据`
- `state.imagine.research` 记 `skipped: true, reason`
- 其余发散质量要求（差异化、完整深卡）不放松

## 自检清单（每次 imagine 收尾前逐项核对）

- [ ] 有效信源 ≥ 8，意图覆盖 ≥ 3 路（或已如实报告缺口/显式降级）
- [ ] 每张要素卡 evidence 指向真实素材
- [ ] 机会缺口 ≥ 3 且各有证据；报告已获用户确认
- [ ] 每个故事候选 gap_id/benchmarks 可回溯，饱和套路未裸用
- [ ] 候选/选择均落盘，state.json 与实际文件一致