"""imagine 模块：候选发散 + 人工挑选。

流程：
  1. 发散 N 个差异化故事候选 → 渲染 imagine/story_candidates.md → 终端选编号
  2. 针对选中故事发散 M 套人物阵容候选 → 渲染 imagine/cast_candidates.md → 终端选编号
  3. 选中者写入 state.story / state.characters（未确认状态），交给正式管线的确认门
支持断点：候选与选择均落盘，重跑不重复消耗已完成的发散。
"""
import json

from . import prompts
from .llm import chat_json
from .pipeline import render_story, render_characters

STORY_CANDIDATES = 3
CAST_CANDIDATES = 2


def _dump(obj):
    return json.dumps(obj, ensure_ascii=False, indent=2)


def _pick(prompt_text, count):
    while True:
        ans = input(prompt_text).strip()
        if ans.isdigit() and 1 <= int(ans) <= count:
            return int(ans) - 1
        print(f"  请输入 1~{count} 之间的编号。")


def _render_story_candidates(candidates):
    lines = ["# 故事候选清单\n\n> 阅读后在终端输入编号选择。每个候选都是完整可发展的故事设定。\n"]
    for i, c in enumerate(candidates, 1):
        lines.append(f"\n---\n\n# 候选 {i}：{c['story']['title']}\n\n**推荐语**：{c['pitch']}\n")
        lines.append(render_story(c["story"]))
    return "\n".join(lines)


def _render_cast_candidates(candidates):
    lines = ["# 人物阵容候选清单\n\n> 阅读后在终端输入编号选择。\n"]
    for i, c in enumerate(candidates, 1):
        names = "、".join(ch["name"] + f"（{ch['role']}）" for ch in c["cast"]["characters"])
        lines.append(f"\n---\n\n# 阵容 {i}\n\n**推荐语**：{c['pitch']}\n**成员**：{names}\n")
        lines.append(render_characters(c["cast"]))
    return "\n".join(lines)


def run(state, story_n=STORY_CANDIDATES, cast_n=CAST_CANDIDATES):
    imag = state.data.setdefault("imagine", {})

    # ---- 故事候选 ----
    if state.data["confirmed"]["story"]:
        print("故事设定已确认，跳过故事候选发散。")
    elif "story_choice" not in imag:
        if "story_candidates" not in imag:
            print(f"[imagine 1/2] 发散 {story_n} 个故事候选…")
            result = chat_json(prompts.IMAGINE_STORY_SYSTEM,
                               prompts.IMAGINE_STORY_USER.format(spec=state.data["spec"], n=story_n),
                               max_tokens=16384)
            imag["story_candidates"] = result["candidates"]
            state.save()
        cands = imag["story_candidates"]
        path = state.imagine_dir / "story_candidates.md"
        path.write_text(_render_story_candidates(cands), encoding="utf-8")
        print(f"\n=== 故事候选已写入 {path} ===")
        for i, c in enumerate(cands, 1):
            print(f"  [{i}] {c['story']['title']} —— {c['pitch']}")
        idx = _pick("选择故事候选编号：", len(cands))
        imag["story_choice"] = idx
        state.data["story"] = cands[idx]["story"]
        state.save()
        print(f"已选定故事：{cands[idx]['story']['title']}")

    # ---- 人物阵容候选 ----
    if state.data["confirmed"]["characters"]:
        print("人物设定已确认，跳过阵容候选发散。")
    elif "cast_choice" not in imag:
        if "cast_candidates" not in imag:
            print(f"[imagine 2/2] 发散 {cast_n} 套人物阵容候选…")
            result = chat_json(prompts.IMAGINE_CAST_SYSTEM,
                               prompts.IMAGINE_CAST_USER.format(story=_dump(state.data["story"]), n=cast_n),
                               max_tokens=16384)
            imag["cast_candidates"] = result["candidates"]
            state.save()
        cands = imag["cast_candidates"]
        path = state.imagine_dir / "cast_candidates.md"
        path.write_text(_render_cast_candidates(cands), encoding="utf-8")
        print(f"\n=== 人物阵容候选已写入 {path} ===")
        for i, c in enumerate(cands, 1):
            print(f"  [{i}] {c['pitch']}")
        idx = _pick("选择阵容编号：", len(cands))
        imag["cast_choice"] = idx
        state.data["characters"] = cands[idx]["cast"]
        state.save()
        print("阵容已选定。")

    print("\nimagine 完成。选中的故事与人物已进入正式管线（待确认状态），"
          "接下来运行 run.py 相同 --name 即可进入确认门。")