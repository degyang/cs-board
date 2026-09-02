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

    # ── asset style ──────────────────────────────────────────────────
    asset = resources.add_parser("asset")
    asset_sub = asset.add_subparsers(dest="subresource", required=True)

    style = asset_sub.add_parser("style")
    style_actions = style.add_subparsers(dest="action", required=True)
    style_list = style_actions.add_parser("list")
    style_list.add_argument("--kind", choices=["preset", "custom"])
    style_list.add_argument("--status", choices=["active", "inactive"])
    style_show = style_actions.add_parser("show")
    style_show.add_argument("--id", required=True, help="style_id")
    style_create = style_actions.add_parser("create")
    style_create.add_argument("--name", required=True)
    style_create.add_argument("--prompt", required=True)
    style_create.add_argument("--engine", default="whiteboard")
    style_create.add_argument("--tags", default="[]")
    style_copy = style_actions.add_parser("copy")
    style_copy.add_argument("--id", required=True, help="源 style_id")
    style_copy.add_argument("--name", help="新名称")
    style_update = style_actions.add_parser("update")
    style_update.add_argument("--id", required=True)
    style_update.add_argument("--name")
    style_update.add_argument("--prompt")
    style_activate = style_actions.add_parser("activate")
    style_activate.add_argument("--id", required=True)
    style_deactivate = style_actions.add_parser("deactivate")
    style_deactivate.add_argument("--id", required=True)

    # ── asset voice ──────────────────────────────────────────────────
    voice = asset_sub.add_parser("voice")
    voice_actions = voice.add_subparsers(dest="action", required=True)
    voice_list = voice_actions.add_parser("list")
    voice_show = voice_actions.add_parser("show")
    voice_show.add_argument("--id", required=True)
    voice_import = voice_actions.add_parser("import")
    voice_import.add_argument("--file", type=Path, required=True)
    voice_import.add_argument("--name", default="")
    voice_update = voice_actions.add_parser("update")
    voice_update.add_argument("--id", required=True)
    voice_update.add_argument("--name", required=True)
    voice_activate = voice_actions.add_parser("activate")
    voice_activate.add_argument("--id", required=True)
    voice_deactivate = voice_actions.add_parser("deactivate")
    voice_deactivate.add_argument("--id", required=True)

    # ── service ──────────────────────────────────────────────────────
    service = resources.add_parser("service")
    service_actions = service.add_subparsers(dest="action", required=True)
    service_list = service_actions.add_parser("list")
    service_list.add_argument("--capability")
    service_list.add_argument("--enabled", type=lambda x: x.lower() == "true")
    service_show = service_actions.add_parser("show")
    service_show.add_argument("--id", required=True)
    service_create = service_actions.add_parser("create")
    service_create.add_argument("--file", type=Path, required=True, help="ServiceDefinition JSON 文件")
    service_update = service_actions.add_parser("update")
    service_update.add_argument("--id", required=True)
    service_update.add_argument("--file", type=Path, required=True)
    service_activate = service_actions.add_parser("activate")
    service_activate.add_argument("--id", required=True)
    service_deactivate = service_actions.add_parser("deactivate")
    service_deactivate.add_argument("--id", required=True)
    service_set_default = service_actions.add_parser("set-default")
    service_set_default.add_argument("--id", required=True)
    service_probe = service_actions.add_parser("probe")
    service_probe.add_argument("--id", required=True)
    service_secret_set = service_actions.add_parser("secret-set")
    service_secret_set.add_argument("--id", required=True)
    service_secret_set.add_argument("--key", required=True)
    service_secret_set.add_argument("--value", help="Secret value; if omitted, reads from stdin (getpass)")
    service_secret_delete = service_actions.add_parser("secret-delete")
    service_secret_delete.add_argument("--id", required=True)
    service_secret_delete.add_argument("--key", required=True)

    # ── settings ─────────────────────────────────────────────────────
    settings = resources.add_parser("settings")
    settings_actions = settings.add_subparsers(dest="action", required=True)
    settings_actions.add_parser("toolchain")
    settings_actions.add_parser("storage")
    settings_actions.add_parser("diagnostics")

    # ── stage ────────────────────────────────────────────────────────
    stage = resources.add_parser("stage")
    stage_actions = stage.add_subparsers(dest="action", required=True)
    stage_run = stage_actions.add_parser("run")
    stage_run.add_argument("--task", required=True)
    stage_run.add_argument("--run")
    stage_run.add_argument("--stage", required=True)
    stage_run.add_argument("--events", choices=["jsonl"], help="流式输出事件")

    stage_retry = stage_actions.add_parser("retry")
    stage_retry.add_argument("--task", required=True)
    stage_retry.add_argument("--run")
    stage_retry.add_argument("--stage", required=True)
    stage_retry.add_argument("--unit", help="重试指定 unit")
    stage_retry.add_argument("--visual", help="重试指定 visual")

    return root


