# AGENTS.md

Инструменты encode/decode base64: CLI (`opencode-test`), tkinter-окно и
web-интерфейс. Только stdlib, без сторонних зависимостей.

## Стек

- Python 3.10+ (standalone-файлы — 3.7+), зависимости только stdlib
  (argparse, base64, tkinter, http.server)
- Сборка: hatchling, src-layout, `pyproject.toml`
- Тесты: pytest; линт/формат: ruff (конфиг в `pyproject.toml`)

## Команды

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"        # установка
pytest                         # тесты
ruff check .                   # линт
ruff format .                  # форматирование
ruff format --check .          # проверка формата
opencode-test 'aGVsbG8='       # запуск CLI
python -m opencode_test 'aGVsbG8='
python3 ui-tkinter/b64gui.py   # tkinter UI
python3 ui-web/b64web.py       # web UI (http://127.0.0.1:8765/)
```

## Устройство

- `src/opencode_test/b64.py` — CLI core (decode/encode, нормализация входа,
  `main(argv, prog=None) -> int`), только stdlib, Python 3.7+
- `src/opencode_test/__main__.py` — `python -m opencode_test`; entry point
  `opencode-test` указывает прямо на `b64:main`
- `src/opencode_test/__init__.py` — `__version__`, единственный источник версии
- `ui-tkinter/b64gui.py` — самодостаточный tkinter-скрипт; core и app-логика
  (`Outcome`, `encode_payload`, `decode_payload`, `classify_input`) — verbatim-копии
- `ui-web/b64web.py` — самодостаточный http.server-скрипт (страница + API
  `POST /api/transform` встроены); те же verbatim-копии core и app-логики
- `standalone/b64dec.py`, `standalone/b64gui.py`, `standalone/b64web.py` —
  байт-в-байт копии `b64.py`, `ui-tkinter/b64gui.py`, `ui-web/b64web.py`
  для переноса текстом в изолированную среду; синхронность проверяют тесты
- `tests/test_b64.py` — CLI-тесты через `main([...])` + `capsys`; тесты
  standalone-запуска
- `tests/test_b64gui.py` — app-логика и tkinter-smoke (skip без дисплея)
- `tests/test_b64web.py` — API web-варианта на живом сервере (ephemeral-порт)
- `tests/test_sync.py` — байт-идентичность standalone-копий, совпадение
  verbatim-блоков core (b64.py / b64gui.py / b64web.py) и app-логики между UI
- Ошибки использования аргументов CLI — exit 2 (штатный argparse); runtime —
  stderr + return 1

При изменении core-логики обновлять verbatim-копии в `ui-tkinter/b64gui.py` и
`ui-web/b64web.py`, затем `cp` в `standalone/` (тесты упадут при рассинхроне).
При изменении кода/стека обновлять этот файл и README.md.
