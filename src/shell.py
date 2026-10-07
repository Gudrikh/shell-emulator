"""Разбор и выполнение команд оболочки."""

import getpass
import os
import posixpath
import shlex

from src.vfs import VfsEntry


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
        if command == "mkdir":
            return self._mkdir(parameters), False
        if command == "mv":
            return self._mv(parameters), False

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

        return "\n".join(content.splitlines()[:line_count])

    def _mkdir(self, parameters):
        """Создаёт каталог в памяти."""
        if len(parameters) != 1:
            return "Ошибка: используйте mkdir путь."
        if self.vfs is None:
            return "Ошибка: VFS не загружена."

        path = self._resolve_path(parameters[0])
        if path is None:
            return "Ошибка: путь выходит за пределы VFS."
        if not path or path in self.vfs.entries:
            return f"Ошибка: объект «{parameters[0]}» уже существует."

        parent = path.rpartition("/")[0]
        if parent:
            parent_entry = self.vfs.entries.get(parent)
            if parent_entry is None or parent_entry.kind != "dir":
                return f"Ошибка: родительский каталог «{parent}» не найден."

        self.vfs.entries[path] = VfsEntry(path, "dir", b"")
        return ""

    def _mv(self, parameters):
        """Перемещает или переименовывает объект в памяти."""
        if len(parameters) != 2:
            return "Ошибка: используйте mv источник назначение."
        if self.vfs is None:
            return "Ошибка: VFS не загружена."

        source = self._resolve_path(parameters[0])
        destination = self._resolve_path(parameters[1])
        if source is None or destination is None:
            return "Ошибка: путь выходит за пределы VFS."
        if not source:
            return "Ошибка: нельзя переместить корень VFS."

        entry = self.vfs.entries.get(source)
        if entry is None:
            return f"Ошибка: источник «{parameters[0]}» не найден."

        target = self._move_target(source, destination)
        error = self._validate_move(source, target, entry)
        if error:
            return error

        self._apply_move(source, target, entry)
        return ""

    def _move_target(self, source, destination):
        """Определяет итоговый путь назначения."""
        target_entry = self.vfs.entries.get(destination)
        if not destination or (
            target_entry is not None and target_entry.kind == "dir"
        ):
            return posixpath.join(
                destination,
                posixpath.basename(source),
            )
        return destination

    def _validate_move(self, source, target, entry):
        """Проверяет возможность перемещения объекта."""
        if target == source:
            return "Ошибка: источник и назначение совпадают."
        if entry.kind == "dir" and target.startswith(source + "/"):
            return "Ошибка: нельзя переместить каталог внутрь себя."
        if target in self.vfs.entries:
            return f"Ошибка: объект «{target}» уже существует."

        parent = target.rpartition("/")[0]
        if parent:
            parent_entry = self.vfs.entries.get(parent)
            if parent_entry is None or parent_entry.kind != "dir":
                return f"Ошибка: каталог назначения «{parent}» не найден."
        return None

    def _apply_move(self, source, target, entry):
        """Меняет пути объекта и его потомков в словаре VFS."""
        prefix = source + "/"
        moved_entries = {}
        old_paths = []

        for old_path, old_entry in self.vfs.entries.items():
            is_source = old_path == source
            is_child = (
                entry.kind == "dir"
                and old_path.startswith(prefix)
            )
            if not is_source and not is_child:
                continue

            new_path = target + old_path[len(source):]
            moved_entries[new_path] = VfsEntry(
                new_path,
                old_entry.kind,
                old_entry.content,
            )
            old_paths.append(old_path)

        for old_path in old_paths:
            del self.vfs.entries[old_path]
        self.vfs.entries.update(moved_entries)
        self._update_current_directory(source, target, entry)

    def _update_current_directory(self, source, target, entry):
        """Сохраняет текущий каталог при перемещении его родителя."""
        if entry.kind != "dir":
            return
        if self.current_directory == source:
            self.current_directory = target
        elif self.current_directory.startswith(source + "/"):
            suffix = self.current_directory[len(source):]
            self.current_directory = target + suffix

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