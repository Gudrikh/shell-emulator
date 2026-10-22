"""Разбор и выполнение команд оболочки."""

import getpass
import os
import posixpath
import shlex

from src.vfs import VfsEntry


DEFAULT_HEAD_LINES = 10
SINGLE_PATH_ARGUMENTS = 1
MOVE_ARGUMENTS = 2
HEAD_COUNT_ARGUMENTS = 3
MIN_HEAD_LINES = 0
LS_FLAGS = frozenset("alR")


class CommandError(ValueError):
    """Ошибка аргументов или выполнения команды."""


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

        if command == "exit":
            return self._exit(parameters)

        handlers = {
            "ls": self._ls,
            "cd": self._cd,
            "whoami": self._whoami,
            "head": self._head,
            "mkdir": self._mkdir,
            "mv": self._mv,
        }
        handler = handlers.get(command)
        if handler is None:
            return f"Ошибка: неизвестная команда «{command}».", False
        try:
            return handler(parameters), False
        except CommandError as error:
            return str(error), False

    @staticmethod
    def _exit(parameters):
        """Завершает работу при отсутствии аргументов."""
        if parameters:
            return "Ошибка: exit не принимает аргументы.", False
        return "Работа эмулятора завершена.", True

    def _parse(self, line):
        """Раскрывает переменные среды и делит строку на части."""
        expanded = os.path.expandvars(line)
        lexer = shlex.shlex(expanded, posix=True)
        lexer.whitespace_split = True
        lexer.escape = ""
        return list(lexer)

    def _ls(self, parameters):
        """Выводит объекты VFS с ключами -a, -l и -R."""
        flags, requested = self._ls_options(parameters)
        if self.vfs is None:
            return "Ошибка: VFS не загружена."
        path = self._resolve_path(requested)
        if path is None:
            return "Ошибка: путь выходит за пределы VFS."
        entry = self.vfs.entries.get(path)
        if path and entry is None:
            return f"Ошибка: путь «{requested}» не найден."
        if entry is not None and entry.kind == "file":
            return self._format_ls_entry(entry, flags)
        if "R" in flags:
            return self._list_recursive(path, flags)
        return self._list_directory(path, flags)

    @staticmethod
    def _ls_options(parameters):
        """Разбирает отдельные и объединённые ключи ls."""
        flags = set()
        paths = []
        parse_flags = True
        for argument in parameters:
            if parse_flags and argument == "--":
                parse_flags = False
            elif Shell._is_ls_flag(argument, parse_flags):
                selected = set(argument[1:])
                if not selected <= LS_FLAGS:
                    raise CommandError(
                        f"Ошибка: неизвестный ключ ls «{argument}»."
                    )
                flags.update(selected)
            else:
                paths.append(argument)
        if len(paths) > SINGLE_PATH_ARGUMENTS:
            raise CommandError("Ошибка: используйте ls [-a] [-l] [-R] [путь].")
        return flags, paths[0] if paths else "."

    @staticmethod
    def _is_ls_flag(argument, parse_flags):
        """Отличает ключ от имени после -- и имени одиночного дефиса."""
        return parse_flags and argument.startswith("-") and argument != "-"

    def _directory_entries(self, directory, flags):
        """Выбирает непосредственных детей, учитывая скрытые имена."""
        entries = []
        for path, entry in self.vfs.entries.items():
            if posixpath.dirname(path) != directory:
                continue
            name = posixpath.basename(path)
            if name.startswith(".") and "a" not in flags:
                continue
            entries.append(entry)
        return sorted(entries, key=lambda entry: entry.path.lower())

    @staticmethod
    def _format_ls_entry(entry, flags):
        """Показывает имя или тип, размер и имя объекта."""
        name = posixpath.basename(entry.path)
        if "l" in flags:
            size = len(entry.content)
            return f"{entry.kind} {size} {name}"
        return name + ("/" if entry.kind == "dir" else "")

    def _list_directory(self, directory, flags):
        """Возвращает содержимое одного каталога."""
        return "\n".join(
            self._format_ls_entry(entry, flags)
            for entry in self._directory_entries(directory, flags)
        )

    def _list_recursive(self, directory, flags):
        """Обходит дерево каталогов без рекурсии в стеке Python."""
        blocks = []
        pending = [directory]
        while pending:
            current = pending.pop()
            entries = self._directory_entries(current, flags)
            content = "\n".join(
                self._format_ls_entry(entry, flags) for entry in entries
            )
            label = "/" + current if current else "/"
            blocks.append(f"{label}:\n{content}".rstrip())
            directories = [
                entry.path for entry in entries if entry.kind == "dir"
            ]
            pending.extend(reversed(directories))
        return "\n\n".join(blocks)

    def _cd(self, parameters):
        """Меняет текущий каталог VFS."""
        if len(parameters) > SINGLE_PATH_ARGUMENTS:
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

        file_path, line_count = self._head_options(parameters)
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

    @staticmethod
    def _head_options(parameters):
        """Проверяет форму команды head и количество строк."""
        if parameters and parameters[0] == "-n":
            if len(parameters) != HEAD_COUNT_ARGUMENTS:
                raise CommandError("Ошибка: используйте head -n число файл.")
            count = Shell._head_line_count(parameters[1])
            return parameters[2], count
        if len(parameters) != SINGLE_PATH_ARGUMENTS:
            raise CommandError("Ошибка: используйте head [-n число] файл.")
        return parameters[0], DEFAULT_HEAD_LINES

    @staticmethod
    def _head_line_count(value):
        """Преобразует и проверяет неотрицательное количество строк."""
        try:
            count = int(value)
        except ValueError as error:
            raise CommandError(
                "Ошибка: число строк должно быть целым числом."
            ) from error
        if count < MIN_HEAD_LINES:
            raise CommandError(
                "Ошибка: число строк не может быть отрицательным."
            )
        return count

    def _mkdir(self, parameters):
        """Создаёт каталог в памяти."""
        if len(parameters) != SINGLE_PATH_ARGUMENTS:
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
        if len(parameters) != MOVE_ARGUMENTS:
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
