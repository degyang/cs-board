from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LINTER = ROOT / "scripts" / "validate_skill_contracts.py"


def test_skill_contract_linter_accepts_repository_skills() -> None:
    result = subprocess.run([sys.executable, str(LINTER)], cwd=ROOT, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert "passed" in result.stdout


def test_skill_contract_linter_rejects_legacy_fixture() -> None:
    fixture = ROOT / "tests" / "fixtures" / "skill-contracts" / "bad"
    result = subprocess.run([sys.executable, str(LINTER), "--skills-root", str(fixture)], cwd=ROOT, capture_output=True, text=True)
    assert result.returncode != 0
    assert "forbidden legacy token --reference" in result.stderr


def test_skill_contract_linter_rejects_visual_anchor_self_cycle() -> None:
    fixture = ROOT / "tests" / "fixtures" / "skill-contracts" / "self-cycle"
    result = subprocess.run([sys.executable, str(LINTER), "--skills-root", str(fixture)], cwd=ROOT, capture_output=True, text=True)
    assert result.returncode != 0
    assert "input declaration missing script_preparation" in result.stderr


def test_skill_contract_linter_rejects_unimplemented_illustration_retry() -> None:
    fixture = ROOT / "tests" / "fixtures" / "skill-contracts" / "unimplemented-retry"
    result = subprocess.run([sys.executable, str(LINTER), "--skills-root", str(fixture)], cwd=ROOT, capture_output=True, text=True)
    assert result.returncode != 0
    assert "must not advertise retry" in result.stderr
