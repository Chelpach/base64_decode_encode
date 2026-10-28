"""Base64 encode/decode GUI (tkinter), stdlib-only.

ui-tkinter/b64gui.py is the source of truth; standalone/b64gui.py is a
byte-identical copy of this file, meant to be pasted as text into isolated
environments and run as ``python3 b64gui.py``.
"""

from __future__ import annotations

import base64
import binascii
import re
import tkinter as tk
from pathlib import Path
from tkinter import filedialog

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

_MODIFIER_KEYS = frozenset(
    {
        "Shift_L",
        "Shift_R",
        "Control_L",
        "Control_R",
        "Alt_L",
        "Alt_R",
        "Meta_L",
        "Meta_R",
        "Super_L",
        "Super_R",
        "Caps_Lock",
    }
)


class App:
    def __init__(self, root: tk.Tk):
        self.root = root
        self._binary: bytes | None = None
        self._binary_name: str | None = None
        self._result: Outcome | None = None
        root.title("b64 encode/decode")
        root.columnconfigure(0, weight=1)
        root.rowconfigure(1, weight=1)
        root.rowconfigure(5, weight=1)

        tk.Label(root, text="Вход").grid(
            row=0, column=0, sticky="w", padx=8, pady=(8, 0)
        )
        self.input_text = tk.Text(root, height=8, wrap="word")
        self.input_text.grid(row=1, column=0, sticky="nsew", padx=8, pady=4)
        self.input_state = tk.Label(root, text="вход: текст", anchor="w", fg="#666666")
        self.input_state.grid(row=2, column=0, sticky="ew", padx=8)

        buttons = tk.Frame(root)
        buttons.grid(row=3, column=0, sticky="ew", padx=8, pady=4)
        tk.Button(buttons, text="Из файла", command=self.on_load).pack(side="left")
        tk.Button(buttons, text="Encode", command=self.on_encode).pack(
            side="left", padx=4
        )
        tk.Button(buttons, text="Decode", command=self.on_decode).pack(side="left")
        tk.Button(buttons, text="Сохранить", command=self.on_save).pack(side="right")

        tk.Label(root, text="Результат").grid(row=4, column=0, sticky="w", padx=8)
        self.result_text = tk.Text(root, height=8, wrap="word", state="disabled")
        self.result_text.grid(row=5, column=0, sticky="nsew", padx=8, pady=4)

        self.status = tk.Label(root, text="готово", anchor="w")
        self.status.grid(row=6, column=0, sticky="ew", padx=8, pady=(0, 8))

        self.input_text.bind("<Key>", self._on_input_edited)
        self.input_text.bind("<<Paste>>", self._on_input_edited)
        self.input_text.bind("<<Cut>>", self._on_input_edited)

    def _set_status(self, msg: str) -> None:
        self.status.config(text=msg)

    def _set_result(self, outcome: Outcome) -> None:
        self._result = outcome
        self.result_text.config(state="normal")
        self.result_text.delete("1.0", "end")
        self.result_text.insert("1.0", outcome.display)
        self.result_text.config(state="disabled")

    def _set_input_mode(self, binary: bytes | None, name: str | None) -> None:
        self._binary = binary
        self._binary_name = name
        if binary is None:
            self.input_state.config(text="вход: текст")
        else:
            self.input_state.config(
                text=f"вход: бинарный файл {name} ({len(binary)} байт)"
            )

    def _on_input_edited(self, event) -> None:
        if event.keysym in _MODIFIER_KEYS:
            return
        if self._binary is not None:
            self._set_input_mode(None, None)
            self._set_status("бинарный вход сброшен — ввод текста")

    def on_load(self) -> None:
        path = filedialog.askopenfilename()
        if not path:
            return
        try:
            data = Path(path).read_bytes()
        except OSError as exc:
            self._set_status(f"Ошибка: {exc}")
            return
        name = Path(path).name
        outcome = classify_input(data, name)
        self.input_text.delete("1.0", "end")
        if outcome.is_binary:
            self._set_input_mode(data, name)
        else:
            self._set_input_mode(None, None)
            self.input_text.insert("1.0", outcome.display)
        self._set_status(outcome.message)

    def on_encode(self) -> None:
        text = self.input_text.get("1.0", "end-1c")
        outcome = encode_payload(text, self._binary)
        self._set_status(outcome.message)
        if outcome.ok:
            self._set_result(outcome)

    def on_decode(self) -> None:
        text = self.input_text.get("1.0", "end-1c")
        outcome = decode_payload(text, self._binary)
        self._set_status(outcome.message)
        if outcome.ok:
            self._set_result(outcome)

    def on_save(self) -> None:
        if self._result is None or self._result.payload is None:
            self._set_status("нечего сохранять")
            return
        path = filedialog.asksaveasfilename(initialfile=self._result.filename)
        if not path:
            return
        try:
            Path(path).write_bytes(self._result.payload)
        except OSError as exc:
            self._set_status(f"Ошибка: {exc}")
            return
        self._set_status(f"сохранено: {path}")


def main() -> int:
    root = tk.Tk()
    App(root)
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
