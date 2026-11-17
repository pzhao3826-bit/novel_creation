# imagine 模块扩展设计：调研驱动的创意生成（Research-Driven Ideation）

> 状态：设计定稿，待实现
> 原则：**先调研市面爆款 → 解析成功要素 → 识别机会缺口 → 带约束发散候选 → 人工挑选**。
> 没有调研支撑的创意不允许进入候选清单。

## 1. 为什么要扩展

现有 imagine 直接从 spec 发散故事/人物候选，本质是模型的先验采样：

- 不知道当下读者在为什么买单，候选可能撞车已泛滥的套路，也可能踩中已过气的题材
- "差异化"只在候选之间成立，没有对**市场存量**做差异化
- 无法解释"为什么是这个创意"——缺少可追溯的决策依据

扩展后，每个候选必须携带**市场依据**（对标哪些爆款、借用什么已验证要素、在哪个缺口上做创新），创意从"灵感"变成"有论据的假设"。

## 2. 新流水线全景

```
spec（题材方向）
  │
  ▼
[R0] 调研规划     根据 spec 生成检索计划（关键词组、平台清单、时间窗）
  │
  ▼
[R1] 市场采集     多路检索：榜单/书评/讨论/完结数据 → 原始素材库（带来源）
  │
  ▼
[R2] 爆款解析     逐部提取成功要素卡：钩子/人设/结构/情绪价值/传播点
  │
  ▼
[R3] 趋势综合     汇总为市场报告：热门要素矩阵、饱和套路清单、机会缺口
  │        ←—— 人工确认门（市场报告可质疑、可要求补查）
  ▼
[R4] 约束发散     以「机会缺口 + 已验证要素 + spec」为约束生成故事候选
  │                每候选附 market_rationale（对标/借用/创新点）
  │        ←—— 人工挑选（原有交互不变）
  ▼
[R5] 阵容发散     针对选中故事发散人物阵容候选（沿用现有逻辑，
  │                增加"对标爆款读者偏好的人设气质"作为参考输入）
  │        ←—— 人工挑选
  ▼
正式管线（故事设定确认门 → 人物设定确认门 → 大纲 → 章节 → 装配）
```

## 3. 各阶段详细设计

### R0 调研规划（planner）

输入：spec、时间窗（默认近 12 个月）、目标市场（默认中文网文+出版中篇）。
输出 `research_plan.json`：

```json
{
  "genre_axes": ["主题材", "相邻可借鉴题材"],
  "queries": [
    {"intent": "榜单", "query": "2026 悬疑小说 畅销榜", "engine": "web_search"},
    {"intent": "口碑", "query": "豆瓣 悬疑小说 高分 2025 2026", "engine": "web_search"},
    {"intent": "讨论", "query": "小红书 悬疑小说 推荐 爆火", "engine": "web_search"},
    {"intent": "网文", "query": "起点 番茄 悬疑 月票榜 完本", "engine": "web_search"}
  ],
  "platforms": ["豆瓣读书", "起点/番茄榜单", "微信读书", "小红书/知乎讨论"],
  "time_window": "近12个月",
  "min_sources": 8
}
```

要点：
- 检索意图分四路：**榜单（卖得好）/ 口碑（评分高）/ 讨论（声量大）/ 网文数据（追读强）**，四路交集才是真爆款，单路只能算候选信号
- 关键词由 LLM 依据 spec 生成，人工可在确认门补充

### R1 市场采集（collector）

- 执行检索计划，每条结果落盘为素材条目：`{source_url, title, snippet, date, intent, fetched_at}`
- 对高价值页面（榜单页、长书评）做全文抓取
- **去重与信源分级**：官方榜单 > 平台数据 > 媒体书评 > 社区讨论；同一作品多源合并
- 产出：`imagine/research/sources.json`（原始素材，只增不改，保证可追溯）
- 硬性下限：有效信源 < `min_sources` 时报警并要求扩查，不允许拿 3 条搜索结果就装作调研过

### R2 爆款解析（analyzer）

对采集到的 Top N（默认 8~12）部作品，逐部生成**成功要素卡**：

```json
{
  "title": "作品名", "author": "作者", "year": "年份",
  "evidence": ["支撑其'爆款'判定的信源引用"],
  "heat_signals": {"榜单": "...", "口碑": "...", "讨论": "..."},
  "hook": "开篇钩子（前3章抓住读者的机制）",
  "premise_type": "前提类型（如：熟人社会+旧案重启）",
  "protagonist_archetype": "主角原型与反差感",
  "structure": "结构特征（双线/倒计时/不可靠叙述…）",
  "emotional_value": "给读者的核心情绪价值（爽/虐/治愈/智性快感…）",
  "spread_point": "传播点（为什么读者愿意安利）",
  "saturation_risk": "该作代表的套路是否已泛滥"
}
```

产出：`imagine/research/hit_cards.json` + 可读版 `hit_cards.md`。

### R3 趋势综合（synthesizer）→ 人工确认门

汇总所有要素卡，产出**市场报告** `imagine/research/market_report.md`：

