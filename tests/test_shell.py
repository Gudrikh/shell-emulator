"""Проверки обработки команд."""

import getpass
import os
import unittest
from unittest.mock import patch

from src.shell import Shell
from src.vfs import VirtualFileSystem, VfsEntry


class ShellTests(unittest.TestCase):
    """Проверяет команды оболочки."""

    def setUp(self):
        """Создаёт тестовую VFS и обработчик команд."""
        sample_content = "\n".join(
            f"Line {number}" for number in range(1, 13)
        ).encode("utf-8")

        entries = {
            "docs": VfsEntry("docs", "dir", b""),
            "docs/sample.txt": VfsEntry(
                "docs/sample.txt",
                "file",
                sample_content,
            ),
            "docs/empty.txt": VfsEntry(
                "docs/empty.txt",
                "file",
                b"",
            ),
            "notes.txt": VfsEntry("notes.txt", "file", b"Note"),
        }
        self.shell = Shell(VirtualFileSystem(entries))

    def test_ls_lists_root_entries(self):
        """Проверяет список объектов в корне VFS."""
        output, should_exit = self.shell.execute("ls")
        self.assertIn("docs/", output)
        self.assertIn("notes.txt", output)
        self.assertFalse(should_exit)

    def test_ls_lists_current_directory(self):
        """Проверяет список объектов выбранной папки."""
        self.shell.execute("cd docs")
        output, _ = self.shell.execute("ls")
        self.assertIn("sample.txt", output)
        self.assertIn("empty.txt", output)

    def test_ls_displays_file_name(self):
        """Проверяет вывод имени файла."""
        output, _ = self.shell.execute("ls docs/sample.txt")
        self.assertEqual(output, "sample.txt")

    def test_ls_missing_path_returns_error(self):
        """Проверяет ошибку для отсутствующего пути."""
        output, should_exit = self.shell.execute("ls missing.txt")
        self.assertIn("не найден", output)
        self.assertFalse(should_exit)

    def test_ls_rejects_extra_arguments(self):
        """Проверяет ошибку при лишних аргументах ls."""
        output, _ = self.shell.execute("ls docs notes.txt")
        self.assertIn("используйте ls", output)

    def test_cd_changes_directory_and_returns_to_root(self):
        """Проверяет переход в папку и возврат в корень."""
        self.shell.execute("cd docs")
        inside, _ = self.shell.execute("ls")
        self.assertIn("sample.txt", inside)

        self.shell.execute("cd")
        root, _ = self.shell.execute("ls")
        self.assertIn("notes.txt", root)

    def test_cd_rejects_file(self):
        """Проверяет, что cd не открывает файл как папку."""
        output, _ = self.shell.execute("cd docs/sample.txt")
        self.assertIn("не является каталогом", output)

    def test_cd_rejects_missing_directory(self):
        """Проверяет ошибку при переходе в отсутствующую папку."""
        output, _ = self.shell.execute("cd missing")
        self.assertIn("не найден", output)

    def test_cd_rejects_path_above_vfs_root(self):
        """Проверяет запрет выхода выше корня VFS."""
        output, _ = self.shell.execute("cd ../../")
        self.assertIn("за пределы VFS", output)

    def test_whoami_displays_os_username(self):
        """Проверяет вывод имени пользователя."""
        output, should_exit = self.shell.execute("whoami")
        self.assertEqual(output, getpass.getuser())
        self.assertFalse(should_exit)

    def test_whoami_rejects_arguments(self):
        """Проверяет ошибку при аргументах whoami."""
        output, _ = self.shell.execute("whoami extra")
        self.assertIn("не принимает аргументы", output)

    def test_head_displays_ten_lines_by_default(self):
        """Проверяет вывод первых десяти строк по умолчанию."""
        output, _ = self.shell.execute("head docs/sample.txt")
        expected = "\n".join(f"Line {number}" for number in range(1, 11))
        self.assertEqual(output, expected)

    def test_head_accepts_line_count(self):
        """Проверяет режим head с заданным количеством строк."""
        output, _ = self.shell.execute("head -n 2 docs/sample.txt")
        self.assertEqual(output, "Line 1\nLine 2")

    def test_head_displays_all_lines_when_count_is_large(self):
        """Проверяет head с количеством больше числа строк в файле."""
        output, _ = self.shell.execute("head -n 20 docs/sample.txt")
        self.assertEqual(output.count("\n"), 11)

    def test_head_zero_lines_returns_empty_output(self):
        """Проверяет запрос нуля строк."""
        output, _ = self.shell.execute("head -n 0 docs/sample.txt")
        self.assertEqual(output, "")

    def test_head_empty_file_returns_empty_output(self):
        """Проверяет обработку пустого файла."""
        output, _ = self.shell.execute("head docs/empty.txt")
        self.assertEqual(output, "")

    def test_head_missing_file_returns_error(self):
        """Проверяет ошибку для отсутствующего файла."""
        output, _ = self.shell.execute("head missing.txt")
        self.assertIn("не найден", output)

    def test_head_rejects_directory(self):
        """Проверяет, что head не читает каталог."""
        output, _ = self.shell.execute("head docs")
        self.assertIn("не является файлом", output)

    def test_head_rejects_non_integer_line_count(self):
        """Проверяет ошибку для нечислового количества строк."""
        output, _ = self.shell.execute("head -n nope docs/sample.txt")
        self.assertIn("целым числом", output)

    def test_head_rejects_negative_line_count(self):
        """Проверяет ошибку для отрицательного количества строк."""
        output, _ = self.shell.execute("head -n -1 docs/sample.txt")
        self.assertIn("не может быть отрицательным", output)

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


if __name__ == "__main__":
    unittest.main()