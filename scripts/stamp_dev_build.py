#!/usr/bin/env python3
"""Turn a checkout into a development build before `decky plugin build`.

Writes `defaults/build-info.json` (Decky CLI ships defaults/ at the plugin root)
and the matching version into package.json, then prints `channel=`, `version=`
and `asset=` lines for $GITHUB_OUTPUT. Release builds skip this script and carry
no identity.

    python3 scripts/stamp_dev_build.py --repository <owner/name> --commit <sha> [--pull-request <N>]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "py_modules"))

from framegen.domain import dev_build  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--repository", required=True, help="owner/name of the repository being built")
    parser.add_argument("--commit", required=True, help="full sha of the commit being built")
    parser.add_argument("--pull-request", type=int, help="number of the pull request being built; none for main")
    parser.add_argument("--root", type=Path, default=REPO_ROOT, help="plugin checkout to stamp")
    args = parser.parse_args(argv)

    try:
        info = dev_build.build_info(args.repository, dev_build.channel(args.pull_request), args.commit)
    except ValueError as exc:
        parser.error(str(exc))

    package_path = args.root / "package.json"
    package = json.loads(package_path.read_text(encoding="utf-8"))
    package["version"] = dev_build.version(package["version"], info)
    package_path.write_text(json.dumps(package, indent=2) + "\n", encoding="utf-8")
    (args.root / "defaults" / dev_build.BUILD_INFO_FILENAME).write_text(dev_build.to_json(info), encoding="utf-8")

    plugin_name = json.loads((args.root / "plugin.json").read_text(encoding="utf-8"))["name"]
    print(f"channel={info.channel}")
    print(f"version={package['version']}")
    print(f"asset={dev_build.asset_name(plugin_name, info)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
