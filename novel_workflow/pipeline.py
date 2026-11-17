"""管线各阶段：spec → 故事设定 → 人物设定 → 大纲 → 章节循环 → 装配导出。"""
import json

from . import config, prompts
from .llm import chat, chat_json
from .state import NovelState


def _dump(obj):
    return json.dumps(obj, ensure_ascii=False, indent=2)


def _confirm_gate(state, key, artifact_path, render):
    """人工确认门：渲染产物到文件，等待终端确认；拒绝则收集修改意见重生成。"""
    path = artifact_path
    while True:
        path.write_text(render(), encoding="utf-8")
        print(f"\n=== 待确认：{path.name}（已写入 {path}）===")
        ans = input("确认通过？[y] 通过 / [其他] 输入修改意见后重生成：").strip()
        if ans.lower() in ("y", "yes", ""):
            state.data["confirmed"][key] = True
            state.save()
            return
        state.data[key] = _regenerate_with_feedback(state, key, ans)
        state.save()


def _regenerate_with_feedback(state, key, feedback):
    tail = f"\n\n上一版：\n{_dump(state.data[key])}\n\n人工修改意见（必须落实）：{feedback}"
    if key == "story":
        return chat_json(prompts.STORY_SYSTEM, prompts.STORY_USER.format(spec=state.data["spec"]) + tail)
    if key == "characters":
        return chat_json(prompts.CHARACTER_SYSTEM, _characters_user(state) + tail)
    if key == "outline":
        return chat_json(prompts.OUTLINE_SYSTEM, _outline_user(state) + tail)
    raise ValueError(key)


# ---------- 渲染 ----------
def _render_story(state):
    return render_story(state.data["story"])


def render_story(s):
    st, cf = s["setting"], s["conflicts"]
    lines = [f"# 故事设定：{s['title']}",
             f"\n- 类型定位：{s['genre']}\n- 一句话故事：{s['logline']}\n- 核心前提：{s['premise']}",
             f"\n## 主题\n- {s['theme']}\n- 主题意象：{s['theme_motif']}",
             f"\n## 文风\n{s['style']}",
             f"\n## 时空背景\n- 时间：{st['time']}\n- 地点：{st['place']}\n- 社会环境：{st['society']}\n- 氛围：{st['atmosphere']}",
             "\n## 世界硬规则"] + [f"- {r}" for r in s["world_rules"]]
    lines += [f"\n## 核心矛盾\n- 外部：{cf['external']}\n- 内部：{cf['internal']}\n- 绞合：{cf['interlock']}",
              f"\n## 结局走向\n{s['ending_direction']}", "\n## 伏笔线索"]
    lines += [f"- {h}" for h in s["seed_hooks"]]
    lines.append("\n## 写作禁忌")
    lines += [f"- {t}" for t in s["taboos"]]
    return "\n".join(lines)


def _render_characters(state):
    return render_characters(state.data["characters"])


def render_characters(data):
    lines = ["# 人物设定"]
    for c in data["characters"]:
        arc = c.get("arc", {})
        lines.append(f"\n## {c['name']}（{c['role']}，{c.get('age', '')}）")
        lines.append(f"- 职业处境：{c.get('occupation', '')}\n- 外貌标志：{c.get('appearance', '')}")
        lines.append(f"\n**小传**：{c.get('backstory', '')}")
        lines.append(f"\n- 外在目标 want：{c.get('want', '')}\n- 内在需求 need：{c.get('need', '')}")
        lines.append(f"- 恐惧：{c.get('fear', '')}\n- 内在谎言：{c.get('lie', '')}\n- 秘密：{c.get('secret', '')}")
        lines.append(f"- 缺陷：{c.get('flaw', '')}\n- 口吻：{c.get('voice', '')}")
        lines.append(f"\n**弧光**：{arc.get('start', '')} → 转变（{arc.get('turn', '')}）→ {arc.get('end', '')}")
        if c.get("psych_profile"):
            lines.append(f"\n**心理侧写**：{c['psych_profile']}")
        lines.append(f"\n**主线功能**：{c.get('plot_function', '')}")
    lines.append("\n## 关系网")
    for r in data.get("relationship_web", []):
        lines.append(f"- **{r['pair']}**：表面「{r['surface']}」／暗层「{r['tension']}」")
    return "\n".join(lines)


