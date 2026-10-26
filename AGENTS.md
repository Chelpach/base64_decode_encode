# AGENTS.md

Демо Python CLI (`opencode-test`) с командами `greet`, `version` и `b64` (decode/encode base64).

## Стек

- Python 3.10+, зависимости только stdlib (argparse, base64)
- Сборка: hatchling, src-layout, `pyproject.toml`
- Тесты: pytest; линт/формат: ruff (конфиг в `pyproject.toml`)

## Команды

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"   # установка
pytest                    # тесты
ruff check .              # линт
ruff format .             # форматирование
ruff format --check .     # проверка формата
opencode-test greet Alice # запуск CLI
opencode-test b64 'aGVsbG8='
python -m opencode_test greet Alice
```

## Устройство

- `src/opencode_test/cli.py` — argparse-команды, `main(argv) -> int`; `b64` перехватывается и делегируется в `b64.main`
- `src/opencode_test/b64.py` — decode/encode base64, `main(argv, prog=None) -> int`, только stdlib, без импортов пакета
- `standalone/b64dec.py` — байт-в-байт копия `b64.py` для переноса текстом в изолированную среду (Python 3.7+ за счёт `from __future__ import annotations`); синхронизация `cp`, идентичность проверяет тест
- `src/opencode_test/__init__.py` — `__version__`, единственный источник версии
- `tests/test_cli.py`, `tests/test_b64.py` — in-process тесты через `main([...])` + `capsys`/`capsysbinary`
- Ошибки использования аргументов — exit 2 (штатный argparse); runtime — stderr + return 1

При изменении кода/стека обновлять этот файл и README.md.
