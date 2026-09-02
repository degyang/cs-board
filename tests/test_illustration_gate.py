"""Illustration approval remains an external Codex candidate gate; no image service is invoked here."""
from csboard.domain.execution_plan import CANONICAL_STAGES


def test_illustration_stage_is_canonical_manual_gate() -> None:
    assert CANONICAL_STAGES[3] == "generate-illustrations"
