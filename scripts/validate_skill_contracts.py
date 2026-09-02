#!/usr/bin/env python3
"""Deterministically validate the Mountain Skill contract without loading skills."""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


STAGES = {
    "script-segmenter": ("visual-anchor-generator", "generate-visual-anchors", ["planning.av-plan"]),
    "voice-cloner": ("voice-cloner", "clone-voice", ["planning.av-plan", "audio.voice-manifest", "timing.timeline"]),
    "storyboard-planner": ("storyboard-planner", "plan-storyboard", ["planning.av-plan", "timing.timeline", "style.snapshot", "planning.storyboard"]),
    "illustration-generator": ("illustration-generator", "generate-illustrations", ["planning.storyboard", "style.snapshot", "illustrations.manifest"]),
    "visual-renderer": ("visual-renderer", "render-visuals", ["illustrations.manifest", "timing.timeline", "planning.storyboard", "render.manifest"]),
    "av-compositor": ("av-compositor", "compose-video", ["audio.voice-manifest", "timing.timeline", "render.manifest", "output.final-manifest"]),
}
WORKFLOW = "video-workflow"
FORBIDDEN = ("--script", "--reference", "--tts-url", "--tts-mode", "创建或选择 Project", '"reference_audio"')


def lint(root: Path) -> list[str]:
    errors: list[str] = []
    expected = set(STAGES) | {WORKFLOW}
    actual = {item.name for item in root.iterdir() if item.is_dir() and (item / "SKILL.md").is_file()} if root.exists() else set()
    if actual != expected:
        errors.append(f"skill directories must be {sorted(expected)}, got {sorted(actual)}")
    for directory, (name, stage, artifacts) in STAGES.items():
        path = root / directory / "SKILL.md"
        text = path.read_text(encoding="utf-8") if path.exists() else ""
        frontmatter = re.match(r"\A---\n(.*?)\n---", text, re.S)
        if not frontmatter or not re.search(rf"^name: {re.escape(name)}$", frontmatter.group(1), re.M):
            errors.append(f"{directory}: frontmatter name must be {name}")
        for token in (stage, "task_id", "run_id", "相对路径", "结构化结果", "Artifact", *artifacts):
            if token not in text:
                errors.append(f"{directory}: missing {token}")
        run = f"stage run --task <task-id> --run <run-id> --stage {stage} --json"
        if run not in text:
            errors.append(f"{directory}: missing canonical stage-run command")
        if directory in {"voice-cloner", "illustration-generator", "visual-renderer"}:
            scope = "--unit <unit-id>" if directory == "voice-cloner" else "--visual <visual-id>"
            if f"stage retry --task <task-id> --run <run-id> --stage {stage} {scope} --json" not in text:
                errors.append(f"{directory}: missing scoped retry command")
        if directory == "illustration-generator" and "尚未由 CORE 实现" not in text:
            errors.append("illustration-generator: must disclose external Gate is unimplemented")
        for forbidden in FORBIDDEN:
            if forbidden in text:
                errors.append(f"{directory}: forbidden legacy token {forbidden}")
    workflow = root / WORKFLOW / "SKILL.md"
    workflow_text = workflow.read_text(encoding="utf-8") if workflow.exists() else ""
    if not re.search(r"\A---\n.*?^name: video-workflow$.*?\n---", workflow_text, re.S | re.M):
        errors.append("video-workflow: invalid frontmatter")
    for token in ("WebUI", "task_id", "run_id", "相对路径", "结构化结果", "Artifact", "尚未实现", *[item[1] for item in STAGES.values()]):
        if token not in workflow_text:
            errors.append(f"video-workflow: missing {token}")
    for forbidden in FORBIDDEN:
        if forbidden in workflow_text:
            errors.append(f"video-workflow: forbidden legacy token {forbidden}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--skills-root", type=Path, default=Path(__file__).resolve().parents[1] / "skills")
    args = parser.parse_args()
    errors = lint(args.skills_root)
    if errors:
        print("Skill contract validation failed:", file=sys.stderr)
        print("\n".join(f"- {error}" for error in errors), file=sys.stderr)
        return 1
    print(f"Skill contract validation passed: {args.skills_root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
