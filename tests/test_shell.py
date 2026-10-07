"""Проверки обработки команд."""

import os
import unittest
from unittest.mock import patch

from src.shell import Shell


class ShellTests(unittest.TestCase):
    """Проверяет команды первого этапа."""

    def setUp(self):
        """Создаёт обработчик для каждой проверки."""
        self.shell = Shell()

    def test_ls_displays_its_argument(self):
        """Проверяет вывод имени команды и аргумента."""
        output, should_exit = self.shell.execute("ls notes.txt")
        self.assertIn("ls", output)
        self.assertIn("notes.txt", output)
        self.assertFalse(should_exit)

    def test_cd_is_a_stub(self):
        """Проверяет работу заглушки cd."""
        output, should_exit = self.shell.execute("cd folder")
        self.assertIn("cd", output)
        self.assertIn("folder", output)
        self.assertFalse(should_exit)

    def test_environment_variable_is_expanded(self):
        """Проверяет раскрытие переменной среды."""
        with patch.dict(os.environ, {"SHELL_TEST": "from-env"}):
            output, _ = self.shell.execute("ls $SHELL_TEST")
        self.assertIn("from-env", output)

    def test_unknown_command_returns_error(self):
        """Проверяет ошибку для неизвестной команды."""
        output, should_exit = self.shell.execute("unknown")
        self.assertIn("неизвестная команда", output)
        self.assertFalse(should_exit)

    def test_exit_with_argument_returns_error(self):
        """Проверяет ошибку при лишнем аргументе exit."""
        output, should_exit = self.shell.execute("exit now")
        self.assertIn("не принимает аргументы", output)
        self.assertFalse(should_exit)

    def test_exit_without_arguments_stops_loop(self):
        """Проверяет команду выхода."""
        _, should_exit = self.shell.execute("exit")
        self.assertTrue(should_exit)

    def test_unclosed_quote_returns_error(self):
        """Проверяет ошибку незакрытой кавычки."""
        output, should_exit = self.shell.execute('ls "notes')
        self.assertIn("проверь кавычки", output)
        self.assertFalse(should_exit)