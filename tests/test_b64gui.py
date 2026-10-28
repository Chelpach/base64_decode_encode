import base64
import importlib.util
import sys
from pathlib import Path

import pytest

tkinter = pytest.importorskip("tkinter")

ROOT = Path(__file__).resolve().parents[1]
GUI_PATH = ROOT / "ui-tkinter" / "b64gui.py"


def _load():
    spec = importlib.util.spec_from_file_location("b64gui_test", GUI_PATH)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["b64gui_test"] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def gui():
    return _load()


@pytest.fixture()
def app(gui):
    try:
        root = tkinter.Tk()
    except tkinter.TclError:
        pytest.skip("no display")
    root.withdraw()
    instance = gui.App(root)
    yield instance
    root.destroy()


def test_encode_text(gui):
    out = gui.encode_payload("hi", None)
    assert out.ok
    assert out.display == "aGk="
    assert out.payload == b"aGk="
    assert out.filename == "encoded.txt"


def test_encode_binary(gui):
    out = gui.encode_payload("", b"\xfb\xff")
    assert out.ok
    assert out.display == base64.b64encode(b"\xfb\xff").decode()
    assert out.filename == "encoded.txt"


def test_encode_empty(gui):
    out = gui.encode_payload("", None)
    assert not out.ok
    assert out.message == "Ошибка: пустой ввод"
    assert out.payload is None


def test_decode_text(gui):
    out = gui.decode_payload("aGVsbG8=", None)
    assert out.ok
    assert out.display == "hello"
    assert out.payload == b"hello"
    assert out.filename == "decoded.txt"


def test_decode_text_with_mime(gui):
    arg = "data:text/plain;charset=utf-8;base64,aGk="
    out = gui.decode_payload(arg, None)
    assert out.ok
    assert out.display == "hi"
    assert out.filename == "decoded.txt"


def test_decode_binary_png(gui):
    payload = b"\x89PNG\x00\x01"
    arg = f"data:image/png;base64,{base64.b64encode(payload).decode()}"
    out = gui.decode_payload(arg, None)
    assert out.ok
    assert out.is_binary
    assert out.payload == payload
    assert out.filename == "decoded.png"
    assert str(len(payload)) in out.display
    assert "image/png" in out.display


def test_decode_invalid(gui):
    out = gui.decode_payload("aGVs!bG8=", None)
    assert not out.ok
    assert "invalid base64 character" in out.message


def test_decode_rejects_binary_input(gui):
    out = gui.decode_payload("aGVsbG8=", b"\x00")
    assert not out.ok
    assert "base64-текст" in out.message


def test_classify_input_text(gui):
    out = gui.classify_input("привет".encode(), "a.txt")
    assert out.ok
    assert not out.is_binary
    assert out.display == "привет"


def test_classify_input_binary(gui):
    data = b"\x89PNG\x00"
    out = gui.classify_input(data, "img.png")
    assert out.ok
    assert out.is_binary
    assert out.payload == data
    assert "img.png" in out.display


def test_app_encode_decode_roundtrip(app):
    app.input_text.insert("1.0", "hi")
    app.on_encode()
    assert app._result.display == "aGk="
    app.input_text.delete("1.0", "end")
    app.input_text.insert("1.0", app._result.display)
    app.on_decode()
    assert app._result.display == "hi"


def test_app_load_text_file(app, gui, monkeypatch, tmp_path):
    src = tmp_path / "a.txt"
    src.write_text("hi", encoding="utf-8")
    monkeypatch.setattr(gui.filedialog, "askopenfilename", lambda *a, **kw: str(src))
    app.on_load()
    assert app._binary is None
    assert app.input_text.get("1.0", "end-1c") == "hi"


def test_app_load_binary_encode_save(app, gui, monkeypatch, tmp_path):
    src = tmp_path / "raw.bin"
    src.write_bytes(b"\x00\x01")
    out = tmp_path / "out.txt"
    monkeypatch.setattr(gui.filedialog, "askopenfilename", lambda *a, **kw: str(src))
    monkeypatch.setattr(gui.filedialog, "asksaveasfilename", lambda *a, **kw: str(out))
    app.on_load()
    assert app._binary == b"\x00\x01"
    app.on_encode()
    assert app._result.display == "AAE="
    app.on_save()
    assert out.read_bytes() == b"AAE="


def test_app_save_writes_raw_decoded_bytes(app, gui, monkeypatch, tmp_path):
    out = tmp_path / "decoded.txt"
    monkeypatch.setattr(gui.filedialog, "asksaveasfilename", lambda *a, **kw: str(out))
    app.input_text.insert("1.0", "aGk=")
    app.on_decode()
    app.on_save()
    assert out.read_bytes() == b"hi"


def test_app_save_without_result(app):
    app.on_save()
    assert app.status.cget("text") == "нечего сохранять"


def test_app_editing_clears_binary(app):
    app._set_input_mode(b"\x00", "x.bin")
    assert app._binary is not None

    class Event:
        keysym = "a"

    app._on_input_edited(Event())
    assert app._binary is None


def test_app_modifier_key_keeps_binary(app):
    app._set_input_mode(b"\x00", "x.bin")

    class Event:
        keysym = "Shift_L"

    app._on_input_edited(Event())
    assert app._binary == b"\x00"
