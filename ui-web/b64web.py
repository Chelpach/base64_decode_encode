"""Base64 encode/decode web UI (stdlib-only http.server).

ui-web/b64web.py is the source of truth; standalone/b64web.py is a
byte-identical copy of this file, meant to be pasted as text into isolated
environments and run as ``python3 b64web.py``.
"""

from __future__ import annotations

import argparse
import base64
import binascii
import json
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

# --- core: copied verbatim from src/opencode_test/b64.py ---

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


# --- end core ---

# --- app logic: copied verbatim between ui-tkinter/b64gui.py and ui-web/b64web.py ---


class Outcome:
    def __init__(
        self,
        ok: bool,
        display: str = "",
        is_binary: bool = False,
        payload: bytes | None = None,
        filename: str | None = None,
        message: str = "",
    ):
        self.ok = ok
        self.display = display
        self.is_binary = is_binary
        self.payload = payload
        self.filename = filename
        self.message = message


def encode_payload(text: str | None, binary: bytes | None) -> Outcome:
    try:
        if binary is not None:
            data = binary
        elif text:
            data = text.encode("utf-8")
        else:
            raise ValueError("пустой ввод")
        out = base64.b64encode(data).decode("ascii")
    except ValueError as exc:
        return Outcome(False, message=f"Ошибка: {exc}")
    return Outcome(
        True,
        display=out,
        payload=out.encode("ascii"),
        filename="encoded.txt",
        message="готово: закодировано",
    )


def decode_payload(text: str | None, binary: bytes | None) -> Outcome:
    try:
        if binary is not None:
            raise ValueError("decode работает только с base64-текстом")
        data, mime = decode_b64(text or "")
    except ValueError as exc:
        return Outcome(False, message=f"Ошибка: {exc}")
    ext = MIME_EXTENSIONS.get(mime or "") or ("txt" if looks_like_text(data) else "bin")
    filename = f"decoded.{ext}"
    if looks_like_text(data):
        return Outcome(
            True,
            display=data.decode("utf-8"),
            payload=data,
            filename=filename,
            message="готово: декодировано",
        )
    size = len(data)
    kind = mime or "бинарные данные"
    return Outcome(
        True,
        display=f"⟨бинарные данные: {size} байт ({kind})⟩",
        is_binary=True,
        payload=data,
        filename=filename,
        message=f"готово: декодировано ({size} байт)",
    )


def classify_input(data: bytes, name: str) -> Outcome:
    if looks_like_text(data):
        return Outcome(
            True,
            display=data.decode("utf-8"),
            message=f"загружен текст из {name}",
        )
    size = len(data)
    return Outcome(
        True,
        display=f"⟨бинарный файл {name}: {size} байт⟩",
        is_binary=True,
        payload=data,
        message=f"загружен бинарный файл {name} ({size} байт)",
    )


# --- end app logic ---

