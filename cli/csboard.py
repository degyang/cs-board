from __future__ import annotations

import argparse
import json
import os
import sys
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

    project = resources.add_parser("project")
    project_actions = project.add_subparsers(dest="action", required=True)
    create = project_actions.add_parser("create")
    create.add_argument("--title")
    create.add_argument("--request", type=Path)
    create.add_argument("--pipeline", default="mountain-av-v1")
    create.add_argument("--engine", default="whiteboard", choices=[item.value for item in Engine])
    show = project_actions.add_parser("show")
    show.add_argument("--project", required=True)

    run = resources.add_parser("run")
    run_actions = run.add_subparsers(dest="action", required=True)
    trace = run_actions.add_parser("trace")
    trace.add_argument("--project", required=True)
    trace.add_argument("--run", required=True)

    events = resources.add_parser("events")
    events_actions = events.add_subparsers(dest="action", required=True)
    events_list = events_actions.add_parser("list")
    events_list.add_argument("--project", required=True)
    events_list.add_argument("--run", required=True)
    events_list.add_argument("--after", type=int, default=0)

    logs = resources.add_parser("logs")
    logs_actions = logs.add_subparsers(dest="action", required=True)
    logs_tail = logs_actions.add_parser("tail")
    logs_tail.add_argument("--project", required=True)
    logs_tail.add_argument("--run", required=True)

    diagnostics = resources.add_parser("diagnostics")
    diagnostics_actions = diagnostics.add_subparsers(dest="action", required=True)
    diagnostics_export = diagnostics_actions.add_parser("export")
    diagnostics_export.add_argument("--project", required=True)
    diagnostics_export.add_argument("--run", required=True)

    pipeline = resources.add_parser("pipeline")
    pipeline_actions = pipeline.add_subparsers(dest="action", required=True)
    for name in ("run", "resume"):
        command = pipeline_actions.add_parser(name)
        command.add_argument("--project", required=True)
        command.add_argument("--policy", default="auto", choices=["auto", "gated", "targeted"])

    stage = resources.add_parser("stage")
    stage_actions = stage.add_subparsers(dest="action", required=True)
    for name in ("run", "retry"):
        command = stage_actions.add_parser(name)
        command.add_argument("--project", required=True)
        command.add_argument("--run")
        command.add_argument("--stage", required=True)
        command.add_argument("--unit")
        command.add_argument("--visual")
        command.add_argument("--script")
    return root


def execute(args: argparse.Namespace) -> dict[str, Any]:
    commands = MountainCommands(args.data_dir)
    if (args.resource, args.action) == ("project", "create"):
        request = {} if args.request is None else json.loads(args.request.read_text(encoding="utf-8"))
        title = args.title or request.get("title", "")
        return commands.create_project(title, request.get("pipeline", args.pipeline), Engine(request.get("engine", args.engine)))
    if (args.resource, args.action) == ("project", "show"):
        return commands.show_project(args.project)
    if (args.resource, args.action) == ("run", "trace"):
        return commands.trace_run(args.project, args.run)
    if (args.resource, args.action) == ("events", "list"):
        return commands.list_events(args.project, args.run, args.after)
    if (args.resource, args.action) == ("logs", "tail"):
        return commands.list_logs(args.project, args.run)
    if (args.resource, args.action) == ("diagnostics", "export"):
        return commands.export_diagnostics(args.project, args.run)
    if (args.resource, args.action, args.stage) == ("stage", "run", "segment-script"):
        if not args.run or not args.script:
            raise ValueError("segment-script 需要 --run 与 --script")
        return commands.segment_script(args.project, args.run, args.script)
    if args.resource in {"pipeline", "stage"}:
        raise DomainError(
            "CAPABILITY_NOT_AVAILABLE",
            f"{args.resource}.{args.action} 将在后续 Mountain PR 提供；M04 仅提供共享 CLI 状态与诊断能力",
        )
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
