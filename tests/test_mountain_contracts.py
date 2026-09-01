from __future__ import annotations

import json
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker, RefResolver


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_DIR = ROOT / "schemas" / "mountain"
FIXTURE_DIR = ROOT / "tests" / "fixtures" / "mountain-task"

SCHEMA_FIXTURES = {
    "task.schema.json": "task.json",
    "run.schema.json": "run.json",
    "av-plan.schema.json": "av-plan.json",
    "voice-manifest.schema.json": "voice-manifest.json",
    "timeline.schema.json": "timeline.json",
    "storyboard.schema.json": "storyboard.json",
    "illustration-manifest.schema.json": "illustration-manifest.json",
    "render-manifest.schema.json": "render-manifest.json",
    "final-manifest.schema.json": "final-manifest.json",
    "domain-event.schema.json": "domain-event.json",
    "diagnostic-log.schema.json": "diagnostic-log.json",
    "audit-record.schema.json": "audit-record.json",
}


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def validator_for(schema_path: Path) -> Draft202012Validator:
    schema = load_json(schema_path)
    common = load_json(SCHEMA_DIR / "common.schema.json")
    resolver = RefResolver(
        base_uri=f"{SCHEMA_DIR.as_uri()}/",
        referrer=schema,
        store={common["$id"]: common},
    )
    return Draft202012Validator(schema, resolver=resolver, format_checker=FormatChecker())


class MountainContractTests(unittest.TestCase):
    def test_all_schemas_are_valid_draft_2020_12_documents(self) -> None:
        for schema_path in sorted(SCHEMA_DIR.glob("*.schema.json")):
            Draft202012Validator.check_schema(load_json(schema_path))

    def test_contract_fixtures_validate(self) -> None:
        for schema_name, fixture_name in SCHEMA_FIXTURES.items():
            errors = sorted(validator_for(SCHEMA_DIR / schema_name).iter_errors(load_json(FIXTURE_DIR / fixture_name)), key=str)
            self.assertEqual([], errors, f"{fixture_name} violates {schema_name}: {errors}")

    def test_av_plan_ranges_are_contiguous_and_exact(self) -> None:
        plan = load_json(FIXTURE_DIR / "av-plan.json")
        source = "".join(unit["text"] for unit in plan["voice_units"])
        cursor = 0
        for unit in plan["voice_units"]:
            self.assertEqual(cursor, unit["source_range"]["start"])
            self.assertEqual(unit["text"], source[unit["source_range"]["start"]:unit["source_range"]["end"]])
            unit_cursor = unit["source_range"]["start"]
            for visual in unit["visual_items"]:
                self.assertEqual(unit_cursor, visual["source_range"]["start"])
                self.assertEqual(visual["text"], source[visual["source_range"]["start"]:visual["source_range"]["end"]])
                unit_cursor = visual["source_range"]["end"]
            self.assertEqual(unit["source_range"]["end"], unit_cursor)
            cursor = unit_cursor
        self.assertEqual(len(source), cursor)

    def test_timeline_has_one_timing_source_per_unit_and_no_visual_gap(self) -> None:
        timeline = load_json(FIXTURE_DIR / "timeline.json")
        for unit in timeline["units"]:
            self.assertIn(unit["timing_source"], {"whisper", "equal_fallback"})
            cursor = 0
            for visual in unit["visual_timings"]:
                self.assertEqual(cursor, visual["start_ms"])
                self.assertGreater(visual["end_ms"], visual["start_ms"])
                cursor = visual["end_ms"]
            self.assertEqual(unit["duration_ms"], cursor)

    def test_timeline_rejects_unknown_timing_source(self) -> None:
        invalid = load_json(FIXTURE_DIR / "timeline.json")
        invalid["units"][0]["timing_source"] = "character_estimate"
        errors = list(validator_for(SCHEMA_DIR / "timeline.schema.json").iter_errors(invalid))
        self.assertTrue(errors)

    def test_fixtures_are_redacted_and_legacy_sample_contains_no_secret_fields(self) -> None:
        forbidden = ("api_key", "authorization", "cookie", "password", "secret", "token")
        for path in sorted((ROOT / "tests" / "fixtures").rglob("*.json")):
            payload = path.read_text(encoding="utf-8").lower()
            for field in forbidden:
                self.assertNotIn(f'"{field}"', payload, f"{path} contains forbidden field {field}")


if __name__ == "__main__":
    unittest.main()