PAGE = """<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="utf-8">
<title>b64 encode / decode</title>
<style>
  body { font: 14px/1.45 system-ui, sans-serif; margin: 0 auto;
         max-width: 860px; padding: 16px; }
  h1 { font-size: 18px; }
  .hint { color: #666; margin: 6px 0 4px; }
  textarea { width: 100%; box-sizing: border-box;
             font: 13px/1.4 ui-monospace, monospace;
             padding: 8px; border: 1px solid #bbb; border-radius: 6px; }
  #input, #result { height: 160px; resize: vertical; }
  .row { display: flex; gap: 8px; margin: 10px 0; }
  button { padding: 6px 14px; border: 1px solid #888; border-radius: 6px;
           background: #f5f5f5; cursor: pointer; }
  button:hover { background: #e8e8e8; }
  #status { margin-top: 10px; color: #444; }
  #file { display: none; }
</style>
</head>
<body>
<h1>Base64 encode / decode</h1>
<div class="hint">Вход</div>
<textarea id="input" placeholder="вставьте значение..."></textarea>
<div class="hint" id="input-state">вход: текст</div>
<div class="row">
  <button id="load">Из файла</button>
  <button id="encode">Encode</button>
  <button id="decode">Decode</button>
  <button id="save">Сохранить</button>
  <input type="file" id="file">
</div>
<div class="hint">Результат</div>
<textarea id="result" readonly></textarea>
<div id="status">готово</div>
<script>
"use strict";
let binary = null;
let resultBytes = null;
let resultName = null;

function el(id) { return document.getElementById(id); }

function toB64(bytes) {
  let s = "";
  for (let i = 0; i < bytes.length; i += 0x8000) {
    s += String.fromCharCode.apply(null, bytes.subarray(i, i + 0x8000));
  }
  return btoa(s);
}

function fromB64(b64) {
  const s = atob(b64);
  const out = new Uint8Array(s.length);
  for (let i = 0; i < s.length; i++) out[i] = s.charCodeAt(i);
  return out;
}

async function api(payload) {
  const res = await fetch("/api/transform", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return res.json();
}

function setStatus(msg) { el("status").textContent = msg; }

function setBinary(bytes, name, display) {
  binary = bytes;
  el("input").value = "";
  el("input").placeholder = display;
  el("input-state").textContent =
    "вход: бинарный файл " + name + " (" + bytes.length + " байт)";
}

function setTextInput(text, name) {
  binary = null;
  el("input").placeholder = "";
  el("input").value = text;
  el("input-state").textContent = name ? "вход: текст из " + name : "вход: текст";
}

function applyResult(data) {
  setStatus(data.message);
  if (!data.ok) return;
  el("result").value = data.display;
  resultBytes = data.data_b64 ? fromB64(data.data_b64) : null;
  resultName = data.filename || "result";
}

async function run(action) {
  const data = await api({
    action: action,
    text: el("input").value,
    data_b64: binary ? toB64(binary) : null,
  });
  applyResult(data);
}

el("load").addEventListener("click", () => el("file").click());

el("file").addEventListener("change", async () => {
  const f = el("file").files[0];
  if (!f) return;
  const bytes = new Uint8Array(await f.arrayBuffer());
  const data = await api({ action: "load", data_b64: toB64(bytes), name: f.name });
  setStatus(data.message);
  if (!data.ok) return;
  if (data.is_binary) {
    setBinary(bytes, f.name, data.display);
  } else {
    setTextInput(data.display, f.name);
  }
});

el("encode").addEventListener("click", () => run("encode"));
el("decode").addEventListener("click", () => run("decode"));

el("save").addEventListener("click", () => {
  if (!resultBytes) {
    setStatus("нечего сохранять");
    return;
  }
  const blob = new Blob([resultBytes], { type: "application/octet-stream" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = resultName || "result";
  a.click();
  URL.revokeObjectURL(url);
  setStatus("сохранено: " + a.download);
});

el("input").addEventListener("input", () => {
  if (binary) {
    binary = null;
    el("input").placeholder = "";
    el("input-state").textContent = "вход: текст";
    setStatus("бинарный вход сброшен — ввод текста");
  }
});
</script>
</body>
</html>
"""


def handle_transform(req: dict) -> dict:
    action = req.get("action")
    binary = None
    if req.get("data_b64"):
        try:
            binary = base64.b64decode(req["data_b64"], validate=True)
        except (binascii.Error, ValueError) as exc:
            return {"ok": False, "message": f"Ошибка: {exc}"}
    if action == "load":
        name = req.get("name") or "файл"
        if binary is None:
            return {"ok": False, "message": "Ошибка: пустой файл"}
        out = classify_input(binary, name)
    elif action == "encode":
        out = encode_payload(req.get("text"), binary)
    elif action == "decode":
        out = decode_payload(req.get("text"), binary)
    else:
        return {"ok": False, "message": "Ошибка: неизвестное действие"}
    data_b64 = None
    if action != "load" and out.payload is not None:
        data_b64 = base64.b64encode(out.payload).decode("ascii")
    return {
        "ok": out.ok,
        "display": out.display,
        "is_binary": out.is_binary,
        "filename": out.filename,
        "message": out.message,
        "data_b64": data_b64,
    }


class Handler(BaseHTTPRequestHandler):
    server_version = "b64web"

    def do_GET(self):
        if self.path.split("?", 1)[0] not in ("/", "/index.html"):
            self.send_error(404)
            return
        body = PAGE.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        if self.path.split("?", 1)[0] != "/api/transform":
            self.send_error(404)
            return
        try:
            length = int(self.headers.get("Content-Length") or 0)
            req = json.loads(self.rfile.read(length).decode("utf-8"))
            if not isinstance(req, dict):
                raise ValueError("ожидался JSON-объект")
        except (ValueError, UnicodeDecodeError) as exc:
            self._send_json({"ok": False, "message": f"Ошибка: {exc}"}, status=400)
            return
        self._send_json(handle_transform(req))

    def _send_json(self, data: dict, status: int = 200) -> None:
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        pass


def make_server(host: str, port: int) -> ThreadingHTTPServer:
    return ThreadingHTTPServer((host, port), Handler)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Base64 encode/decode web UI (stdlib only)",
    )
    parser.add_argument(
        "--host", default="127.0.0.1", help="bind address (default 127.0.0.1)"
    )
    parser.add_argument("--port", type=int, default=8765, help="port (default 8765)")
    args = parser.parse_args(argv)
    httpd = make_server(args.host, args.port)
    host, port = httpd.server_address[:2]
    print(f"b64web: http://{host}:{port}/")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nостановлено")
    finally:
        httpd.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
