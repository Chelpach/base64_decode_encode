import argparse
import sys

from opencode_test import __version__
from opencode_test.b64 import main as b64_main


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="opencode-test",
        description="Small demo CLI: greet, version and b64 commands",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    greet = subparsers.add_parser("greet", help="print a greeting")
    greet.add_argument("name", nargs="?", default="world", help="who to greet")

    subparsers.add_parser("version", help="print the package version")

    b64 = subparsers.add_parser(
        "b64",
        help="decode/encode base64 (same interface as standalone/b64dec.py)",
    )
    b64.add_argument("b64_args", nargs=argparse.REMAINDER, help=argparse.SUPPRESS)

    return parser


def main(argv: list[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv[1:]
    if argv and argv[0] == "b64":
        return b64_main(argv[1:], prog="opencode-test b64")

    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "greet":
        print(f"Hello, {args.name}!")
    else:
        print(__version__)
    return 0


def console_main() -> None:
    raise SystemExit(main())
