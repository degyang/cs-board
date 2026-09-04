#!/usr/bin/env python3
"""Run every backend pytest file once, in balanced concurrent shards.

The gate shortens wall-clock time by overlapping subprocess/HTTP/file-system
waits.  It does not select individual tests, add timeouts, or permit skips.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SKIPPED = re.compile(r"\b([1-9][0-9]*) skipped\b")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the complete backend pytest gate in parallel file shards")
    parser.add_argument("--workers", type=int, default=4, choices=range(1, 9))
    args = parser.parse_args()

    test_files = sorted((PROJECT_ROOT / "tests").glob("test_*.py"))
    if not test_files:
        print("backend test gate: no test files found", file=sys.stderr)
        return 2
    shards: list[list[Path]] = [[] for _ in range(args.workers)]
    for index, test_file in enumerate(test_files):
        shards[index % args.workers].append(test_file)

    started = time.monotonic()
    processes: list[tuple[int, subprocess.Popen[str], object, Path]] = []
    with tempfile.TemporaryDirectory(prefix="csboard-pytest-gate-") as raw:
        log_dir = Path(raw)
        try:
            for index, shard in enumerate(shards):
                log_path = log_dir / f"shard-{index}.log"
                log_file = log_path.open("w", encoding="utf-8")
                command = [sys.executable, "-m", "pytest", "-q", *[str(path.relative_to(PROJECT_ROOT)) for path in shard]]
                process = subprocess.Popen(command, cwd=PROJECT_ROOT, stdout=log_file, stderr=subprocess.STDOUT, text=True)
                processes.append((index, process, log_file, log_path))
            results = []
            for index, process, log_file, log_path in processes:
                return_code = process.wait()
                log_file.close()
                output = log_path.read_text(encoding="utf-8")
                print(f"\n===== shard {index} =====")
                print(output.rstrip())
                results.append((return_code, output))
        except KeyboardInterrupt:
            for _, process, log_file, _ in processes:
                if process.poll() is None:
                    process.terminate()
                log_file.close()
            for _, process, _, _ in processes:
                process.wait()
            raise

    elapsed = time.monotonic() - started
    failed = [index for index, (return_code, _) in enumerate(results) if return_code != 0]
    skipped = sum(int(match.group(1)) for _, output in results for match in SKIPPED.finditer(output))
    print(f"\nbackend test gate: files={len(test_files)} shards={args.workers} wall_seconds={elapsed:.2f} failed_shards={failed} skipped={skipped}")
    return 1 if failed or skipped else 0


if __name__ == "__main__":
    raise SystemExit(main())
