import base64
import importlib.util
import json
import sys
import threading
import urllib.error
import urllib.request
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
WEB_PATH = ROOT / "ui-web" / "b64web.py"


def _load():
    spec = importlib.util.spec_from_file_location("b64web_test", WEB_PATH)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["b64web_test"] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def web():
    return _load()


@pytest.fixture(scope="module")
def base_url(web):
    httpd = web.make_server("127.0.0.1", 0)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{httpd.server_address[1]}"
    httpd.shutdown()
    httpd.server_close()


def api(base_url, payload):
    req = urllib.request.Request(
        base_url + "/api/transform",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode("utf-8"))


def test_page_served(base_url):
    with urllib.request.urlopen(base_url + "/") as resp:
        assert resp.status == 200
        body = resp.read().decode("utf-8")
    assert "Encode" in body
    assert "Decode" in body
    assert "Сохранить" in body


def test_unknown_path_404(base_url):
    with pytest.raises(urllib.error.HTTPError) as exc:
        urllib.request.urlopen(base_url + "/nope")
    assert exc.value.code == 404


def test_encode_text(base_url):
    data = api(base_url, {"action": "encode", "text": "hi"})
    assert data["ok"]
    assert data["display"] == "aGk="
    assert data["filename"] == "encoded.txt"
    assert base64.b64decode(data["data_b64"]) == b"aGk="


def test_encode_binary_payload(base_url):
    raw = base64.b64encode(b"\xfb\xff").decode()
    data = api(base_url, {"action": "encode", "data_b64": raw})
    assert data["ok"]
    assert data["display"] == "+/8="


def test_decode_text(base_url):
    data = api(base_url, {"action": "decode", "text": "aGVsbG8="})
    assert data["ok"]
    assert data["display"] == "hello"
    assert base64.b64decode(data["data_b64"]) == b"hello"


def test_decode_binary(base_url):
    payload = b"\x89PNG\x00\x01"
    arg = f"data:image/png;base64,{base64.b64encode(payload).decode()}"
    data = api(base_url, {"action": "decode", "text": arg})
    assert data["ok"]
    assert data["is_binary"]
    assert data["filename"] == "decoded.png"
    assert base64.b64decode(data["data_b64"]) == payload


def test_decode_invalid(base_url):
    data = api(base_url, {"action": "decode", "text": "aGVs!bG8="})
    assert not data["ok"]
    assert "invalid base64 character" in data["message"]


def test_decode_rejects_binary_input(base_url):
    data = api(base_url, {"action": "decode", "text": "aGk=", "data_b64": "AAE="})
    assert not data["ok"]
    assert "base64-текст" in data["message"]


def test_load_text(base_url):
    data_b64 = base64.b64encode(b"hi").decode()
    data = api(base_url, {"action": "load", "data_b64": data_b64, "name": "a.txt"})
    assert data["ok"]
    assert not data["is_binary"]
    assert data["display"] == "hi"


def test_load_binary(base_url):
    data_b64 = base64.b64encode(b"\x00\x01").decode()
    data = api(base_url, {"action": "load", "data_b64": data_b64, "name": "a.bin"})
    assert data["ok"]
    assert data["is_binary"]
    assert "a.bin" in data["display"]


def test_load_empty_file(base_url):
    data = api(base_url, {"action": "load", "name": "a.bin"})
    assert not data["ok"]
    assert "пустой файл" in data["message"]


def test_unknown_action(base_url):
    data = api(base_url, {"action": "nope"})
    assert not data["ok"]
    assert "неизвестное действие" in data["message"]


def test_bad_json_returns_400(base_url):
    req = urllib.request.Request(
        base_url + "/api/transform",
        data=b"{not json",
        headers={"Content-Type": "application/json"},
    )
    with pytest.raises(urllib.error.HTTPError) as exc:
        urllib.request.urlopen(req)
    assert exc.value.code == 400
