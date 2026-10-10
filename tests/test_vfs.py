"""Проверки валидации CSV после разбиения функций."""

import tempfile
import unittest
from pathlib import Path

from src.vfs import VirtualFileSystem, VfsError


HEADER = 'path,type,content_base64\n'


class VfsLoadingTests(unittest.TestCase):
    """Проверяет корректные записи и ошибки входных данных."""

    def load(self, content):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'vfs.csv'
            path.write_text(content, encoding='utf-8')
            return VirtualFileSystem.from_csv(path)

    def test_file_content_is_decoded(self):
        vfs = self.load(HEADER + 'docs,dir,\ndocs/a.txt,file,YWJj\n')
        self.assertEqual(vfs.entries['docs/a.txt'].content, b'abc')

    def test_missing_file_returns_vfs_error(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(VfsError, 'не найден'):
                VirtualFileSystem.from_csv(Path(directory) / 'missing.csv')

    def test_wrong_header_is_rejected(self):
        with self.assertRaisesRegex(VfsError, 'заголовки'):
            self.load('path,type,data\n')

    def test_duplicate_path_is_rejected(self):
        with self.assertRaisesRegex(VfsError, 'повторяется'):
            self.load(HEADER + 'docs,dir,\ndocs,dir,\n')

    def test_invalid_paths_are_rejected(self):
        for path in ('/root', 'a//b', 'a/../b', r'a\b', ''):
            with self.subTest(path=path):
                with self.assertRaisesRegex(VfsError, 'неверный путь'):
                    self.load(HEADER + f'{path},file,\n')

    def test_missing_or_extra_fields_are_rejected(self):
        for row in ('a,file\n', 'a,file,,extra\n'):
            with self.subTest(row=row):
                with self.assertRaises(VfsError):
                    self.load(HEADER + row)

    def test_invalid_kind_is_rejected(self):
        with self.assertRaisesRegex(VfsError, 'тип должен быть'):
            self.load(HEADER + 'a,link,\n')

    def test_invalid_base64_is_rejected(self):
        with self.assertRaisesRegex(VfsError, 'Base64'):
            self.load(HEADER + 'a,file,invalid!\n')

    def test_directory_content_is_rejected(self):
        with self.assertRaisesRegex(VfsError, 'содержимого'):
            self.load(HEADER + 'docs,dir,YWJj\n')

    def test_parent_must_exist_and_be_a_directory(self):
        for rows in ('docs/a,file,\n', 'docs,file,\ndocs/a,file,\n'):
            with self.subTest(rows=rows):
                with self.assertRaisesRegex(VfsError, 'не найдена папка'):
                    self.load(HEADER + rows)
