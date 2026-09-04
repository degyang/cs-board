#!/usr/bin/env python3
"""Preflight validation for COMMIT-SPLIT-EXECUTION.

Checks:
1. Every file path in the plan exists on disk
2. No archive/reference files in feature commits
3. No outputs/ files in any commit
4. No duplicate test ownership across commits
5. .gitignore additions are safe
"""
import os
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

ARCHIVE_FILES = {
    "webapp/server.py",
    "webapp/mountain_api.py",
    "webapp/mountain_stages.py",
    "webapp/mountain_v1_api.py",
    "tests/test_mountain_api.py",
}

OUTPUTS_PREFIX = "outputs/"

# Commit definitions: (number, message, files)
COMMITS = [
    (1, "feat(domain): add voice_asset, precondition, style_routing domain modules", [
        "csboard/domain/voice_asset.py",
        "csboard/domain/precondition.py",
        "csboard/domain/style_template.py",
        "csboard/domain/provider_types.py",
        "csboard/domain/script_preparation.py",
        "tests/test_script_preparation.py",
        "tests/test_storyboard.py",
    ]),
    (2, "feat(backend): rewrite asset repository and ports for persistence", [
        "csboard/ports/asset_repository.py",
        "csboard/adapters/filesystem/asset_repository.py",
        "csboard/adapters/filesystem/repository.py",
        "csboard/application/preset_catalog.py",
        "csboard/application/migrated_asset_catalog.py",  # NEW
        "csboard/application/style_routing.py",  # NEW
        "csboard/application/precondition_catalog.py",  # NEW
        "csboard/application/illustration_candidates.py",  # NEW
        "tests/test_asset_repository.py",
        "tests/test_migrated_asset_catalog.py",
        "tests/test_mountain_asset_api.py",
    ]),
    (3, "fix(backend): service registry auto-populate required_secrets", [
        "csboard/adapters/filesystem/service_registry.py",
        "tests/test_service_registry.py",
        "tests/test_mountain_service_api.py",
        "tests/test_secret_security.py",
        "tests/test_service_resolver.py",
    ]),
    (4, "feat(backend): application orchestration with co-located tests", [
        "csboard/application/commands.py",
        "csboard/application/composition.py",
        "csboard/application/illustrations.py",
        "csboard/application/voice_units.py",
        "csboard/application/work_orders.py",
        "csboard/application/storyboard.py",
        "tests/test_task_create_contract_30.py",
        "tests/test_task_execution_plan_23.py",
        "tests/test_stage_entry_contract_27.py",
        "tests/test_stage_entry_contract_28.py",
        "tests/test_stage_gates_24.py",
        "tests/test_stage_work_orders.py",
        "tests/test_input_transaction_11.py",
        "tests/test_whisper_adapter.py",
        "tests/test_composition_service.py",
        "tests/test_illustrations.py",
        "tests/test_task_recovery_002.py",
        "tests/test_task_package_backend_001.py",
    ]),
    (5, "fix(backend): adapter updates (whisper, whiteboard, openai, provider_factory)", [
        "csboard/adapters/whisper/alignment_adapter.py",
        "csboard/adapters/whiteboard/renderer_adapter.py",
        "csboard/adapters/openai_compatible/image_adapter.py",
        "csboard/adapters/provider_factory.py",
        "tests/test_openai_image_adapter.py",
        "tests/test_whiteboard_renderer_adapter.py",
        "tests/test_dynamic_provider_factory.py",
    ]),
    (6, "feat(backend): update active webapp API routes", [
        "webapp/error_contract.py",
        "webapp/mountain_server.py",
        "webapp/mountain_task_api.py",
        "webapp/mountain_asset_api.py",
        "webapp/mountain_capability_api.py",
        "webapp/mountain_service_api.py",
        "webapp/mountain_settings_api.py",
        "tests/test_mountain_server.py",
        "tests/test_mountain_bootstrap.py",
        "tests/test_mountain_contracts.py",
        "tests/test_mountain_settings_api.py",
        "tests/test_mountain_precondition_api.py",
        "tests/test_port_conformance.py",
        "tests/test_backend_runtime_17.py",
        "tests/test_legacy_isolation.py",
        "tests/test_m07_pr1c_acceptance.py",
        "tests/test_output_directory_picker_backend_002.py",
        "tests/test_workmates_release_guard.py",
    ]),
    (7, "feat(backend): update CLI and webapp entry points", [
        "cli/csboard.py",
        "start-webapp.py",
        "video_renderer/align.mjs",
        "tests/test_cli_csboard.py",
    ]),
    (8, "feat(frontend): asset management, voice page, sidebar/nav, styles", [
        "web-v2/src/app/router.tsx",
        "web-v2/src/components/layout/Sidebar.tsx",
        "web-v2/src/lib/api/assets.ts",
        "web-v2/src/lib/api/client.ts",
        "web-v2/src/lib/api/http.ts",
        "web-v2/src/lib/api/types.ts",
        "web-v2/src/pages/AssetManagementPage.tsx",
        "web-v2/src/pages/VoiceManagementPage.tsx",  # NEW
        "web-v2/src/pages/VoiceAlignmentPage.tsx",
        "web-v2/src/styles/app.css",
        "web-v2/src/styles/assets.css",
        "web-v2/tests/assets-contract.test.tsx",
        "web-v2/tests/sidebar-layout.test.tsx",
        "web-v2/tests/preset-browser.test.tsx",
        "web-v2/tests/http-assets.test.ts",
        "web-v2/tests/output-directory-picker.test.tsx",
    ]),
    (9, "feat(frontend): model services API key conditional display", [
        "web-v2/src/pages/ModelServicesPage.tsx",
        "web-v2/src/pages/ServiceFormPage.tsx",
        "web-v2/tests/services-contract.test.tsx",
    ]),
    (10, "feat(frontend): create-task page updates", [
        "web-v2/src/pages/CreateTaskPage.tsx",
        "web-v2/tests/create-task.test.tsx",
        "web-v2/tests/race-condition.test.tsx",
    ]),
    (11, "docs(mountain): update delivery status, decisions, skills, workmates", [
        "docs/Mountain/04-webui-redesign.md",
        "docs/Mountain/05-skills-design.md",
        "docs/Mountain/08-decisions.md",
        "docs/Mountain/14-task-and-script-preparation.md",
        "docs/Mountain/15-production-control-and-style-assets.md",
        "docs/Mountain/23-current-delivery-status.md",
        "docs/Mountain/README.md",
        "docs/Mountain/28-domain-extraction-and-character-assets-roadmap.md",  # NEW
        "skills/av-compositor/SKILL.md",
        "skills/illustration-generator/SKILL.md",
        "skills/storyboard-planner/SKILL.md",
        "skills/video-workflow/SKILL.md",
        "skills/visual-renderer/SKILL.md",
        "skills/voice-cloner/SKILL.md",
        "skills/visual-anchor-generator/SKILL.md",
        "skills/script-segmenter/SKILL.md",
    ]),
    (12, "chore(ops): add scripts, agent config, assets seed", [
        "scripts/render_stream_whiteboard.py",
        "scripts/restart_backend_when_idle.ps1",
        "scripts/run_mountain_backend.py",
        "scripts/legacy_dependency_guard.py",  # NEW
        "scripts/run_backend_test_gate.py",  # NEW
        "scripts/workmates_release_guard.py",  # NEW
        "assets/seed-voices",
    ]),
    (13, "chore(gitignore): add outputs/ to .gitignore", [
        ".gitignore",
    ]),
]


