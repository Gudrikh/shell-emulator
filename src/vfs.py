"""Загрузка виртуальной файловой системы из CSV."""

import base64
import binascii
import csv
from dataclasses import dataclass


CSV_FIELDS = ["path", "type", "content_base64"]


class VfsError(ValueError):
    """Ошибка загрузки или проверки VFS."""


@dataclass(frozen=True)
class VfsEntry:
    """Запись файла или папки в VFS."""

    path: str
    kind: str
    content: bytes


class VirtualFileSystem:
    """Хранит файлы и папки VFS в памяти."""

    def __init__(self, entries):
        """Создаёт VFS из словаря записей."""
        self.entries = entries

    @classmethod
    def from_csv(cls, path):
        """Загружает VFS из CSV и проверяет её структуру."""
        try:
            with open(path, newline="", encoding="utf-8-sig") as stream:
                reader = csv.DictReader(stream)
                if reader.fieldnames != CSV_FIELDS:
                    raise VfsError("Неверные заголовки CSV-файла.")

                entries = {}
                for row in reader:
                    line_number = reader.line_num
                    entry = cls._parse_row(row, line_number)
                    if entry.path in entries:
                        raise VfsError(
                            f"Строка {line_number}: путь повторяется."
                        )
                    entries[entry.path] = entry

                cls._validate_parents(entries)
                return cls(entries)
        except FileNotFoundError as error:
            raise VfsError(f"Файл VFS не найден: {path}") from error
        except (OSError, UnicodeError, csv.Error) as error:
            raise VfsError(f"Не удалось прочитать CSV: {error}") from error

    @staticmethod
    def _parse_row(row, line_number):
        """Проверяет CSV-строку и декодирует содержимое файла."""
        if None in row or any(value is None for value in row.values()):
            raise VfsError(f"Строка {line_number}: не хватает полей.")

        path = row["path"].strip()
        kind = row["type"].strip()
        encoded = row["content_base64"].strip()
        parts = path.split("/")

        if (
            not path
            or path.startswith("/")
            or "\\" in path
            or any(part in ("", ".", "..") for part in parts)
        ):
            raise VfsError(f"Строка {line_number}: неверный путь.")

        if kind not in ("file", "dir"):
            raise VfsError(f"Строка {line_number}: тип должен быть file или dir.")

        if kind == "dir":
            if encoded:
                raise VfsError(
                    f"Строка {line_number}: у папки не должно быть содержимого."
                )
            content = b""
        else:
            try:
                content = base64.b64decode(encoded, validate=True)
            except (binascii.Error, ValueError) as error:
                raise VfsError(
                    f"Строка {line_number}: неверный Base64."
                ) from error

        return VfsEntry(path, kind, content)

    @staticmethod
    def _validate_parents(entries):
        """Проверяет, что родительские папки записаны в CSV."""
        for path in entries:
            parent = path.rpartition("/")[0]
            if parent and (
                parent not in entries or entries[parent].kind != "dir"
            ):
                raise VfsError(
                    f"Для пути «{path}» не найдена папка «{parent}»."
                )