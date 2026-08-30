from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

from csboard.application.commands import MountainCommands
from csboard.domain.enums import Engine
from csboard.domain.errors import DomainError, NotFoundError


EXIT_OK = 0
EXIT_VALIDATION = 2
EXIT_NOT_FOUND = 3
EXIT_RETRYABLE = 4
EXIT_CANCELLED = 5
ROOT = Path(__file__).resolve().parents[1]


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(prog="python -m cli.csboard")
    root.add_argument("--data-dir", type=Path, default=Path(os.environ.get("CSBOARD_DATA_DIR", ROOT / ".webapp")))
    root.add_argument("--json", action="store_true", help="以稳定 JSON 输出结果")
    resources = root.add_subparsers(dest="resource", required=True)

    # ── task ──────────────────────────────────────────────────────
    task = resources.add_parser("task")
    task_actions = task.add_subparsers(dest="action", required=True)
    create = task_actions.add_parser("create")
    create.add_argument("--title")
    create.add_argument("--request", type=Path)
    create.add_argument("--pipeline", default="mountain-av-v1")
    create.add_argument("--engine", default="whiteboard", choices=[item.value for item in Engine])
    show = task_actions.add_parser("show")
    show.add_argument("--task", required=True)

    # ── run ──────────────────────────────────────────────────────────
    run = resources.add_parser("run")
    run_actions = run.add_subparsers(dest="action", required=True)
    trace = run_actions.add_parser("trace")
    trace.add_argument("--task", required=True)
    trace.add_argument("--run", required=True)

    # ── events ───────────────────────────────────────────────────────
    events = resources.add_parser("events")
    events_actions = events.add_subparsers(dest="action", required=True)
    events_list = events_actions.add_parser("list")
    events_list.add_argument("--task", required=True)
    events_list.add_argument("--run", required=True)
    events_list.add_argument("--after", type=int, default=0)

    # ── logs ─────────────────────────────────────────────────────────
    logs = resources.add_parser("logs")
    logs_actions = logs.add_subparsers(dest="action", required=True)
    logs_tail = logs_actions.add_parser("tail")
    logs_tail.add_argument("--task", required=True)
    logs_tail.add_argument("--run", required=True)
    logs_tail.add_argument("--follow", action="store_true", help="持续输出新日志")

    # ── diagnostics ──────────────────────────────────────────────────
    diagnostics = resources.add_parser("diagnostics")
    diagnostics_actions = diagnostics.add_subparsers(dest="action", required=True)
    diagnostics_export = diagnostics_actions.add_parser("export")
    diagnostics_export.add_argument("--task", required=True)
    diagnostics_export.add_argument("--run", required=True)

    # ── artifact ─────────────────────────────────────────────────────
    artifact = resources.add_parser("artifact")
    artifact_actions = artifact.add_subparsers(dest="action", required=True)
    artifact_show = artifact_actions.add_parser("show")
    artifact_show.add_argument("--task", required=True)
    artifact_show.add_argument("--run", required=True)
    artifact_show.add_argument("--key", required=True, help="Artifact key (如 planning.av-plan)")

    # ── pipeline ─────────────────────────────────────────────────────
    pipeline = resources.add_parser("pipeline")
    pipeline_actions = pipeline.add_subparsers(dest="action", required=True)
    pipeline_run = pipeline_actions.add_parser("run")
    pipeline_run.add_argument("--task", required=True)
    pipeline_run.add_argument("--run")
    pipeline_run.add_argument("--policy", default="auto", choices=["auto", "gated", "targeted"])
    pipeline_run.add_argument("--stage", help="targeted 策略的目标阶段")
    pipeline_run.add_argument("--events", choices=["jsonl"], help="流式输出事件")
    pipeline_resume = pipeline_actions.add_parser("resume")
    pipeline_resume.add_argument("--task", required=True)
    pipeline_resume.add_argument("--run")
    pipeline_resume.add_argument("--policy", default="auto", choices=["auto", "gated", "targeted"])
    pipeline_resume.add_argument("--events", choices=["jsonl"], help="流式输出事件")

    # ── stage ────────────────────────────────────────────────────────
    stage = resources.add_parser("stage")
    stage_actions = stage.add_subparsers(dest="action", required=True)
    stage_run = stage_actions.add_parser("run")
    stage_run.add_argument("--task", required=True)
    stage_run.add_argument("--run")
    stage_run.add_argument("--stage", required=True)
    stage_run.add_argument("--script", help="（已废弃）文案内容由 task.json 管理")
    stage_run.add_argument("--reference", type=Path, help="clone-voice 的参考音频")
    stage_run.add_argument("--tts-url", default="http://127.0.0.1:7860", help="TTS 服务地址")
    stage_run.add_argument("--tts-mode", default="gradio", choices=["gradio", "fastapi"], help="TTS 模式")
    stage_run.add_argument("--events", choices=["jsonl"], help="流式输出事件")

    stage_retry = stage_actions.add_parser("retry")
    stage_retry.add_argument("--task", required=True)
    stage_retry.add_argument("--run")
    stage_retry.add_argument("--stage", required=True)
    stage_retry.add_argument("--unit", help="重试指定 unit")
    stage_retry.add_argument("--visual", help="重试指定 visual")

    return root


