#!/usr/bin/env python3
"""Turn a checkout into a release build before `decky plugin build`.

Names the release by the day (framegen.domain.release_version), writes that version into
package.json and the build's identity on the stable channel into `defaults/build-info.json` (so the
release knows where its updates are published), and prints `version=`, `tag=` and `channel=` lines for
$GITHUB_OUTPUT.

    python3 scripts/stamp_release.py --repository <owner/name> --commit <sha> [--existing-tag <tag> ...]
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "py_modules"))

from framegen.domain import dev_build, release_version  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--repository", required=True, help="owner/name of the repository being released")
    parser.add_argument("--commit", required=True, help="full sha of the commit being released")
    parser.add_argument("--existing-tag", action="append", default=[], help="a tag the repository already has")
    parser.add_argument("--date", type=date.fromisoformat, help="the release day (default: today, UTC)")
    parser.add_argument("--root", type=Path, default=REPO_ROOT, help="plugin checkout to stamp")
    args = parser.parse_args(argv)

    today = args.date or datetime.now(timezone.utc).date()
    version = release_version.next_release(today, args.existing_tag)
    try:
        info = dev_build.build_info(args.repository, dev_build.STABLE_CHANNEL, args.commit, version=version)
    except ValueError as exc:
        parser.error(str(exc))
    package_path = args.root / "package.json"
    package = json.loads(package_path.read_text(encoding="utf-8"))
    package["version"] = version
    package_path.write_text(json.dumps(package, indent=2) + "\n", encoding="utf-8")
    (args.root / "defaults").mkdir(exist_ok=True)
    (args.root / "defaults" / dev_build.BUILD_INFO_FILENAME).write_text(dev_build.to_json(info), encoding="utf-8")

    print(f"version={version}")
    print(f"tag={release_version.tag(version)}")
    print(f"channel={info.channel}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