def _get_service_registry(data_dir: Path, secret_store=None):
    from csboard.adapters.filesystem.service_registry import FilesystemServiceRegistry
    if secret_store is None:
        from csboard.adapters.secrets import create_secret_store
        import os
        allow_plaintext = os.environ.get("CSBOARD_ALLOW_PLAINTEXT_SECRETS", "") == "1"
        secret_store, _ = create_secret_store(data_dir, encrypted=not allow_plaintext)
    return FilesystemServiceRegistry(data_dir, secret_store)


def _get_asset_repository(data_dir: Path):
    from csboard.adapters.filesystem.asset_repository import FilesystemAssetRepository
    return FilesystemAssetRepository(data_dir)


def execute(args: argparse.Namespace) -> dict[str, Any]:
    import os
    from csboard.adapters.secrets import create_secret_store
    from csboard.adapters.provider_factory import ProviderFactory
    from csboard.application.service_resolver import ServiceResolver

    allow_plaintext = os.environ.get("CSBOARD_ALLOW_PLAINTEXT_SECRETS", "") == "1"
    secret_store, _ = create_secret_store(args.data_dir, encrypted=not allow_plaintext)
    registry = _get_service_registry(args.data_dir, secret_store=secret_store)
    service_resolver = ServiceResolver(registry)
    provider_factory = ProviderFactory(args.data_dir, secret_store=secret_store)

    commands = MountainCommands(
        args.data_dir,
        provider_factory=provider_factory,
        service_resolver=service_resolver,
    )

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
            for item in result.get("items", []):
                print(json.dumps(item, ensure_ascii=False, sort_keys=True), flush=True)
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
        return commands.pipeline_run(args.task, getattr(args, "run", None), args.policy, args.stage)
    if (args.resource, args.action) == ("pipeline", "resume"):
        return commands.pipeline_resume(args.task, getattr(args, "run", None), args.policy)

    # ── stage ────────────────────────────────────────────────────────
    if (args.resource, args.action) == ("stage", "run"):
        if args.stage not in commands.pipeline._executors:
            raise DomainError("CAPABILITY_NOT_AVAILABLE", f"stage.run.{args.stage} 将在后续 Mountain PR 提供")
        task = commands.repository.get_task(args.task)
        run_id = getattr(args, "run", None) or task.active_run_id
        if not run_id:
            raise ValueError("需要 --run 或任务有活跃运行")
        return commands.stage_run(args.task, run_id, args.stage)

    if (args.resource, args.action) == ("stage", "retry"):
        task = commands.repository.get_task(args.task)
        run_id = getattr(args, "run", None) or task.active_run_id
        if not run_id:
            raise ValueError("需要 --run 或任务有活跃运行")
        return commands.stage_retry(args.task, run_id, args.stage, args.unit, args.visual)

    # ── asset style ──────────────────────────────────────────────────
    if args.resource == "asset" and args.subresource == "style":
        from csboard.application.context import utc_now
        repo = _get_asset_repository(args.data_dir)
        if args.action == "list":
            templates = repo.list_style_templates(kind=args.kind, status=args.status)
            return {"items": [t.to_dict() for t in templates], "total": len(templates)}
        if args.action == "show":
            return repo.get_style_template(args.id).to_dict()
        if args.action == "create":
            import uuid
            tags = json.loads(args.tags) if args.tags else []
            now = utc_now()
            from csboard.domain.style_template import StyleTemplate
            template = StyleTemplate(
                style_id=uuid.uuid4().hex[:16],
                revision=1,
                name=args.name,
                kind="custom",
                prompt_text=args.prompt,
                engine=args.engine,
                tags=tags,
                status="active",
                created_at=now,
                updated_at=now,
            )
            repo.save_style_template(template)
            return template.to_dict()
        if args.action == "copy":
            source = repo.get_style_template(args.id)
            import uuid
            now = utc_now()
            custom = source.copy_to_custom(uuid.uuid4().hex[:16], now)
            if args.name:
                custom.name = args.name
            repo.save_style_template(custom)
            return custom.to_dict()
        if args.action == "update":
            template = repo.get_style_template(args.id)
            if template.kind == "preset":
                raise DomainError("VALIDATION_ERROR", "preset 风格禁止修改")
            if args.name:
                template.name = args.name
            if args.prompt:
                template.prompt_text = args.prompt
            repo.save_style_template(template)
            return template.to_dict()
        if args.action == "activate":
            repo.activate_style_template(args.id)
            return repo.get_style_template(args.id).to_dict()
        if args.action == "deactivate":
            repo.deactivate_style_template(args.id)
            return repo.get_style_template(args.id).to_dict()

    # ── asset voice ──────────────────────────────────────────────────
    if args.resource == "asset" and args.subresource == "voice":
        repo = _get_asset_repository(args.data_dir)
        if args.action == "list":
            voices = repo.list_voice_assets()
            return {"items": [v.to_dict() for v in voices], "total": len(voices)}
        if args.action == "show":
            return repo.get_voice_asset(args.id).to_dict()
        if args.action == "import":
            from csboard.adapters.ffmpeg.media_adapter import FFmpegMediaAdapter
            import tempfile
            media = FFmpegMediaAdapter()
            content = args.file.read_bytes()
            ext = args.file.suffix.lower()
            tmp_path = None
            try:
                with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
                    tmp.write(content)
                    tmp_path = tmp.name
                probe = media.probe(tmp_path)
            finally:
                if tmp_path:
                    os.unlink(tmp_path)
            name = args.name or args.file.name
            asset = repo.save_voice_asset(content, name, probe.duration_ms, probe.sample_rate, probe.channels, ext.lstrip("."))
            return asset.to_dict()
        if args.action == "update":
            voice = repo.get_voice_asset(args.id)
            meta_path = repo._voice_meta_path(args.id)
            data = json.loads(meta_path.read_text(encoding="utf-8"))
            data["name"] = args.name
            meta_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            return repo.get_voice_asset(args.id).to_dict()
        if args.action == "activate":
            repo.activate_voice_asset(args.id)
            return repo.get_voice_asset(args.id).to_dict()
        if args.action == "deactivate":
            repo.deactivate_voice_asset(args.id)
            return repo.get_voice_asset(args.id).to_dict()

    # ── service ──────────────────────────────────────────────────────
    if args.resource == "service":
        from csboard.domain.service_definition import ServiceDefinition
        if args.action == "list":
            services = registry.list_services(capability=args.capability, enabled=args.enabled)
            return {"items": [s.to_dict() for s in services], "total": len(services)}
        if args.action == "show":
            return registry.get_service(args.id).to_dict()
        if args.action == "create":
            data = json.loads(args.file.read_text(encoding="utf-8"))
            service = ServiceDefinition.from_dict(data)
            return registry.create_service(service).to_dict()
        if args.action == "update":
            data = json.loads(args.file.read_text(encoding="utf-8"))
            return registry.update_service(args.id, data).to_dict()
        if args.action == "activate":
            return registry.activate_service(args.id).to_dict()
        if args.action == "deactivate":
            return registry.deactivate_service(args.id).to_dict()
        if args.action == "set-default":
            return registry.set_default(args.id).to_dict()
        if args.action == "probe":
            return registry.probe_service(args.id)
        if args.action == "secret-set":
            import getpass
            value = args.value or getpass.getpass(f"Enter secret value for {args.key}: ")
            registry.set_secret(args.id, args.key, value)
            return {"ok": True}
        if args.action == "secret-delete":
            registry.delete_secret(args.id, args.key)
            return {"ok": True}

    # ── settings ─────────────────────────────────────────────────────
    if args.resource == "settings":
        import shutil
        import subprocess
        if args.action == "toolchain":
            components = []
            for name, cmd in [("python", "python3"), ("node", "node"), ("ffmpeg", "ffmpeg"), ("ffprobe", "ffprobe")]:
                path = shutil.which(cmd)
                version = None
                if path:
                    try:
                        r = subprocess.run([path, "--version"], capture_output=True, text=True, timeout=5)
                        version = r.stdout.strip().split("\n")[0]
                    except Exception:
                        pass
                components.append({"component": name, "available": bool(path), "version": version})
            return {"items": components}
        if args.action == "storage":
            data_dir = args.data_dir
            try:
                test_file = data_dir / ".write_test"
                test_file.write_text("test", encoding="utf-8")
                test_file.unlink()
                writable = True
            except OSError:
                writable = False
            return {"writable": writable, "assets_available": (data_dir / "assets").exists()}
        if args.action == "diagnostics":
            services = registry.list_services()
            return {
                "services": [{"service_id": s.service_id, "enabled": s.enabled} for s in services],
                "toolchain": [{"component": c, "available": bool(shutil.which(c))} for c in ["python", "node", "ffmpeg", "ffprobe"]],
            }

    raise ValueError("未知命令")


def main(argv: list[str] | None = None) -> int:
    raw_args = list(sys.argv[1:] if argv is None else argv)
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
