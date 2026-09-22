"""Fail CI when mypy reports an error that is not already baselined.

Predictor and cogitomedica fail on any mypy error. This tree still has a known
set, so the gate blocks new findings until that set is empty. Fixing an old
error does not require editing the baseline.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASELINE = ROOT / "mypy-baseline.txt"
ERROR_RE = re.compile(r"^(?P<path>.+?):\d+: (?P<message>error: .+)$")


def normalize(line: str) -> str | None:
    match = ERROR_RE.match(line.strip())
    if not match:
        return None
    path = match.group("path").replace("\\", "/")
    return f"{path}: {match.group('message')}"


def load_baseline() -> set[str]:
    if not BASELINE.exists():
        raise FileNotFoundError(f"Missing {BASELINE.name}. Regenerate it from mypy src.")
    allowed: set[str] = set()
    for line in BASELINE.read_text(encoding="utf-8").splitlines():
        stripped = line.strip().replace("\\", "/")
        if stripped and not stripped.startswith("#"):
            allowed.add(stripped)
    return allowed


def main() -> int:
    completed = subprocess.run(
        [sys.executable, "-m", "mypy", "src"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    output = f"{completed.stdout}\n{completed.stderr}"
    current = {item for line in output.splitlines() if (item := normalize(line))}

    if completed.returncode not in (0, 1):
        sys.stderr.write(output)
        return completed.returncode or 1

    new_errors = sorted(current - load_baseline())
    if new_errors:
        sys.stderr.write("New mypy errors (not in mypy-baseline.txt):\n")
        sys.stderr.write("\n".join(new_errors))
        sys.stderr.write("\n")
        return 1

    print(f"mypy baseline ok ({len(current)} known errors)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
