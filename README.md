# 中篇小说自动创作管线

分层生成 + 状态管理：
**Spec → [imagine 候选发散+挑选] → 故事设定 → 人物设定 → 章节大纲（伏笔+弧光登记）→ 逐章循环（生成→审校→状态回写）→ 终稿装配**

## imagine 模块：我出候选，你来挑

**前置规程**：`docs/imagine-research-design.md` 是 imagine 的强制输入——先调研市面同类型爆款（榜单/口碑/讨论/网文数据四路）、解析成功要素、找出机会缺口并经你确认，然后每个候选锚定缺口、附市场依据（对标作品/借用要素/创新点）。调研由助手会话按规程执行；脚本自由发散仅为显式降级通道，需加 `--no-research` 且候选强制标注「未经市场调研」。

```bash
python3 run.py --name my_novel --spec "悬疑，海边小镇，别的你发挥" --imagine --no-research  # 显式降级
```

- 发散 **3 个差异化故事候选**（premise/矛盾类型/结局落点实质不同，拒绝换皮），写入 `imagine/story_candidates.md`，终端列出一句话卖点，你输编号挑选
- 针对选中故事发散 **2 套气质迥异的人物阵容候选**（主角底色/对手类型/关系结构不同），写入 `imagine/cast_candidates.md`，同样编号挑选
- 选中者直接落为正式管线的故事/人物设定，后续确认门照常——不满意仍可输修改意见微调
- `--imagine-only` 选完即停；`--story-candidates 5 --cast-candidates 3` 可调候选数量
- 候选与选择全部落盘，中断重跑不重复发散；已确认的设定自动跳过对应候选环节

## 快速开始

```bash
pip3 install -r requirements.txt
cp .env.example .env   # 填入 LLM_BASE_URL / LLM_API_KEY / LLM_MODEL（OpenAI 兼容接口）

python3 run.py --name my_novel --total-words 50000 \
  --spec "题材：悬疑；背景：南方小镇；视角：第三人称限知；基调：冷峻克制；禁忌：不写超自然"
```

`--spec` 也可以传一个 .txt/.md 文件路径。

## 五阶段与四处人工确认门

| 阶段 | 产物 | 内容 | 确认门 |
|---|---|---|---|
| 1 故事设定 | `settings/story.md` | 类型定位、一句话故事、核心前提、主题与主题意象、文风视角、时空背景（年代/地点/社会/氛围）、世界硬规则、内外核心矛盾及绞合、结局走向、伏笔线索、写作禁忌 | ✔ |
| 2 人物设定 | `settings/characters.md` | 每人深卡：小传、外貌标志、want/need、恐惧、内在谎言、秘密、缺陷、口吻、人物弧光（起点→转变→终点）、主线功能；主角/对手含心理侧写；两两关系网（表面关系+暗层张力） | ✔ |
| 3 章节大纲 | `outline/outline.md` | 三幕结构、逐章目标/冲突/事件/人物/基调/字数预算、**伏笔登记表**（埋设→回收）、**人物弧光落章表** | ✔ |
| 4 章节循环 | `chapters/chNN.md` | 自动：深卡+关系张力+摘要切片注入 → 生成 → 审校（最多重写 N 轮）→ 回写人物状态/时间线/伏笔进展 | 自动 |
| 5 终稿装配 | `final/书名.md/.txt`、`final/report.md` | 伏笔回收核对、弧光完整性、结局呼应检查 | ✔ |

确认门操作：终端输入 `y` 通过；输入其他文字视为修改意见，自动带意见重生成，直到你满意。

## 结构校验（不靠模型自觉）

- 人物：3~6 人、必有主角、深卡必填字段齐全、弧光必有转变节点、关系网人物必须已登记
- 大纲：伏笔回收章晚于埋设章且存在；每位有弧光的人物其 turn 节点必须落到具体章节
- 终稿：伏笔回收记录逐条核对，缺失即写入报告

## 作品目录结构

```
output/<name>/
├── state.json                  # 唯一状态源（设定/大纲/摘要/进度，勿手改）
├── imagine/                    # 候选发散
│   ├── story_candidates.md     #   故事候选清单
│   └── cast_candidates.md      #   人物阵容候选清单
├── settings/                   # 已确认设定
│   ├── story.md                #   故事设定
│   └── characters.md           #   人物深卡与关系网
├── outline/
│   └── outline.md              # 三幕大纲 + 伏笔登记表 + 弧光落章表
├── chapters/
│   └── ch01.md …               # 分章稿
└── final/
    ├── 书名.md / 书名.txt       # 成品全文
    └── report.md               # 终稿检查报告
```

旧版平铺布局（`01_story.md` 等编号文件散在根目录）在续跑时自动迁移到上述结构，进度不丢。

## 断点续跑

状态全部落盘在 `output/<name>/state.json`。中断后：

```bash
python3 run.py --name my_novel                    # spec 已保存，可省略
python3 run.py --name my_novel --stage characters # 只跑到某阶段
```

已确认的设定/大纲、已完成的章节自动跳过。已有章节进度时不允许更换 spec。

## 无 API 验证

```bash
python3 run.py --name smoke --dry-run
```

桩数据走通全流程（四道确认门、人物/伏笔/弧光校验、装配、续跑），不消耗 token。

## 配置项（.env）

| 变量 | 说明 |
|---|---|
| LLM_BASE_URL / LLM_API_KEY / LLM_MODEL | OpenAI 兼容接口 |
| LLM_REVIEW_MODEL | 审校模型（可选，建议更强模型；不填复用主模型） |
| CHAPTER_WORDS | 单章目标字数，默认 3000（决定章节数） |
| MAX_REVISE_ROUNDS | 单章最大重写轮数，默认 2 |