def check_file_exists(path):
    """Accept a working-tree path or a tracked deletion planned for this split."""
    full = ROOT / path
    if full.exists():
        return True
    tracked = subprocess.run(
        ["git", "ls-files", "--error-unmatch", "--", path],
        cwd=ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return tracked.returncode == 0


def main():
    errors = []
    warnings = []
    all_files = []
    test_ownership = defaultdict(list)  # test_file -> [commit_numbers]

    for num, msg, files in COMMITS:
        for f in files:
            # 1. Check archive files not in feature commits
            if f in ARCHIVE_FILES:
                errors.append(f"Commit #{num}: archive file '{f}' must not be committed")

            # 2. Check no outputs/
            if f.startswith(OUTPUTS_PREFIX):
                errors.append(f"Commit #{num}: outputs/ file '{f}' must not be committed")

            # 3. Track test ownership
            if f.startswith("tests/") or f.startswith("web-v2/tests/"):
                test_ownership[f].append(num)

            # 4. Check file exists (warn if not)
            if not check_file_exists(f):
                warnings.append(f"Commit #{num}: file not found on disk: '{f}' (may be NEW/untracked)")

            all_files.append((num, f))

    # 5. Check duplicate test ownership
    for test_file, commits in sorted(test_ownership.items()):
        if len(commits) > 1:
            errors.append(f"Duplicate ownership: '{test_file}' appears in commits {commits}")

    # 6. Check .gitignore
    gitignore = ROOT / ".gitignore"
    if gitignore.exists():
        content = gitignore.read_text()
        if not any(line.strip() == "outputs/" for line in content.splitlines()):
            warnings.append(".gitignore does not contain 'outputs/' — commit #13 will add it")
        elif subprocess.run(
            ["git", "diff", "--quiet", "--", ".gitignore"], cwd=ROOT
        ).returncode == 0:
            warnings.append(".gitignore already contains an exact root 'outputs/' rule — commit #13 may be no-op")

    # 7. Count commits
    if len(COMMITS) != 13:
        errors.append(f"Expected 13 commits, found {len(COMMITS)}")

    # Report
    print("=" * 60)
    print("PREFLIGHT VALIDATION")
    print("=" * 60)

    if errors:
        print(f"\n❌ {len(errors)} ERRORS:")
        for e in errors:
            print(f"  - {e}")
    else:
        print("\n✅ No errors")

    if warnings:
        print(f"\n⚠️  {len(warnings)} WARNINGS:")
        for w in warnings:
            print(f"  - {w}")

    print(f"\nTotal files: {len(all_files)}")
    print(f"Total commits: {len(COMMITS)}")

    # Summary by commit
    print("\nPer-commit file count:")
    for num, msg, files in COMMITS:
        tests = [f for f in files if f.startswith("tests/") or f.startswith("web-v2/tests/")]
        sources = [f for f in files if not (f.startswith("tests/") or f.startswith("web-v2/tests/"))]
        print(f"  #{num:2d}: {len(sources):2d} source + {len(tests):2d} test = {len(files):2d} files")

    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
