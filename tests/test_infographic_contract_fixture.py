"""P1 golden fixture compatibility checks for DynamicInfographicProps v1."""

from __future__ import annotations

import json
from pathlib import Path


def test_remotion_smoke_props_fixture_is_complete_v1_contract() -> None:
    value = json.loads((Path(__file__).parent / "fixtures" / "remotion-smoke-props.json").read_text(encoding="utf-8"))
    assert value["schemaVersion"] == 1
    assert {"fps", "width", "height", "totalDurationMs", "totalDurationFrames", "style", "pages"} <= value.keys()
    page = value["pages"][0]
    assert {"id", "image", "startFrame", "endFrame", "seriesTitle", "chapterTitle", "pageTitle", "layoutType", "composition", "slideRole", "relationshipType", "coreIdea", "visualStrategy", "narrativeLink", "nodes", "conclusion", "cues", "seriesPersistent", "chapterPersistent"} <= page.keys()
    assert page["startFrame"] < page["endFrame"] <= value["totalDurationFrames"]
