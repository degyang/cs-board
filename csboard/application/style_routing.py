"""Deterministic reference-image routing for versioned Style snapshots."""

from __future__ import annotations

from typing import Any


def select_reference_route(config: dict[str, Any] | None, text: str) -> dict[str, Any] | None:
    routing = (config or {}).get("reference_routing")
    if not isinstance(routing, dict) or not routing.get("enabled"):
        return None
    haystack = text.casefold()
    rules = routing.get("rules")
    if not isinstance(rules, list):
        return None
    for rule in rules:
        if not isinstance(rule, dict):
            continue
        keywords = rule.get("keywords")
        asset_ids = rule.get("reference_asset_ids")
        if (isinstance(keywords, list) and isinstance(asset_ids, list) and asset_ids
                and any(isinstance(keyword, str) and keyword.casefold() in haystack for keyword in keywords)):
            return {
                "rule_id": str(rule.get("rule_id", "")),
                "name": str(rule.get("name", "")),
                "reference_asset_ids": [str(asset_id) for asset_id in asset_ids],
            }
    return None
