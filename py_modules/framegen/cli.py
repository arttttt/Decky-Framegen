"""Command-line entry for the ~/fgmod launch wrappers.

`python3 -m framegen patch|unpatch -- <command>` prints the patched (or
unpatched) game directory; on failure it prints the message for the user and
exits with 1. `wine-overrides` prints WINEDLLOVERRIDES with the proxy added.
Logs go to stderr.
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path

from framegen.application.launch_wrapper import LaunchWrapper, WrapperError
from framegen.domain import bundle, launch_options


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python3 -m framegen")
    commands = parser.add_subparsers(dest="action", required=True)
    patch = commands.add_parser("patch", help="patch the game a launch command starts")
    patch.add_argument("--dll", default=bundle.DEFAULT_PROXY_DLL, help="proxy DLL name")
    patch.add_argument("--version", default="", help="library version id, e.g. nightly-20261023 (default: the default version)")
    patch.add_argument("--variant", default="", help="FSR 4 variant of that version (default: its family's default)")
    patch.add_argument("--reset-ini", action="store_true", help="replace the game's OptiScaler.ini")
    commands.add_parser("unpatch", help="unpatch the game a launch command starts")
    for name in ("patch", "unpatch"):
        commands.choices[name].add_argument("command", nargs=argparse.REMAINDER, help="-- followed by the launch command")
    overrides = commands.add_parser("wine-overrides", help="print WINEDLLOVERRIDES with the proxy's entry added")
    overrides.add_argument("--dll", default=bundle.DEFAULT_PROXY_DLL, help="proxy DLL name")
    return parser


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(stream=sys.stderr, level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    args = _parser().parse_args(argv)
    if args.action == "wine-overrides":
        print(launch_options.wine_dll_overrides(os.environ.get("WINEDLLOVERRIDES", ""), args.dll))
        return 0
    command = args.command[1:] if args.command[:1] == ["--"] else args.command
    if not command:
        print("Usage: <wrapper> program [program_arguments...]")
        return 1
    wrapper = LaunchWrapper(Path(os.environ["HOME"]), os.environ)
    try:
        if args.action == "patch":
            directory = wrapper.patch(command, args.dll, args.variant, version_id=args.version, reset_ini=args.reset_ini)
        else:
            directory = wrapper.unpatch(command)
    except WrapperError as exc:
        print(exc)
        return 1
    print(directory)
    return 0