def _render_outline(state):
    o = state.data["outline"]
    lines = ["# 章节大纲"]
    for a in o["acts"]:
        lines.append(f"\n## 第{a['act']}幕 {a['name']}（第{a['chapters'][0]}~{a['chapters'][-1]}章）")
        for ch in o["chapters"]:
            if ch["act"] == a["act"]:
                lines.append(f"\n### 第{ch['no']}章 {ch['title']}（约{ch['word_budget']}字）\n"
                             f"- 目标：{ch['goal']}\n- 冲突：{ch['conflict']}\n"
                             f"- 事件：{'；'.join(ch['events'])}\n"
                             f"- 人物：{'、'.join(ch['characters'])}｜基调：{ch['mood']}")
    lines.append("\n## 人物弧光落章表")
    for b in o.get("arc_beats", []):
        lines.append(f"- {b['name']}·{b['beat']} → 第{b['chapter']}章：{b['desc']}")
    lines.append("\n## 伏笔登记表")
    for f in o["foreshadows"]:
        lines.append(f"- {f['id']}：{f['content']}（埋设第{f['plant_chapter']}章 → 回收第{f['payoff_chapter']}章）")
    return "\n".join(lines)


# ---------- 各阶段 ----------
def _characters_user(state):
    return prompts.CHARACTER_USER.format(spec=state.data["spec"], story=_dump(state.data["story"]))


def _outline_user(state):
    total = state.data.get("total_words", 50000)
    return prompts.OUTLINE_USER.format(spec=state.data["spec"], story=_dump(state.data["story"]),
                                       characters=_dump(state.data["characters"]),
                                       total_words=total, chapter_words=config.CHAPTER_WORDS)


def stage_story(state):
    if state.data["confirmed"]["story"]:
        print("故事设定已确认，跳过。")
        return
    if state.data["story"] is None:
        print("[1/5] 生成故事设定…")
        state.data["story"] = chat_json(prompts.STORY_SYSTEM, prompts.STORY_USER.format(spec=state.data["spec"]))
        state.save()
    _confirm_gate(state, "story", state.settings_dir / "story.md", lambda: _render_story(state))


def stage_characters(state):
    if state.data["confirmed"]["characters"]:
        print("人物设定已确认，跳过。")
        return
    if state.data["characters"] is None:
        print("[2/5] 生成人物设定…")
        state.data["characters"] = chat_json(prompts.CHARACTER_SYSTEM, _characters_user(state))
        state.save()
    _validate_characters(state)
    _confirm_gate(state, "characters", state.settings_dir / "characters.md", lambda: _render_characters(state))


def _validate_characters(state):
    chars = state.data["characters"]["characters"]
    assert 3 <= len(chars) <= 6, "主要人物数量应在 3~6 之间"
    names = {c["name"] for c in chars}
    assert any(c["role"] == "主角" for c in chars), "缺少主角"
    for c in chars:
        for field in ("want", "need", "fear", "lie", "voice", "backstory"):
            assert c.get(field), f"人物 {c['name']} 缺少 {field}"
        assert c.get("arc", {}).get("turn"), f"人物 {c['name']} 弧光缺少转变节点"
    for r in state.data["characters"].get("relationship_web", []):
        for n in r["pair"].replace("×", "x").split("x"):
            assert n.strip() in names, f"关系网出现未登记人物：{n}"


def stage_outline(state):
    if state.data["confirmed"]["outline"]:
        print("大纲已确认，跳过。")
        return
    if state.data["outline"] is None:
        print("[3/5] 生成章节大纲…")
        state.data["outline"] = chat_json(prompts.OUTLINE_SYSTEM, _outline_user(state))
        state.save()
    _validate_outline(state)
    _confirm_gate(state, "outline", state.outline_dir / "outline.md", lambda: _render_outline(state))


def _validate_outline(state):
    o = state.data["outline"]
    nos = {c["no"] for c in o["chapters"]}
    names = {c["name"] for c in state.data["characters"]["characters"]}
    for f in o["foreshadows"]:
        assert f["payoff_chapter"] > f["plant_chapter"], f"伏笔 {f['id']} 回收章不晚于埋设章"
        assert f["plant_chapter"] in nos and f["payoff_chapter"] in nos, f"伏笔 {f['id']} 指向不存在的章节"
    for b in o.get("arc_beats", []):
        assert b["chapter"] in nos, f"弧光节点 {b['name']}·{b['beat']} 指向不存在的章节"
        assert b["name"] in names, f"弧光节点出现未登记人物：{b['name']}"
    for c in state.data["characters"]["characters"]:
        if c.get("arc", {}).get("turn"):
            assert any(b["name"] == c["name"] and b["beat"] == "turn" for b in o.get("arc_beats", [])), \
                f"人物 {c['name']} 的弧光转变未落章"


def _write_chapter_once(state, ch, revision_note=""):
    s = state.data["story"]
    user = prompts.CHAPTER_USER.format(
        title=s["title"], no=ch["no"], chapter_title=ch["title"], style=s["style"],
        setting_brief=state.setting_brief(),
        rules="\n".join(f"- {r}" for r in s["world_rules"]),
        characters=state.relevant_characters(ch), relations=state.relevant_relations(ch),
        summary=state.data["summary"]["global_summary"] + "\n近章详摘：" + state.data["summary"]["recent_detail"],
        previous_tail=state.previous_tail(ch["no"]),
        chapter_outline=_dump(ch), arc_tasks=state.arc_tasks(ch["no"]),
        foreshadow_tasks=state.foreshadow_tasks(ch["no"]),
        theme_motif=s["theme_motif"],
        taboos="\n".join(f"- {t}" for t in s["taboos"]),
        word_budget=ch["word_budget"], revision_note=revision_note)
    return chat(prompts.CHAPTER_SYSTEM, user, max_tokens=8192)


