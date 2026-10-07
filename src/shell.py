"""Обработка команд первого этапа."""

import os
import shlex


class Shell:
    """Разбирает и выполняет команды эмулятора."""

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

        if command in ("ls", "cd"):
            return self._stub(command, parameters), False

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

    def _stub(self, command, parameters):
        """Показывает имя команды-заглушки и её аргументы."""
        if parameters:
            arguments = ", ".join(parameters)
        else:
            arguments = "нет"

        return f"Заглушка {command}; аргументы: {arguments}"