1. **热门要素矩阵**：钩子×人设×结构×情绪价值的共现统计，哪些组合被反复验证
2. **饱和套路清单**：已泛滥、新作必须避开或反转的桥段（附作品证据）
3. **机会缺口**（核心产出，3~5 个）：每个缺口 = 「已验证的需求 + 未被满足的角度」，例如"读者要智性快感（已验证），但市面全是警察视角，法医家属视角空缺"
4. **风险提示**：题材政策红线、审美疲劳周期
5. 全部结论必须引用要素卡/信源，禁止无据断言

确认门交互（与现有门一致）：`y` 通过；输入文字 = 质疑或补查指令 → 带着意见回到 R1 补充采集或 R3 重新综合。

结构化镜像 `market_report.json`（供 R4 程序化注入）：

```json
{
  "validated_elements": ["要素及证据"],
  "saturated_tropes": ["套路及证据"],
  "opportunity_gaps": [
    {"id": "G1", "validated_need": "已验证需求", "unmet_angle": "空缺角度", "evidence": ["..."]}
  ],
  "risks": ["..."]
}
```

### R4 约束发散（constrained ideation）

替换现有 `IMAGINE_STORY_USER` 的自由发散，新约束：

- 每个候选**必须锚定一个机会缺口 G_i**，并声明借用哪些已验证要素
- **禁止**直接使用饱和套路清单中的桥段，除非做明确反转（反转方式须写出）
- 候选间差异化要求保留（premise/主角处境/矛盾类型/结局落点）
- 每候选新增字段：

```json
"market_rationale": {
  "gap_id": "G1",
  "benchmarks": ["对标的爆款作品"],
  "borrowed_elements": ["借用的已验证要素"],
  "innovation": "在缺口上的具体创新",
  "trope_avoidance": "避开/反转了哪些饱和套路"
}
```

- 候选清单渲染时，每个候选头部展示推荐语 + 市场依据摘要，让人工挑选时能看到"为什么"
- 校验器：`gap_id` 必须存在于 market_report；`benchmarks` 必须出现在要素卡中——防止模型编造对标

### R5 阵容发散

沿用现有逻辑，注入市场报告中的 `protagonist_archetype` 偏好作为参考（参考而非枷锁：允许一套阵容故意反市场做差异化，但须声明理由）。

## 4. 目录结构增量

```
output/<name>/
├── imagine/
│   ├── research/                    # 新增：调研区
│   │   ├── research_plan.json       #   R0 检索计划
│   │   ├── sources.json             #   R1 原始素材（只增不改）
│   │   ├── hit_cards.json / .md     #   R2 成功要素卡
│   │   ├── market_report.json / .md #   R3 市场报告（确认门产物）
│   │   └── research_log.md          #   各轮补查记录
│   ├── story_candidates.md          #   R4 候选（含市场依据）
│   └── cast_candidates.md           #   R5 阵容候选
└── state.json                       # imagine 段新增 research 子状态
```

state.json 增量：

```json
"imagine": {
  "research": {
    "plan": {}, "sources_count": 0,
    "hit_cards": [], "market_report": {},
    "confirmed_report": false, "rounds": []
  },
  "story_candidates": [], "story_choice": null,
  "cast_candidates": [], "cast_choice": null
}
```

## 5. 检索实现与降级策略

| 环境 | 检索通道 | 说明 |
|---|---|---|
| 默认 | 搜索 API（OpenAI 兼容服务方的 web_search 工具，或独立搜索 API，`.env` 配 `SEARCH_API_*`） | 管线自动执行 R1 |
| 宿主助手会话 | 由助手（QwenWork）执行检索，把结果写入 `sources.json` 后管线从 R2 续跑 | `--research-import <file>` 导入 |
| 无任何检索通道 | **不允许静默跳过调研**。二选一：人工提供素材文件导入；或显式 `--no-research` 降级为旧版自由发散，且候选文件头部强制标注"未经市场调研" | 降级必须显式、留痕 |

## 6. CLI 增量

```bash
# 完整调研驱动流程
python3 run.py --name my_novel --spec "悬疑，海边小镇" --imagine

# 控制调研深度
--research-top-n 10        # 解析爆款数量（默认8）
--research-window 12m      # 时间窗
--research-import f.json   # 导入外部采集素材，跳过 R1
--no-research              # 显式降级（候选标注未调研）

# 只跑调研，报告确认后停下
--stage research
```

断点语义：R1 素材只增不改；报告未确认可反复补查；报告确认后重跑不重复检索；候选发散在报告变更后自动失效重生成。

## 7. 质量红线（校验器强制）

1. 有效信源 ≥ min_sources，四路意图至少覆盖三路
2. 每张要素卡的 evidence 非空且指向 sources 中的真实条目
3. 市场报告的机会缺口 ≥ 3 个，每个缺口有 evidence
4. 每个故事候选的 gap_id / benchmarks 可回溯校验
5. 未经调研的候选必须带显式标注
6. dry-run 桩数据覆盖 R0~R4 全链路与上述校验

## 8. 实施拆分（后续自动化跑）

- [ ] M1：`research.py`（R0 规划 + R1 采集 + 导入/降级通道）+ state 增量
- [ ] M2：R2 要素卡 + R3 市场报告 + 确认门 + 校验器
- [ ] M3：R4 约束发散改造（prompts + market_rationale 校验 + 渲染）
- [ ] M4：CLI 接线 + dry-run 全链路桩 + README 更新