def stage_chapters(state):
    print("[4/5] 章节循环…")
    for ch in state.data["outline"]["chapters"]:
        no = ch["no"]
        if no in state.data["chapters_done"]:
            print(f"  第{no}章已完成，跳过。")
            continue
        print(f"  第{no}章《{ch['title']}》生成中…")
        draft = _write_chapter_once(state, ch)
        for round_no in range(config.MAX_REVISE_ROUNDS + 1):
            review = _review_chapter(state, ch, draft)
            if review.get("pass", True):
                break
            if round_no == config.MAX_REVISE_ROUNDS:
                print(f"    第{no}章达到最大重写次数，保留当前稿并标记待人工复核。")
                state.data.setdefault("needs_human_review", []).append(no)
                break
            issues = "\n".join(f"- [{i['severity']}] {i['desc']} → {i['fix']}" for i in review.get("issues", []))
            print(f"    审校未过（第{round_no + 1}轮重写）：{len(review.get('issues', []))} 个问题")
            draft = _write_chapter_once(state, ch, revision_note=f"\n【责任编辑修改指令（必须全部落实）】\n{issues}")
        state.write_chapter(no, ch["title"], draft)
        print(f"    更新剧情状态…")
        update = chat_json(prompts.SUMMARY_SYSTEM, prompts.SUMMARY_USER.format(
            old_summary=state.data["summary"]["global_summary"], no=no, chapter_text=draft))
        state.apply_summary_update(no, update)
    state.save()


def _review_chapter(state, ch, draft):
    s = state.data["story"]
    return chat_json(prompts.REVIEW_SYSTEM, prompts.REVIEW_USER.format(
        characters=state.relevant_characters(ch), relations=state.relevant_relations(ch),
        rules="\n".join(s["world_rules"]),
        summary=state.data["summary"]["global_summary"], chapter_outline=_dump(ch),
        arc_tasks=state.arc_tasks(ch["no"]), foreshadow_tasks=state.foreshadow_tasks(ch["no"]),
        draft=draft, word_budget=ch["word_budget"]), model=config.REVIEW_MODEL, temperature=0.2)


def stage_assemble(state):
    print("[5/5] 终稿装配…")
    outline = state.data["outline"]
    s = state.data["story"]
    parts = [f"# {s['title']}\n\n> {s['theme']}\n"]
    digests = []
    for ch in outline["chapters"]:
        text = state.read_chapter(ch["no"])
        parts.append(text)
        paras = [p for p in text.split("\n\n") if p.strip()]
        digests.append(f"第{ch['no']}章 {ch['title']}：开头「{paras[1][:80] if len(paras) > 1 else ''}…」"
                       f"结尾「{paras[-1][-80:]}…」")
    check = chat_json(prompts.ASSEMBLY_CHECK_SYSTEM, prompts.ASSEMBLY_CHECK_USER.format(
        foreshadows=_dump({"登记表": outline["foreshadows"], "进展": state.data["foreshadow_log"]}),
        arc_beats=_dump({"落章表": outline.get("arc_beats", []), "人物状态": state.data["character_state"]}),
        ending_direction=s["ending_direction"],
        summary=state.data["summary"]["global_summary"], chapter_digests="\n".join(digests)),
        model=config.REVIEW_MODEL, temperature=0.2)
    problems = state.unrecycled_foreshadows() + check.get("issues", [])
    report = ["# 终稿检查报告", f"\n结论：{check.get('verdict', '未知')}"]
    report += [f"- {p}" for p in problems] if problems else ["- 未发现结构性问题"]
    if state.data.get("needs_human_review"):
        report.append(f"- 待人工复核章节：{state.data['needs_human_review']}")
    (state.final_dir / "report.md").write_text("\n".join(report), encoding="utf-8")
    full = "\n\n---\n\n".join(parts)
    (state.final_dir / f"{s['title']}.md").write_text(full, encoding="utf-8")
    (state.final_dir / f"{s['title']}.txt").write_text(
        full.replace("# ", "").replace("> ", "").replace("\n---\n", "\n"), encoding="utf-8")
    print("\n".join(report))
    print(f"\n=== 待确认：终稿（{state.dir}）===")
    ans = input("确认交付？[y] 完成 / [其他] 保留现场退出，之后可修改并续跑：").strip()
    if ans.lower() in ("y", "yes", ""):
        state.data["confirmed"]["final"] = True
        state.save()
        print(f"完成。成品：{state.final_dir / (s['title'] + '.md')}")
    else:
        print("已保留全部现场，修改后可用相同 --name 续跑。")