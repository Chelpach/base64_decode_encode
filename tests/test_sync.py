import importlib.util
import inspect
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

CORE_FUNCS = [
    "_normalize_mapped",
    "normalize_b64",
    "_first_invalid",
    "decode_b64",
    "looks_like_text",
]
LOGIC_FUNCS = ["Outcome", "encode_payload", "decode_payload", "classify_input"]


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def modules():
    pytest.importorskip("tkinter")
    b64 = _load("sync_b64", ROOT / "src" / "opencode_test" / "b64.py")
    gui = _load("sync_gui", ROOT / "ui-tkinter" / "b64gui.py")
    web = _load("sync_web", ROOT / "ui-web" / "b64web.py")
    return b64, gui, web


def test_standalone_copies_are_in_sync():
    pairs = [
        ("src/opencode_test/b64.py", "standalone/b64dec.py"),
        ("ui-tkinter/b64gui.py", "standalone/b64gui.py"),
        ("ui-web/b64web.py", "standalone/b64web.py"),
    ]
    for src, dst in pairs:
        assert (ROOT / dst).read_bytes() == (ROOT / src).read_bytes(), dst


def test_core_function_sources_match(modules):
    b64, gui, web = modules
    for name in CORE_FUNCS:
        src = inspect.getsource(getattr(b64, name))
        assert inspect.getsource(getattr(gui, name)) == src, f"gui {name}"
        assert inspect.getsource(getattr(web, name)) == src, f"web {name}"


def test_core_constants_match(modules):
    b64, gui, web = modules
    for mod in (gui, web):
        assert mod.MIME_EXTENSIONS == b64.MIME_EXTENSIONS
        assert mod._B64_CHARS == b64._B64_CHARS
        assert mod._DATA_URL_RE.pattern == b64._DATA_URL_RE.pattern


def test_logic_sources_match_between_uis(modules):
    _, gui, web = modules
    for name in LOGIC_FUNCS:
        src = inspect.getsource(getattr(gui, name))
        assert inspect.getsource(getattr(web, name)) == src, name
