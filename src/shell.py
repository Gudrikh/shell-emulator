"""Разбор и выполнение команд оболочки."""

import getpass
import os
import posixpath
import shlex


DEFAULT_HEAD_LINES = 10


class Shell:
    """Разбирает и выполняет команды эмулятора."""

    def __init__(self, vfs=None):
        """Сохраняет VFS и устанавливает корневой каталог."""
        self.vfs = vfs
        self.current_directory = ""

    def execute(self, line):
        """Возвращает вывод команды и признак выхода."""
        try:
            arguments = self._parse(line)
        except ValueError:
            return "Ошибка: проверь кавычки в команде.", False

        if not arguments:
            return "", False

        command = arguments[0]
        parameters = arguments[1:]

        if command == "ls":
            return self._ls(parameters), False
        if command == "cd":
            return self._cd(parameters), False
        if command == "whoami":
            return self._whoami(parameters), False
        if command == "head":
            return self._head(parameters), False

        if command == "exit":
            if parameters:
                return "Ошибка: exit не принимает аргументы.", False
            return "Работа эмулятора завершена.", True

        return f"Ошибка: неизвестная команда «{command}».", False

    def _parse(self, line):
        """Раскрывает переменные среды и делит строку на части."""
        expanded = os.path.expandvars(line)
        lexer = shlex.shlex(expanded, posix=True)
        lexer.whitespace_split = True
        lexer.escape = ""
        return list(lexer)

    def _ls(self, parameters):
        """Выводит файл или содержимое каталога."""
        if len(parameters) > 1:
            return "Ошибка: используйте ls [путь]."
        if self.vfs is None:
            return "Ошибка: VFS не загружена."

        path = self.current_directory
        if parameters:
            path = self._resolve_path(parameters[0])
            if path is None:
                return "Ошибка: путь выходит за пределы VFS."

        if not path:
            return self._list_directory("")
        entry = self.vfs.entries.get(path)
        if entry is None:
            return f"Ошибка: путь «{parameters[0]}» не найден."
        if entry.kind == "file":
            return posixpath.basename(path)
        return self._list_directory(path)

    def _list_directory(self, directory):
        """Возвращает имена непосредственных дочерних объектов."""
        prefix = f"{directory}/" if directory else ""
        children = {}

        for path, entry in self.vfs.entries.items():
            if not path.startswith(prefix):
                continue
            name = path[len(prefix):]
            if name and "/" not in name:
                children[name] = entry.kind

        return "\n".join(
            name + ("/" if kind == "dir" else "")
            for name, kind in sorted(
                children.items(),
                key=lambda item: item[0].lower(),
            )
        )

    def _cd(self, parameters):
        """Меняет текущий каталог VFS."""
        if len(parameters) > 1:
            return "Ошибка: используйте cd [путь]."
        if self.vfs is None:
            return "Ошибка: VFS не загружена."

        requested_path = parameters[0] if parameters else "/"
        path = self._resolve_path(requested_path)
        if path is None:
            return "Ошибка: путь выходит за пределы VFS."
        if not path:
            self.current_directory = ""
            return ""

        entry = self.vfs.entries.get(path)
        if entry is None:
            return f"Ошибка: каталог «{requested_path}» не найден."
        if entry.kind != "dir":
            return f"Ошибка: «{requested_path}» не является каталогом."

        self.current_directory = path
        return ""

    def _whoami(self, parameters):
        """Выводит имя пользователя операционной системы."""
        if parameters:
            return "Ошибка: whoami не принимает аргументы."
        return getpass.getuser()

    def _head(self, parameters):
        """Выводит начало текстового файла из VFS."""
        if self.vfs is None:
            return "Ошибка: VFS не загружена."

        line_count = DEFAULT_HEAD_LINES
        if parameters and parameters[0] == "-n":
            if len(parameters) != 3:
                return "Ошибка: используйте head -n число файл."
            try:
                line_count = int(parameters[1])
            except ValueError:
                return "Ошибка: число строк должно быть целым числом."
            if line_count < 0:
                return "Ошибка: число строк не может быть отрицательным."
            file_path = parameters[2]
        elif len(parameters) == 1:
            file_path = parameters[0]
        else:
            return "Ошибка: используйте head [-n число] файл."

        path = self._resolve_path(file_path)
        if path is None:
            return "Ошибка: путь выходит за пределы VFS."

        entry = self.vfs.entries.get(path)
        if entry is None:
            return f"Ошибка: файл «{file_path}» не найден."
        if entry.kind != "file":
            return f"Ошибка: «{file_path}» не является файлом."

        try:
            content = entry.content.decode("utf-8")
        except UnicodeDecodeError:
            return "Ошибка: файл не содержит текст в кодировке UTF-8."

        lines = content.splitlines()
        return "\n".join(lines[:line_count])

    def _resolve_path(self, path):
        """Нормализует путь относительно текущего каталога VFS."""
        if path.startswith("/"):
            candidate = path.lstrip("/")
        else:
            candidate = posixpath.join(self.current_directory, path)

        normalized = posixpath.normpath(candidate)
        if normalized in ("", "."):
            return ""
        if normalized == ".." or normalized.startswith("../"):
            return None
        return normalized