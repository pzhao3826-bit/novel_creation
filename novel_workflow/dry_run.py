"""无 API 干跑：用桩数据替换 LLM 调用，验证管线结构、状态流转与断点逻辑。"""
import builtins


def _stub_story():
    return {
        "title": "测试之书", "genre": "社会派悬疑", "logline": "旧友追查小镇沉案",
        "premise": "甲想查明真相，被乙与小镇沉默阻挡，赌注是自我认同",
        "theme": "真相的代价", "theme_motif": "退潮后露出的旧船骸",
        "style": "第三人称限知，冷峻",
        "setting": {"time": "九十年代末，跨度一个月", "place": "南方海边小镇",
                    "society": "熟人社会，沉默共谋", "atmosphere": "潮湿、压抑"},
        "world_rules": ["死人不会复活", "无超自然"],
        "conflicts": {"external": "甲与乙的掩盖对抗", "internal": "甲对旧友的信任与怀疑",
                      "interlock": "每逼近真相一分，就要背叛旧情一分"},
        "ending_direction": "真相揭开但代价永存，落点苦涩微光",
        "seed_hooks": ["旧照片", "缺页日记"], "taboos": ["不写超自然"],
    }


def _stub_characters():
    def card(name, role, psych):
        return {"name": name, "age": "35", "role": role, "occupation": "镇民",
                "appearance": f"{name}的标志细节", "backstory": f"{name}的关键过往",
                "want": "外在目标", "need": "内在需求", "fear": "恐惧", "lie": "错误信念",
                "secret": "秘密", "flaw": "缺陷", "voice": "口吻",
                "arc": {"start": "起点", "turn": "逼迫转变的事件", "end": "终点"},
                "psych_profile": psych, "plot_function": "与主线冲突咬合"}
    return {
        "characters": [card("甲", "主角", "多疑而重情"), card("乙", "对手", "自负且恐惧暴露"),
                       card("丙", "关键配角", "")],
        "relationship_web": [
            {"pair": "甲×乙", "surface": "旧友", "tension": "隐瞒与试探"},
            {"pair": "甲×丙", "surface": "邻里", "tension": "丙知情不言"},
        ],
    }


def _stub_outline():
    return {
        "acts": [{"act": 1, "name": "起", "chapters": [1, 2]}, {"act": 2, "name": "承转", "chapters": [3]}],
        "chapters": [
            {"no": i, "title": f"章{i}", "act": 1 if i < 3 else 2, "goal": "推进", "conflict": "冲突",
             "events": ["事件"], "characters": ["甲", "乙", "丙"], "mood": "紧张", "word_budget": 3000}
            for i in (1, 2, 3)
        ],
        "arc_beats": [
            {"name": "甲", "beat": "turn", "chapter": 2, "desc": "发现乙的谎言"},
            {"name": "乙", "beat": "turn", "chapter": 3, "desc": "掩盖崩塌"},
            {"name": "丙", "beat": "turn", "chapter": 2, "desc": "被迫开口"},
        ],
        "foreshadows": [{"id": "F1", "content": "旧照片", "plant_chapter": 1, "payoff_chapter": 3}],
    }


def _fake_chat_json(system, user, **kw):
    if "发散" in system and "故事方案" in system:
        return {"candidates": [
            {"pitch": f"候选{i}卖点", "story": dict(_stub_story(), title=f"候选书{i}")}
            for i in (1, 2, 3)]}
    if "人物阵容方案" in system:
        return {"candidates": [{"pitch": f"阵容{i}气质", "cast": _stub_characters()} for i in (1, 2)]}
    if "策划主编" in system:
        return _stub_story()
    if "塑造立体人物" in system:
        return _stub_characters()
    if "大纲师" in system:
        return _stub_outline()
    if "剧情管理员" in system:
        return {"global_summary": "甲开始查案。", "recent_detail": "本章详摘。",
                "character_updates": [{"name": "甲", "update": "获得线索"}], "timeline": "次日",
                "foreshadow_progress": [{"id": "F1", "status": "paid" if "第 3 章" in user or "第3章" in user else "planted", "note": "体现"}]}
    if "审校" in user:
        return {"pass": True, "issues": []}
    if "终稿全局检查" in user:
        return {"issues": [], "verdict": "可交付"}
    raise AssertionError(f"未识别的 chat_json 调用: {user[:100]}")


def _fake_chat(system, user, **kw):
    return "这是桩正文。甲说：“线索在这里。”\n\n乙沉默不语。"


def run(name):
    from novel_workflow import imagine, pipeline
    from novel_workflow.state import NovelState

    pipeline.chat = _fake_chat
    pipeline.chat_json = _fake_chat_json
    imagine.chat_json = _fake_chat_json
    orig_input = builtins.input
    answers = iter(["2", "1"])  # imagine：选故事候选2、阵容1；其余确认门一律 y
    builtins.input = lambda prompt="": next(answers, "y")
    try:
        state = NovelState(name + "_dryrun")
        state.data["spec"] = "干跑测试"
        state.data["total_words"] = 9000
        state.save()
        # 无调研且未显式降级：必须拒绝发散
        try:
            imagine.run(state)
            raise AssertionError("未调研且未降级时 imagine 应拒绝执行")
        except SystemExit:
            pass
        imagine.run(state, no_research=True)
        assert state.data["imagine"]["research"]["skipped"] is True
        assert "未经市场调研" in (state.imagine_dir / "story_candidates.md").read_text(encoding="utf-8")
        assert state.data["story"]["title"] == "候选书2", "imagine 故事选择未生效"
        assert state.data["imagine"]["cast_choice"] == 0
        assert (state.imagine_dir / "story_candidates.md").exists()
        assert (state.imagine_dir / "cast_candidates.md").exists()
        for stage in ("story", "characters", "outline", "chapters", "assemble"):
            getattr(pipeline, f"stage_{stage}")(state)
        assert state.data["confirmed"] == {"story": True, "characters": True, "outline": True, "final": True}
        assert state.data["chapters_done"] == [1, 2, 3]
        assert not state.unrecycled_foreshadows(), "伏笔未回收"
        title = state.data["story"]["title"]
        assert (state.final_dir / f"{title}.md").exists()
        assert (state.final_dir / f"{title}.txt").exists()
        assert (state.settings_dir / "story.md").exists() and (state.settings_dir / "characters.md").exists()
        assert (state.outline_dir / "outline.md").exists() and (state.final_dir / "report.md").exists()
        # 旧平铺布局迁移：模拟旧成品与旧报告留在根目录，重建 state 应自动归位
        (state.final_dir / f"{title}.md").rename(state.dir / f"{title}.md")
        (state.final_dir / "report.md").rename(state.dir / "05_final_report.md")
        NovelState(name + "_dryrun")
        assert (state.final_dir / f"{title}.md").exists(), "旧成品迁移失败"
        assert (state.final_dir / "report.md").exists(), "旧报告迁移失败"
        assert not (state.dir / f"{title}.md").exists() and not (state.dir / "05_final_report.md").exists()
        # 断点续跑：已完成阶段应全部跳过（含 imagine 重入）
        imagine.run(state, no_research=True)
        for stage in ("story", "characters", "outline", "chapters"):
            getattr(pipeline, f"stage_{stage}")(state)
        print("\nDRY-RUN PASS：imagine 候选发散与挑选、故事/人物设定、大纲（弧光/伏笔校验）、"
              "章节循环、装配导出、断点续跑均通过。")
        print(f"产物目录：{state.dir}")
    finally:
        builtins.input = orig_input