"""Command-line entry for the ~/fgmod launch wrappers: `python3 -m framegen patch|unpatch -- <command>`.

On success the patched (or unpatched) game directory is printed; on failure the
message for the user is printed and the exit code is 1. Logs go to stderr.
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path

from framegen.application.launch_wrapper import LaunchWrapper, WrapperError


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python3 -m framegen")
    commands = parser.add_subparsers(dest="action", required=True)
    patch = commands.add_parser("patch", help="patch the game a launch command starts")
    patch.add_argument("--dll", default="dxgi.dll", help="proxy DLL name")
    patch.add_argument("--variant", default="", help="FSR4 runtime variant (default: the bundle's)")
    patch.add_argument("--reset-ini", action="store_true", help="replace the game's OptiScaler.ini")
    commands.add_parser("unpatch", help="unpatch the game a launch command starts")
    for command in commands.choices.values():
        command.add_argument("command", nargs=argparse.REMAINDER, help="-- followed by the launch command")
    return parser


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(stream=sys.stderr, level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    args = _parser().parse_args(argv)
    command = args.command[1:] if args.command[:1] == ["--"] else args.command
    if not command:
        print("Usage: <wrapper> program [program_arguments...]")
        return 1
    wrapper = LaunchWrapper(Path(os.environ["HOME"]), os.environ)
    try:
        if args.action == "patch":
            directory = wrapper.patch(command, args.dll, args.variant, reset_ini=args.reset_ini)
        else:
            directory = wrapper.unpatch(command)
    except WrapperError as exc:
        print(exc)
        return 1
    print(directory)
    return 0
