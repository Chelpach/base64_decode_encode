"""Base64 decode/encode tool, stdlib-only.

standalone/b64dec.py is a byte-identical copy of this file, meant to be
pasted as text into isolated environments and run as ``python3 b64dec.py``.
"""

from __future__ import annotations

import argparse
import base64
import binascii
import re
import sys
from pathlib import Path

MIME_EXTENSIONS = {
    "image/png": "png",
    "image/jpeg": "jpg",
    "image/gif": "gif",
    "image/webp": "webp",
    "application/pdf": "pdf",
    "application/zip": "zip",
    "text/plain": "txt",
}

_DATA_URL_RE = re.compile(r"^data:(?P<mime>[^;,]+)(?:;[^,]*)?,(?P<data>.*)$", re.DOTALL)
_B64_CHARS = frozenset(
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/"
)


def _normalize_mapped(raw: str) -> tuple[str, str | None, list[int]]:
    kept = [(i, ch) for i, ch in enumerate(raw) if not ch.isspace()]
    posmap = [i for i, _ in kept]
    s = "".join(ch for _, ch in kept)
    mime = None
    match = _DATA_URL_RE.match(s)
    if match:
        mime = match.group("mime").lower()
        posmap = posmap[match.start("data") :]
        s = match.group("data")
    s = s.replace("-", "+").replace("_", "/")
    s += "=" * (-len(s) % 4)
    return s, mime, posmap


def normalize_b64(raw: str) -> tuple[str, str | None]:
    s, mime, _ = _normalize_mapped(raw)
    return s, mime


def _first_invalid(s: str) -> tuple[int, str] | None:
    body = s.rstrip("=")
    for i, ch in enumerate(body):
        if ch not in _B64_CHARS:
            return i, ch
    return None


def decode_b64(raw: str) -> tuple[bytes, str | None]:
    s, mime, posmap = _normalize_mapped(raw)
    if not s.rstrip("="):
        raise ValueError("empty input")
    bad = _first_invalid(s)
    if bad is not None:
        pos, ch = bad
        raise ValueError(f"invalid base64 character {ch!r} at position {posmap[pos]}")
    try:
        return base64.b64decode(s, validate=True), mime
    except binascii.Error as exc:
        raise ValueError(f"invalid base64: {exc}") from exc


def looks_like_text(data: bytes) -> bool:
    if b"\x00" in data:
        return False
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        return False
    return all(ch.isprintable() or ch in "\t\r\n" for ch in text)


def output_path_for(mime: str | None) -> Path:
    ext = MIME_EXTENSIONS.get(mime or "", "bin")
    path = Path(f"decoded.{ext}")
    n = 1
    while path.exists():
        path = Path(f"decoded-{n}.{ext}")
        n += 1
    return path


def build_parser(prog: str | None = None) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=prog,
        description=(
            "Decode base64 (default) or encode with -e. "
            "Input: DATA argument, else --input FILE, else stdin. "
            "Output: text to stdout, binary to decoded.<ext>, or --output FILE "
            "('-' means raw stdout)."
        ),
    )
    parser.add_argument(
        "data",
        nargs="?",
        help="base64 string to decode, or text to encode with -e",
    )
    parser.add_argument(
        "-e",
        "--encode",
        action="store_true",
        help="encode mode: input is text/bytes, output is base64",
    )
    parser.add_argument(
        "-i",
        "--input",
        type=Path,
        metavar="FILE",
        help="read input from FILE (base64 text, or raw bytes with -e)",
    )
    parser.add_argument(
        "-o",
        "--output",
        metavar="FILE",
        help="write result to FILE; '-' writes raw bytes to stdout",
    )
    return parser


def _read_text(args: argparse.Namespace) -> str:
    if args.data is not None:
        return args.data
    if args.input is not None:
        return args.input.read_text(encoding="utf-8")
    if not sys.stdin.isatty():
        return sys.stdin.read()
    raise ValueError("no input: pass DATA, --input FILE, or pipe to stdin")


def _read_bytes(args: argparse.Namespace) -> bytes:
    if args.data is not None:
        return args.data.encode("utf-8")
    if args.input is not None:
        return args.input.read_bytes()
    if not sys.stdin.isatty():
        return sys.stdin.buffer.read()
    raise ValueError("no input: pass DATA, --input FILE, or pipe to stdin")


def _run_decode(args: argparse.Namespace) -> int:
    data, mime = decode_b64(_read_text(args))
    if args.output == "-":
        sys.stdout.buffer.write(data)
        return 0
    if args.output is not None:
        Path(args.output).write_bytes(data)
        return 0
    if looks_like_text(data):
        sys.stdout.buffer.write(data)
        return 0
    path = output_path_for(mime)
    path.write_bytes(data)
    print(f"binary output written to {path}", file=sys.stderr)
    return 0


def _run_encode(args: argparse.Namespace) -> int:
    data = _read_bytes(args)
    if not data:
        raise ValueError("empty input")
    out = base64.b64encode(data).decode("ascii") + "\n"
    if args.output is not None and args.output != "-":
        Path(args.output).write_text(out, encoding="ascii")
        return 0
    sys.stdout.write(out)
    return 0


def main(argv: list[str] | None = None, prog: str | None = None) -> int:
    parser = build_parser(prog)
    args = parser.parse_args(argv)
    if args.data is not None and args.input is not None:
        parser.error("pass either DATA or --input FILE, not both")
    try:
        if args.encode:
            return _run_encode(args)
        return _run_decode(args)
    except (ValueError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
