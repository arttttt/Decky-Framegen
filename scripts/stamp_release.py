#!/usr/bin/env python3
"""Turn a checkout into a release build before `decky plugin build`.

Names the release by the day (framegen.domain.release_version), writes that version into
package.json, and prints `version=` and `tag=` lines for $GITHUB_OUTPUT. A release build carries no
development identity, so its Developer section stays hidden.

    python3 scripts/stamp_release.py [--existing-tag <tag> ...]
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "py_modules"))

from framegen.domain import release_version  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--existing-tag", action="append", default=[], help="a tag the repository already has")
    parser.add_argument("--date", type=date.fromisoformat, help="the release day (default: today, UTC)")
    parser.add_argument("--root", type=Path, default=REPO_ROOT, help="plugin checkout to stamp")
    args = parser.parse_args(argv)

    today = args.date or datetime.now(timezone.utc).date()
    version = release_version.next_release(today, args.existing_tag)
    package_path = args.root / "package.json"
    package = json.loads(package_path.read_text(encoding="utf-8"))
    package["version"] = version
    package_path.write_text(json.dumps(package, indent=2) + "\n", encoding="utf-8")

    print(f"version={version}")
    print(f"tag={release_version.tag(version)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