def _stream_events_jsonl(commands: MountainCommands, task_id: str, run_id: str, after: int = 0) -> None:
    """Stream events as JSONL to stdout."""
    cursor = after
    while True:
        result = commands.list_events(task_id, run_id, cursor)
        for event in result.get("items", []):
            print(json.dumps(event, ensure_ascii=False, sort_keys=True), flush=True)
            cursor = event.get("sequence", cursor)
        time.sleep(0.5)


def execute(args: argparse.Namespace) -> dict[str, Any]:
    commands = MountainCommands(args.data_dir)

    # ── task ──────────────────────────────────────────────────────
    if (args.resource, args.action) == ("task", "create"):
        request = {} if args.request is None else json.loads(args.request.read_text(encoding="utf-8"))
        title = args.title or request.get("title", "")
        return commands.create_task(title, request.get("pipeline", args.pipeline), Engine(request.get("engine", args.engine)), request)
    if (args.resource, args.action) == ("task", "show"):
        return commands.show_task(args.task)

    # ── run ──────────────────────────────────────────────────────────
    if (args.resource, args.action) == ("run", "trace"):
        return commands.trace_run(args.task, args.run)

    # ── events ───────────────────────────────────────────────────────
    if (args.resource, args.action) == ("events", "list"):
        return commands.list_events(args.task, args.run, args.after)

    # ── logs ─────────────────────────────────────────────────────────
    if (args.resource, args.action) == ("logs", "tail"):
        result = commands.list_logs(args.task, args.run)
        if hasattr(args, "follow") and args.follow:
            # Print existing logs first
            for item in result.get("items", []):
                print(json.dumps(item, ensure_ascii=False, sort_keys=True), flush=True)
            # Then follow for new logs
            log_path = commands.repository.run_dir(args.task, args.run) / "observability" / "logs.jsonl"
            last_size = log_path.stat().st_size if log_path.exists() else 0
            while True:
                time.sleep(0.5)
                if not log_path.exists():
                    continue
                current_size = log_path.stat().st_size
                if current_size > last_size:
                    with log_path.open("r", encoding="utf-8") as f:
                        f.seek(last_size)
                        for line in f:
                            line = line.strip()
                            if line:
                                print(line, flush=True)
                    last_size = current_size
        return result

    # ── diagnostics ──────────────────────────────────────────────────
    if (args.resource, args.action) == ("diagnostics", "export"):
        return commands.export_diagnostics(args.task, args.run)

    # ── artifact ─────────────────────────────────────────────────────
    if (args.resource, args.action) == ("artifact", "show"):
        return commands.artifact_show(args.task, args.run, args.key)

    # ── pipeline ─────────────────────────────────────────────────────
    if (args.resource, args.action) == ("pipeline", "run"):
        result = commands.pipeline_run(args.task, getattr(args, "run", None), args.policy, args.stage)
        if hasattr(args, "events") and args.events == "jsonl":
            # Stream events in background (simplified: just return result)
            pass
        return result
    if (args.resource, args.action) == ("pipeline", "resume"):
        result = commands.pipeline_resume(args.task, getattr(args, "run", None), args.policy)
        if hasattr(args, "events") and args.events == "jsonl":
            pass
        return result

    # ── stage ────────────────────────────────────────────────────────
    if (args.resource, args.action) == ("stage", "run"):
        # Route to specific stage handler or pipeline
        if args.stage == "generate-visual-anchors":
            task = commands.repository.get_task(args.task)
            run_id = getattr(args, "run", None) or task.active_run_id
            if not run_id:
                raise ValueError("generate-visual-anchors 需要 --run")
            return commands.generate_visual_anchors(args.task, run_id)
        elif args.stage == "clone-voice":
            task = commands.repository.get_task(args.task)
            run_id = getattr(args, "run", None) or task.active_run_id
            if not run_id or not args.reference:
                raise ValueError("clone-voice 需要 --run 与 --reference")
            from csboard.adapters.indextts.tts_adapter import IndexTTSAdapter
            from csboard.adapters.whisper.alignment_adapter import WhisperAlignmentAdapter
            from csboard.adapters.ffmpeg.media_adapter import FFmpegMediaAdapter
            tts = IndexTTSAdapter(base_url=args.tts_url, mode=args.tts_mode)
            alignment = WhisperAlignmentAdapter(
                renderer_root=ROOT / "video_renderer",
            )
            media = FFmpegMediaAdapter()
            return commands.clone_voice(
                args.task, run_id, tts, alignment, media,
                reference_audio=args.reference,
            )
        elif args.stage == "plan-storyboard":
            task = commands.repository.get_task(args.task)
            run_id = getattr(args, "run", None) or task.active_run_id
            if not run_id:
                raise ValueError("需要 --run 或任务有活跃运行")
            text_model = commands._text_model_from_request(args.task)
            return commands.plan_storyboard(args.task, run_id, text_model)
        elif args.stage == "generate-illustrations":
            task = commands.repository.get_task(args.task)
            run_id = getattr(args, "run", None) or task.active_run_id
            if not run_id:
                raise ValueError("需要 --run 或任务有活跃运行")
            image_model = commands._image_model_from_request(args.task)
            return commands.generate_illustrations(args.task, run_id, image_model)
        elif args.stage == "render-visuals":
            task = commands.repository.get_task(args.task)
            run_id = getattr(args, "run", None) or task.active_run_id
            if not run_id:
                raise ValueError("需要 --run 或任务有活跃运行")
            from csboard.adapters.whiteboard.renderer_adapter import WhiteboardRendererAdapter
            renderer = WhiteboardRendererAdapter()
            return commands.render_visuals(args.task, run_id, renderer)
        elif args.stage == "compose-video":
            task = commands.repository.get_task(args.task)
            run_id = getattr(args, "run", None) or task.active_run_id
            if not run_id:
                raise ValueError("需要 --run 或任务有活跃运行")
            from csboard.adapters.ffmpeg.media_adapter import FFmpegMediaAdapter
            media = FFmpegMediaAdapter()
            return commands.compose_video(args.task, run_id, media)
        else:
            # For unregistered stages, raise CAPABILITY_NOT_AVAILABLE
            if args.stage not in commands.pipeline._executors:
                raise DomainError(
                    "CAPABILITY_NOT_AVAILABLE",
                    f"stage.run.{args.stage} 将在后续 Mountain PR 提供",
                )
            # For registered stages, use pipeline targeted mode
            task = commands.repository.get_task(args.task)
            run_id = getattr(args, "run", None) or task.active_run_id
            if not run_id:
                raise ValueError("需要 --run 或任务有活跃运行")
            return commands.pipeline_run(args.task, run_id, "targeted", args.stage)

    if (args.resource, args.action) == ("stage", "retry"):
        task = commands.repository.get_task(args.task)
        run_id = getattr(args, "run", None) or task.active_run_id
        if not run_id:
            raise ValueError("需要 --run 或任务有活跃运行")
        return commands.stage_retry(args.task, run_id, args.stage, args.unit, args.visual)

    raise ValueError("未知命令")


def main(argv: list[str] | None = None) -> int:
    raw_args = list(sys.argv[1:] if argv is None else argv)
    # The documented form puts --json after a command; argparse global options
    # normally require it first, so normalize it without changing the public CLI.
    if "--json" in raw_args:
        raw_args.remove("--json")
        raw_args.insert(0, "--json")
    args = parser().parse_args(raw_args)
    try:
        result = execute(args)
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return EXIT_OK
    except NotFoundError as error:
        result = {"ok": False, "error": {"code": error.code, "message": error.message, "retryable": error.retryable}}
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return EXIT_NOT_FOUND
    except (DomainError, ValueError, OSError, json.JSONDecodeError) as error:
        code = error.code if isinstance(error, DomainError) else "VALIDATION_ERROR"
        result = {"ok": False, "error": {"code": code, "message": str(error), "retryable": False}}
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return EXIT_VALIDATION


if __name__ == "__main__":
    sys.exit(main())
