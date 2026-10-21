# OpenCode test

Небольшое демо CLI-приложение на Python: команды `greet`, `version` и `b64`.
Зависимости только из стандартной библиотеки (argparse, base64).

## Установка

```bash
git clone <repo-url>
cd opencode-test
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

## Использование

```bash
opencode-test greet          # Hello, world!
opencode-test greet Alice    # Hello, Alice!
opencode-test version        # 0.1.0
python -m opencode_test greet Alice
```

## Base64: decode/encode

Подкоманда `b64` (интерфейс совпадает со standalone-скриптом `standalone/b64dec.py`):

```bash
echo 'aGVsbG8sIHdvcmxkIQ==' | opencode-test b64  # hello, world!
opencode-test b64 'aGVsbG8sIHdvcmxkIQ=='          # то же через аргумент
opencode-test b64 -i encoded.txt -o out.bin       # из файла в файл
opencode-test b64 'data:image/png;base64,iVBOR...'  # бинарь -> decoded.png
opencode-test b64 -i photo.b64 -o - | file -      # сырые байты в пайп
opencode-test b64 -e 'hello, world!'              # aGVsbG8sIHdvcmxkIQ==
echo -n 'hi' | opencode-test b64 -e               # aGk=
```

Вход нормализуется автоматически: пробелы/переносы строк, отсутствующий
`=`-padding, urlsafe-алфавит, префикс `data:<mime>;base64,`.

Без `-o`: текст печатается в stdout точными байтами; бинарь записывается
в файл `decoded.<ext>` (расширение из mime data-URL, иначе `.bin`), путь
сообщается в stderr. `-o -` пишет сырые байты в stdout.

## Перенос в изолированную среду

`standalone/b64dec.py` — один самодостаточный файл (только stdlib, Python 3.10+).
Переносится текстом:

```bash
python3 - << 'EOF' > b64dec.py
# сюда вставить содержимое standalone/b64dec.py
EOF
python3 b64dec.py 'aGVsbG8sIHdvcmxkIQ=='          # hello, world!
```

Либо вставить текст файла в любой редактор и сохранить как `b64dec.py`.
Запасной вариант без файла для тривиальных случаев:

```bash
echo 'aGVsbG8sIHdvcmxkIQ==' | python3 -c "import base64,sys; s=''.join(sys.stdin.read().split()); s+='='*(-len(s)%4); sys.stdout.buffer.write(base64.b64decode(s))"
```

Большие payload передавайте через `-i` или stdin: у аргументов shell есть лимит длины.

## Разработка

```bash
pytest               # тесты
ruff check .         # линт
ruff format .        # форматирование
```
