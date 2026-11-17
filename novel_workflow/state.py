"""作品状态存储：故事设定、人物设定、大纲、伏笔/弧光登记、滚动摘要、章节进度。
全部落盘为 JSON/MD，可断点续跑。"""
import json

from . import config


class NovelState:
    """作品目录结构：
    output/<name>/
      state.json            # 唯一状态源
      imagine/              # 候选发散与挑选记录
      settings/             # story.md / characters.md
      outline/              # outline.md
      chapters/             # ch01.md ...
      final/                # 书名.md/.txt + report.md
    """

    def __init__(self, name):
        self.dir = config.OUTPUT_ROOT / name
        self.imagine_dir = self.dir / "imagine"
        self.settings_dir = self.dir / "settings"
        self.outline_dir = self.dir / "outline"
        self.chapters_dir = self.dir / "chapters"
        self.final_dir = self.dir / "final"
        for d in (self.imagine_dir, self.settings_dir, self.outline_dir, self.chapters_dir, self.final_dir):
            d.mkdir(parents=True, exist_ok=True)
        self.state_file = self.dir / "state.json"
        self._migrate_legacy_layout()
        self.data = {
            "spec": "",
            "story": None,
            "characters": None,
            "outline": None,
            "confirmed": {"story": False, "characters": False, "outline": False, "final": False},
            "summary": {"global_summary": "（尚无剧情）", "recent_detail": "", "timeline": "开篇"},
            "character_state": {},
            "foreshadow_log": {},
            "chapters_done": [],
        }
        if self.state_file.exists():
            self.data = json.loads(self.state_file.read_text(encoding="utf-8"))

    def _migrate_legacy_layout(self):
        """旧平铺布局 → 分区布局。只移动仍留在根目录的旧文件，不动新结构。"""
        moves = {
            "00_candidates_story.md": self.imagine_dir / "story_candidates.md",
            "00_candidates_cast.md": self.imagine_dir / "cast_candidates.md",
            "01_story.md": self.settings_dir / "story.md",
            "02_characters.md": self.settings_dir / "characters.md",
            "01_bible.md": self.settings_dir / "story.md",
            "02_outline.md": self.outline_dir / "outline.md",
            "03_outline.md": self.outline_dir / "outline.md",
            "04_final_report.md": self.final_dir / "report.md",
            "05_final_report.md": self.final_dir / "report.md",
        }
        for old, new in moves.items():
            src = self.dir / old
            if src.exists() and not new.exists():
                src.rename(new)
        # 旧版成品（书名.md/.txt 在根目录）：依据 state.json 里的书名识别
        if self.state_file.exists():
            try:
                title = json.loads(self.state_file.read_text(encoding="utf-8")).get("story", {}).get("title")
            except (json.JSONDecodeError, AttributeError):
                title = None
            if title:
                for ext in (".md", ".txt"):
                    src = self.dir / f"{title}{ext}"
                    dst = self.final_dir / f"{title}{ext}"
                    if src.exists() and not dst.exists():
                        src.rename(dst)

    def save(self):
        self.state_file.write_text(json.dumps(self.data, ensure_ascii=False, indent=2), encoding="utf-8")

    # ---- 章节文件 ----
    def chapter_path(self, no):
        return self.chapters_dir / f"ch{no:02d}.md"

    def write_chapter(self, no, title, text):
        self.chapter_path(no).write_text(f"# 第{no}章 {title}\n\n{text}\n", encoding="utf-8")

    def read_chapter(self, no):
        p = self.chapter_path(no)
        return p.read_text(encoding="utf-8") if p.exists() else ""

    def previous_tail(self, no, chars=500):
        if no <= 1:
            return "（本章为开篇）"
        text = self.read_chapter(no - 1)
        return text[-chars:] if text else "（上一章缺失）"

    # ---- 上下文切片 ----
    def relevant_characters(self, chapter):
        names = set(chapter.get("characters", []))
        cards = [c for c in self.data["characters"]["characters"] if c["name"] in names]
        if not cards:
            cards = self.data["characters"]["characters"]
        lines = []
        for c in cards:
            arc = c.get("arc", {})
            line = (f"### {c['name']}（{c['role']}，{c.get('age', '')}，{c.get('occupation', '')}）\n"
                    f"- 标志细节：{c.get('appearance', '')}\n"
                    f"- 外在目标 want：{c.get('want', c.get('motivation', ''))}｜内在需求 need：{c.get('need', '')}\n"
                    f"- 恐惧：{c.get('fear', '')}｜内在谎言：{c.get('lie', '')}｜秘密：{c.get('secret', '')}\n"
                    f"- 缺陷：{c.get('flaw', '')}\n"
                    f"- 口吻：{c.get('voice', '')}\n"
                    f"- 弧光：{arc.get('start', '')} → {arc.get('turn', '')} → {arc.get('end', '')}")
            if c.get("psych_profile"):
                line += f"\n- 心理侧写：{c['psych_profile']}"
            extra = self.data["character_state"].get(c["name"], "")
            if extra:
                line += f"\n- 当前状态（截至上一章）：{extra}"
            lines.append(line)
        return "\n\n".join(lines)

    def relevant_relations(self, chapter):
        names = set(chapter.get("characters", []))
        web = self.data["characters"].get("relationship_web", [])
        rels = [r for r in web if all(n in names for n in r["pair"].replace("×", "x").split("x"))]
        if not rels:
            return "（本章无已登记的关系张力）"
        return "\n".join(f"- {r['pair']}：表面「{r['surface']}」，暗层「{r['tension']}」" for r in rels)

    def setting_brief(self):
        s = self.data["story"]["setting"]
        return f"{s['time']}｜{s['place']}｜{s['society']}｜氛围：{s['atmosphere']}"

    def arc_tasks(self, no):
        tasks = [f"[{b['name']}·{b['beat']}] {b['desc']}"
                 for b in self.data["outline"].get("arc_beats", []) if b["chapter"] == no]
        return "\n".join(tasks) if tasks else "（本章无指定弧光节点，但人物言行仍须符合深卡）"

    def foreshadow_tasks(self, no):
        tasks = []
        for f in self.data["outline"]["foreshadows"]:
            if f["plant_chapter"] == no:
                tasks.append(f"[埋设 {f['id']}] {f['content']}（计划第{f['payoff_chapter']}章回收）")
            if f["payoff_chapter"] == no:
                tasks.append(f"[回收 {f['id']}] {f['content']}（第{f['plant_chapter']}章已埋设，本章必须回收）")
        return "\n".join(tasks) if tasks else "（本章无伏笔任务）"

    def apply_summary_update(self, no, update):
        self.data["summary"] = {
            "global_summary": update.get("global_summary", self.data["summary"]["global_summary"]),
            "recent_detail": update.get("recent_detail", ""),
            "timeline": update.get("timeline", ""),
        }
        for cu in update.get("character_updates", []):
            prev = self.data["character_state"].get(cu["name"], "")
            self.data["character_state"][cu["name"]] = (prev + "；" + cu["update"]).strip("；")
        log = self.data["foreshadow_log"]
        for fp in update.get("foreshadow_progress", []):
            log.setdefault(fp["id"], []).append({"chapter": no, "status": fp["status"], "note": fp.get("note", "")})
        if no not in self.data["chapters_done"]:
            self.data["chapters_done"].append(no)
        self.save()

    def unrecycled_foreshadows(self):
        problems = []
        for f in self.data["outline"]["foreshadows"]:
            entries = self.data["foreshadow_log"].get(f["id"], [])
            if not any(e["status"] == "paid" for e in entries):
                problems.append(f"{f['id']}（计划第{f['payoff_chapter']}章回收）未见回收记录")
        return problems