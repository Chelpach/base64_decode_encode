import base64
import io
import subprocess
import sys
from pathlib import Path

import pytest

from opencode_test.b64 import decode_b64, looks_like_text, main, normalize_b64
from opencode_test.cli import main as cli_main

ROOT = Path(__file__).resolve().parents[1]


class _TtyIn:
    def isatty(self) -> bool:
        return True

    def read(self, *args, **kwargs):
        raise AssertionError("stdin must not be read")


def test_normalize_strips_whitespace_and_fixes_padding():
    assert normalize_b64(" aGVs\nbG8\t") == ("aGVsbG8=", None)


def test_normalize_unifies_urlsafe_alphabet():
    assert normalize_b64("-/8")[0] == "+/8="


def test_normalize_data_url_extracts_mime():
    s, mime = normalize_b64("data:image/png;base64,iVBORw0KGgo=")
    assert mime == "image/png"
    assert s == "iVBORw0KGgo="


def test_normalize_data_url_with_charset():
    s, mime = normalize_b64("data:text/plain;charset=utf-8;base64,aGk=")
    assert mime == "text/plain"
    assert s == "aGk="


def test_decode_b64_roundtrip_bytes():
    data, mime = decode_b64(base64.b64encode(b"hi \xfb\xff").decode())
    assert data == b"hi \xfb\xff"
    assert mime is None


def test_looks_like_text():
    assert looks_like_text("привет, мир!\n".encode())
    assert not looks_like_text(b"\x00\x01")
    assert not looks_like_text(b"\xff\xfe")
    assert not looks_like_text(b"a\x1bb")


def test_decode_text_to_stdout_exact_bytes(capsysbinary):
    assert main(["aGVsbG8sIHdvcmxkIQ=="]) == 0
    assert capsysbinary.readouterr().out == b"hello, world!"


def test_decode_from_stdin(monkeypatch, capsysbinary):
    monkeypatch.setattr(sys, "stdin", io.StringIO("aGVs\nbG8="))
    assert main([]) == 0
    assert capsysbinary.readouterr().out == b"hello"


def test_decode_from_input_file(tmp_path, capsysbinary):
    src = tmp_path / "encoded.txt"
    src.write_text("aGVsbG8=", encoding="utf-8")
    assert main(["-i", str(src)]) == 0
    assert capsysbinary.readouterr().out == b"hello"


def test_decode_binary_auto_file(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    payload = b"\x89PNG\x00\x01\x02"
    assert main([base64.b64encode(payload).decode()]) == 0
    captured = capsys.readouterr()
    assert (tmp_path / "decoded.bin").read_bytes() == payload
    assert "decoded.bin" in captured.err


def test_decode_binary_auto_name_from_mime(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    payload = b"\x89PNG\x00\x01\x02"
    arg = f"data:image/png;base64,{base64.b64encode(payload).decode()}"
    assert main([arg]) == 0
    assert (tmp_path / "decoded.png").read_bytes() == payload


def test_decode_binary_auto_name_collision(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "decoded.bin").write_bytes(b"old")
    payload = b"\x00\x01"
    assert main([base64.b64encode(payload).decode()]) == 0
    assert (tmp_path / "decoded-1.bin").read_bytes() == payload


def test_decode_output_file(tmp_path):
    out = tmp_path / "out.txt"
    assert main(["aGVsbG8=", "-o", str(out)]) == 0
    assert out.read_bytes() == b"hello"


def test_decode_output_dash_raw_stdout(capsysbinary):
    payload = b"\x00\x01\x02"
    assert main([base64.b64encode(payload).decode(), "-o", "-"]) == 0
    assert capsysbinary.readouterr().out == payload


def test_decode_invalid_character(capsys):
    assert main(["aGVs!bG8="]) == 1
    err = capsys.readouterr().err
    assert "invalid base64 character '!'" in err
    assert "position 4" in err


def test_decode_empty_input(capsys):
    assert main(["  "]) == 1
    assert "empty input" in capsys.readouterr().err


def test_decode_no_input(monkeypatch, capsys):
    monkeypatch.setattr(sys, "stdin", _TtyIn())
    assert main([]) == 1
    assert "no input" in capsys.readouterr().err


def test_data_and_input_conflict_exits_2(tmp_path):
    with pytest.raises(SystemExit) as exc:
        main(["aGVsbG8=", "-i", str(tmp_path / "x.txt")])
    assert exc.value.code == 2


def test_encode_text_argument(capsys):
    assert main(["-e", "hello, world!"]) == 0
    assert capsys.readouterr().out == "aGVsbG8sIHdvcmxkIQ==\n"


def test_encode_from_stdin(monkeypatch, capsys):
    monkeypatch.setattr(sys, "stdin", io.TextIOWrapper(io.BytesIO(b"hi")))
    assert main(["-e"]) == 0
    assert capsys.readouterr().out == "aGk=\n"


def test_encode_from_input_file(tmp_path, capsys):
    src = tmp_path / "raw.bin"
    src.write_bytes(b"hi")
    assert main(["-e", "-i", str(src)]) == 0
    assert capsys.readouterr().out == "aGk=\n"


def test_encode_to_file(tmp_path):
    out = tmp_path / "encoded.txt"
    assert main(["-e", "hi", "-o", str(out)]) == 0
    assert out.read_text(encoding="ascii") == "aGk=\n"


def test_encode_empty_input(capsys):
    assert main(["-e", ""]) == 1
    assert "empty input" in capsys.readouterr().err


def test_round_trip_encode_decode(capsysbinary):
    assert main(["-e", "привет"]) == 0
    encoded = capsysbinary.readouterr().out.decode().strip()
    assert main([encoded]) == 0
    assert capsysbinary.readouterr().out == "привет".encode()


def test_standalone_copy_is_in_sync():
    core = (ROOT / "src" / "opencode_test" / "b64.py").read_bytes()
    standalone = (ROOT / "standalone" / "b64dec.py").read_bytes()
    assert standalone == core


def test_standalone_runs_as_file(tmp_path):
    script = ROOT / "standalone" / "b64dec.py"
    proc = subprocess.run(
        [sys.executable, str(script), "aGVsbG8="],
        capture_output=True,
        cwd=tmp_path,
    )
    assert proc.returncode == 0
    assert proc.stdout == b"hello"

    payload = b"\x89PNG\x00\x01"
    arg = f"data:image/png;base64,{base64.b64encode(payload).decode()}"
    proc = subprocess.run(
        [sys.executable, str(script), arg],
        capture_output=True,
        cwd=tmp_path,
    )
    assert proc.returncode == 0
    assert (tmp_path / "decoded.png").read_bytes() == payload


def test_cli_b64_subcommand(capsysbinary):
    assert cli_main(["b64", "aGVsbG8="]) == 0
    assert capsysbinary.readouterr().out == b"hello"


def test_cli_b64_subcommand_with_options(capsys):
    assert cli_main(["b64", "-e", "hi"]) == 0
    assert capsys.readouterr().out == "aGk=\n"
