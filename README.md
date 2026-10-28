# Base64: CLI + UI

Инструменты encode/decode base64: CLI-утилита, tkinter-окно и web-интерфейс.
Только стандартная библиотека Python, без сторонних зависимостей.

## Установка CLI

```bash
git clone <repo-url>
cd opencode-test
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

## CLI

```bash
opencode-test 'aGVsbG8sIHdvcmxkIQ=='          # hello, world!
echo 'aGVsbG8sIHdvcmxkIQ==' | opencode-test   # то же через stdin
opencode-test -e 'hello, world!'              # aGVsbG8sIHdvcmxkIQ==
echo -n 'hi' | opencode-test -e               # aGk=
opencode-test -i encoded.txt -o out.bin       # из файла в файл
opencode-test 'data:image/png;base64,iVBOR...'  # бинарь -> decoded.png
opencode-test -i photo.b64 -o - | file -      # сырые байты в пайп
python -m opencode_test 'aGVsbG8='            # то же без установки
```

Вход нормализуется автоматически: пробелы/переносы строк, отсутствующий
`=`-padding, urlsafe-алфавит, префикс `data:<mime>;base64,`.
Приоритет входа: аргумент DATA, затем `--input FILE`, затем stdin.

Без `-o`: текст печатается в stdout точными байтами; бинарь записывается
в файл `decoded.<ext>` (расширение из mime data-URL, иначе `.bin`), путь
сообщается в stderr. `-o -` пишет сырые байты в stdout.

## UI: tkinter

```bash
python3 ui-tkinter/b64gui.py
```

Окно: поле «Вход», кнопки `Из файла`, `Encode`, `Decode`, `Сохранить`,
поле «Результат» ниже и статус-строка.

## UI: web

```bash
python3 ui-web/b64web.py            # http://127.0.0.1:8765/
python3 ui-web/b64web.py --port 9000
```

Та же форма в браузере. «Сохранить» — скачивание результата браузером.
При удалённом доступе пробросьте порт (ssh -L).

## Поведение UI (одинаково в обоих вариантах)

- Кнопка Encode/Decode работает с текстом из поля «Вход».
- «Из файла»: файл с текстом (UTF-8) заполняет поле; бинарный файл
  помечается как «бинарный вход» и кодируется напрямую по Encode.
- Encode: текст кодируется как UTF-8, бинарный вход — как есть; результат —
  base64-текст. Decode: принимает только base64-текст.
- Decode-результат: текст показывается в поле, бинарь — плейсхолдер
  «N байт (mime)»; «Сохранить» всегда пишет точные байты
  (`decoded.<ext>` по mime, иначе `.txt`/`.bin`).
- Любое редактирование поля входа сбрасывает бинарный вход; ошибки
  показываются в статус-строке.

## Перенос в изолированную среду

Один самодостаточный файл (только stdlib) на каждый инструмент:

| Файл | Назначение | Python |
|---|---|---|
| `standalone/b64dec.py` | CLI | 3.7+ |
| `standalone/b64gui.py` | tkinter-окно | 3.7+ |
| `standalone/b64web.py` | web-интерфейс | 3.7+ |

Переносится текстом:

```bash
python3 - << 'EOF' > b64dec.py
# сюда вставить содержимое standalone/b64dec.py
EOF
python3 b64dec.py 'aGVsbG8sIHdvcmxkIQ=='          # hello, world!
```

Каждый файл — байт-в-байт копия своего исходника (`src/opencode_test/b64.py`,
`ui-tkinter/b64gui.py`, `ui-web/b64web.py`); синхронность проверяется тестами.
Большие payload передавайте через `-i` или stdin: у аргументов shell есть
лимит длины.

## Разработка

```bash
pytest               # тесты
ruff check .         # линт
ruff format .        # форматирование
```
