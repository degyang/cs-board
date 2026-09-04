from __future__ import annotations

import hashlib
import io
import json
import shutil
from pathlib import Path
from contextlib import redirect_stdout

import pytest
from starlette.testclient import TestClient

from csboard.adapters.filesystem import FilesystemTaskRepository
from csboard.domain.errors import DomainError
from webapp.mountain_server import create_app


TASK = "task-02b3a76b491445bfaf594b02c75cd70e"
RUN = "run-7d5e2a1fb3a7481a877fb53fb3aded79"
REFS = ["docs/workmates/issues/USER-TASK-PACKAGE-20260904-003.md", "docs/Mountain/23-current-delivery-status.md"]
MISSING = ["task.json", "run.json", "inputs", "21 voice units", "21 images", "21 clips", "stage/gate/trace/log evidence"]


def source(tmp_path: Path) -> tuple[Path, int, str]:
    path = tmp_path / "surviving-final.mp4"
    path.write_bytes(b"verified final\x00" * 128)
    return path, path.stat().st_size, hashlib.sha256(path.read_bytes()).hexdigest()


def do_import(repo: FilesystemTaskRepository, path: Path, size: int, digest: str) -> dict:
    return repo.import_partial_historical_final(
        task_id=TASK, run_id=RUN, source_file=path, expected_size=size,
        expected_sha256=digest, authority_refs=REFS, missing_evidence=MISSING,
    )


def test_recovery_success_list_detail_final_and_redaction(tmp_path: Path) -> None:
    path, size, digest = source(tmp_path)
    repo = FilesystemTaskRepository(tmp_path)
    result = do_import(repo, path, size, digest)
    assert result["recovery_status"] == "partial"
    assert repo.list_task_ids() == [TASK]
    assert repo.recovery_metadata(TASK)["missing_evidence"] == MISSING
    assert repo.final_path(TASK, RUN).read_bytes() == path.read_bytes()

    client = TestClient(create_app(tmp_path))
    listed = client.get("/api/v1/tasks").json()
    assert listed["items"][0]["recovery_status"] == "partial"
    detail = client.get(f"/api/v1/tasks/{TASK}").json()
    assert detail["recovery_status"] == "partial"
    assert "source_file" in detail["recovery"]
    assert str(tmp_path) not in json.dumps(detail)
    final = client.get(f"/api/v1/tasks/{TASK}/runs/{RUN}/final")
    assert final.status_code == 200
    assert final.content == path.read_bytes()


@pytest.mark.parametrize("kind", ["hash", "size", "missing"])
def test_recovery_rejects_invalid_source_without_package(tmp_path: Path, kind: str) -> None:
    path, size, digest = source(tmp_path)
    repo = FilesystemTaskRepository(tmp_path)
    if kind == "hash":
        digest = "0" * 64
    elif kind == "size":
        size += 1
    else:
        path = tmp_path / "missing.mp4"
    with pytest.raises(DomainError):
        do_import(repo, path, size, digest)
    assert repo.list_task_ids() == []


def test_recovery_is_idempotent_and_conflict_is_rejected(tmp_path: Path) -> None:
    path, size, digest = source(tmp_path)
    repo = FilesystemTaskRepository(tmp_path)
    assert do_import(repo, path, size, digest)["idempotent"] is False
    assert do_import(repo, path, size, digest)["idempotent"] is True
    with pytest.raises(DomainError) as error:
        repo.import_partial_historical_final(task_id=TASK, run_id=RUN, source_file=path, expected_size=size, expected_sha256=digest, authority_refs=["other-authority"], missing_evidence=MISSING)
    assert error.value.code == "RECOVERY_TARGET_CONFLICT"


def test_recovery_failure_rolls_back_package_and_locator(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path, size, digest = source(tmp_path)
    repo = FilesystemTaskRepository(tmp_path)
    monkeypatch.setattr(repo, "_write_package_locator", lambda *_args: (_ for _ in ()).throw(OSError("injected")))
    with pytest.raises(OSError):
        do_import(repo, path, size, digest)
    assert repo.list_task_ids() == []
    assert not (tmp_path / "outputs" / TASK).exists()
    assert not (tmp_path / "outputs" / ".csboard-staging").exists()


def test_recovery_cli_entrypoint(tmp_path: Path) -> None:
    path, size, digest = source(tmp_path)
    from cli.csboard import EXIT_OK, main
    cli_task = "task-cli-recovery-002"
    cli_run = "run-cli-recovery-002"
    output_root = Path(__file__).parents[1] / "outputs" / ".recovery-test-002"
    output = io.StringIO()
    try:
        with redirect_stdout(output):
            code = main(["--data-dir", str(tmp_path), "task", "recover", "--task", cli_task, "--run", cli_run,
                         "--source", str(path), "--size", str(size), "--sha256", digest,
                         "--output-root", str(output_root),
                         *sum((["--authority-ref", item] for item in REFS), []),
                         *sum((["--missing-evidence", item] for item in MISSING), []), "--json"])
        assert code == EXIT_OK
        assert json.loads(output.getvalue())["recovery_status"] == "partial"
    finally:
        shutil.rmtree(output_root, ignore_errors=True)
