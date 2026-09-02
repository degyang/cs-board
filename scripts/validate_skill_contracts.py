#!/usr/bin/env python3
"""Deterministically validate the Mountain Skill contract without loading skills."""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


STAGES = {
    "script-segmenter": {"name": "visual-anchor-generator", "stage": "generate-visual-anchors", "inputs": ["script_preparation", "visual-anchor"], "outputs": ["planning.av-plan"], "retry_scope": None},
    "voice-cloner": {"name": "voice-cloner", "stage": "clone-voice", "inputs": ["planning.av-plan"], "outputs": ["audio.voice-manifest", "timing.timeline"], "retry_scope": "--unit <unit-id>"},
    "storyboard-planner": {"name": "storyboard-planner", "stage": "plan-storyboard", "inputs": ["planning.av-plan", "timing.timeline", "style.snapshot"], "outputs": ["planning.storyboard"], "retry_scope": None},
    "illustration-generator": {"name": "illustration-generator", "stage": "generate-illustrations", "inputs": ["planning.storyboard", "style.snapshot"], "outputs": ["illustrations.manifest"], "retry_scope": None},
    "visual-renderer": {"name": "visual-renderer", "stage": "render-visuals", "inputs": ["illustrations.manifest", "timing.timeline", "planning.storyboard"], "outputs": ["render.manifest"], "retry_scope": "--visual <visual-id>"},
    "av-compositor": {"name": "av-compositor", "stage": "compose-video", "inputs": ["audio.voice-manifest", "timing.timeline", "render.manifest"], "outputs": ["output.final-manifest"], "retry_scope": None},
}
WORKFLOW = "video-workflow"
FORBIDDEN = ("--script", "--reference", "--tts-url", "--tts-mode", "创建或选择 Project", '"reference_audio"')


def lint(root: Path) -> list[str]:
    errors: list[str] = []
    expected = set(STAGES) | {WORKFLOW}
    actual = {item.name for item in root.iterdir() if item.is_dir() and (item / "SKILL.md").is_file()} if root.exists() else set()
    if actual != expected:
        errors.append(f"skill directories must be {sorted(expected)}, got {sorted(actual)}")
    for directory, contract in STAGES.items():
        name, stage = contract["name"], contract["stage"]
        path = root / directory / "SKILL.md"
        text = path.read_text(encoding="utf-8") if path.exists() else ""
        frontmatter = re.match(r"\A---\n(.*?)\n---", text, re.S)
        if not frontmatter or not re.search(rf"^name: {re.escape(name)}$", frontmatter.group(1), re.M):
            errors.append(f"{directory}: frontmatter name must be {name}")
        for token in (stage, "task_id", "run_id", "相对路径", "结构化结果", "Artifact"):
            if token not in text:
                errors.append(f"{directory}: missing {token}")
        input_line = next((line for line in text.splitlines() if line.startswith("输入") and "输出" in line), "")
        for token in contract["inputs"]:
            if token not in input_line:
                errors.append(f"{directory}: input declaration missing {token}")
        for token in contract["outputs"]:
            if token not in input_line:
                errors.append(f"{directory}: output declaration missing {token}")
        run = f"stage run --task <task-id> --run <run-id> --stage {stage} --json"
        if run not in text:
            errors.append(f"{directory}: missing canonical stage-run command")
        if contract["retry_scope"]:
            scope = contract["retry_scope"]
            if f"stage retry --task <task-id> --run <run-id> --stage {stage} {scope} --json" not in text:
                errors.append(f"{directory}: missing scoped retry command")
        if directory == "illustration-generator":
            if "尚未由 CORE 实现" not in text:
                errors.append("illustration-generator: must disclose external Gate is unimplemented")
            if f"stage retry --task <task-id> --run <run-id> --stage {stage}" in text:
                errors.append("illustration-generator: unimplemented external Gate must not advertise retry")
        for forbidden in FORBIDDEN:
            if forbidden in text:
                errors.append(f"{directory}: forbidden legacy token {forbidden}")
    workflow = root / WORKFLOW / "SKILL.md"
    workflow_text = workflow.read_text(encoding="utf-8") if workflow.exists() else ""
    if not re.search(r"\A---\n.*?^name: video-workflow$.*?\n---", workflow_text, re.S | re.M):
        errors.append("video-workflow: invalid frontmatter")
    for token in ("WebUI", "task_id", "run_id", "相对路径", "结构化结果", "Artifact", "尚未实现", *[item["stage"] for item in STAGES.values()]):
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
