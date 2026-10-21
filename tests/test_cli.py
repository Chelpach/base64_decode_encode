import pytest

from opencode_test import __version__
from opencode_test.cli import main


def test_greet_default(capsys):
    assert main(["greet"]) == 0
    assert capsys.readouterr().out == "Hello, world!\n"


def test_greet_with_name(capsys):
    assert main(["greet", "Alice"]) == 0
    assert capsys.readouterr().out == "Hello, Alice!\n"


def test_version(capsys):
    assert main(["version"]) == 0
    assert capsys.readouterr().out == f"{__version__}\n"


def test_unknown_command_exits_2():
    with pytest.raises(SystemExit) as exc:
        main(["unknown"])
    assert exc.value.code == 2


def test_missing_command_exits_2():
    with pytest.raises(SystemExit) as exc:
        main([])
    assert exc.value.code == 2
