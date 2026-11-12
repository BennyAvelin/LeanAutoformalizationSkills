#!/usr/bin/env python3
"""Extract Lake build-action elapsed times; these are not CPU measurements."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re


ANSI = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")
BUILT = re.compile(
    r"^\s*(?:[✔⚠ℹ✖]\s+)?\[[0-9]+/[0-9]+\]\s+"
    r"(?:\(Optional\)\s+)?Built\s+(?P<target>[^\s()]+)"
    r"(?:\s+\((?P<time>[0-9]+(?:\.[0-9]+)?)(?P<unit>ms|s)\))?\s*$"
)


def parse_timings(log: str, roots: tuple[str, ...] = ()) -> dict:
    """Preserve each build action, including repeated or untimed actions.

    A root includes its exact caption, submodules, and colon-qualified facets.
    It never includes another namespace that merely shares its name prefix.
    """
    actions = []
    for line in ANSI.sub("", log).splitlines():
        match = BUILT.search(line)
        if match is None:
            continue
        target = match["target"]
        if roots and not any(target == root or target.startswith((root + ".", root + ":"))
                             for root in roots):
            continue
        seconds = None
        if match["time"] is not None:
            seconds = float(match["time"])
            if match["unit"] == "ms":
                seconds /= 1000
        actions.append({"target": target, "elapsed_seconds": seconds})
    timed = [entry for entry in actions if entry["elapsed_seconds"] is not None]
    return {
        "build_actions": len(actions),
        "timed_build_actions": len(timed),
        "untimed_build_actions": len(actions) - len(timed),
        "sum_elapsed_seconds": sum(entry["elapsed_seconds"] for entry in timed),
        "actions": actions,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("log", type=Path)
    parser.add_argument("--root-module", action="append", default=[],
                        help="project root module; repeat for multiple libraries")
    args = parser.parse_args()
    try:
        report = parse_timings(args.log.read_text(encoding="utf-8"), tuple(args.root_module))
    except (OSError, UnicodeError) as error:
        parser.exit(2, f"cannot read build log: {error}\n")
    if not report["build_actions"]:
        parser.exit(2, "no matching Built actions; check the log format and root modules\n")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
