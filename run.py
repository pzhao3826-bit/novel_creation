#!/usr/bin/env python3
"""中篇小说自动创作管线入口。

用法：
  python3 run.py --name my_novel --spec "题材：悬疑；总字数约5万；视角：第三人称限知；……"
  python3 run.py --name my_novel            # 断点续跑（spec 已保存）
  python3 run.py --name my_novel --stage story|characters|outline|chapters|assemble
  python3 run.py --name my_novel --spec "悬疑，海边小镇" --imagine   # 先发散候选，你来挑
  python3 run.py --name my_novel --dry-run  # 无 API 干跑，验证管线结构
"""
import argparse
import sys

from novel_workflow.state import NovelState


def main():
    ap = argparse.ArgumentParser(description="中篇小说自动创作管线")
    ap.add_argument("--name", required=True, help="作品标识（output/ 下的目录名）")
    ap.add_argument("--spec", help="创作需求文本，或指向 .txt/.md 文件的路径")
    ap.add_argument("--total-words", type=int, default=50000, help="目标总字数（默认5万）")
    ap.add_argument("--stage", choices=["story", "characters", "outline", "chapters", "assemble"], help="只跑到指定阶段")
    ap.add_argument("--imagine", action="store_true", help="先发散故事/人物候选供挑选，选完继续正式管线")
    ap.add_argument("--imagine-only", action="store_true", help="只做候选发散与挑选，选完即停")
    ap.add_argument("--story-candidates", type=int, default=3, help="故事候选数（默认3）")
    ap.add_argument("--cast-candidates", type=int, default=2, help="人物阵容候选数（默认2）")
    ap.add_argument("--dry-run", action="store_true", help="用桩数据走通全流程，不调用 API")
    args = ap.parse_args()

    if args.dry_run:
        from novel_workflow import dry_run
        dry_run.run(args.name)
        return

    from novel_workflow import config, pipeline
    config.validate()

    state = NovelState(args.name)
    if args.spec:
        from pathlib import Path
        p = Path(args.spec)
        spec_text = p.read_text(encoding="utf-8") if p.is_file() else args.spec
        if state.data["spec"] and state.data["spec"] != spec_text and state.data["chapters_done"]:
            sys.exit("已有章节进度，不允许更换 spec。请换 --name 新建作品。")
        state.data["spec"] = spec_text
    if not state.data["spec"]:
        sys.exit("首次运行必须提供 --spec。")
    state.data["total_words"] = args.total_words
    state.save()

    if args.imagine or args.imagine_only:
        from novel_workflow import imagine
        imagine.run(state, story_n=args.story_candidates, cast_n=args.cast_candidates)
        if args.imagine_only:
            return

    stages = ["story", "characters", "outline", "chapters", "assemble"]
    stop = stages.index(args.stage) + 1 if args.stage else len(stages)
    for name in stages[:stop]:
        getattr(pipeline, f"stage_{name}")(state)


if __name__ == "__main__":
    main()