"""Проверки целостности VFS при mkdir и mv."""

import tempfile
import unittest
from pathlib import Path

from src.shell import Shell
from src.vfs import VirtualFileSystem, VfsEntry


class MutationTests(unittest.TestCase):
    """Проверяет изменения дерева и сохранение исходного CSV."""

    def setUp(self):
        paths = {
            'docs': ('dir', b''),
            'docs/sub': ('dir', b''),
            'docs/sub/readme.txt': ('file', b'content'),
            'archive': ('dir', b''),
            'notes.txt': ('file', b'note'),
        }
        self.vfs = VirtualFileSystem({
            path: VfsEntry(path, kind, content)
            for path, (kind, content) in paths.items()
        })
        self.shell = Shell(self.vfs)

    def test_mkdir_creates_directory(self):
        output, _ = self.shell.execute('mkdir docs/new')
        self.assertEqual(output, '')
        self.assertEqual(self.vfs.entries['docs/new'].kind, 'dir')

    def test_mkdir_rejects_duplicate_and_missing_parent(self):
        for command in ('mkdir docs', 'mkdir missing/child', 'mkdir /'):
            with self.subTest(command=command):
                before = dict(self.vfs.entries)
                output, _ = self.shell.execute(command)
                self.assertIn('Ошибка:', output)
                self.assertEqual(self.vfs.entries, before)

    def test_move_file_preserves_content(self):
        output, _ = self.shell.execute('mv notes.txt renamed.txt')
        self.assertEqual(output, '')
        self.assertNotIn('notes.txt', self.vfs.entries)
        self.assertEqual(self.vfs.entries['renamed.txt'].content, b'note')

    def test_move_directory_moves_descendants_and_cwd(self):
        self.shell.execute('cd docs/sub')
        output, _ = self.shell.execute('mv /docs /archive')
        self.assertEqual(output, '')
        self.assertEqual(self.shell.current_directory, 'archive/docs/sub')
        result, _ = self.shell.execute('head readme.txt')
        self.assertEqual(result, 'content')
        for key, entry in self.vfs.entries.items():
            self.assertEqual(key, entry.path)
        self.assertNotIn('docs/sub/readme.txt', self.vfs.entries)

    def test_move_errors_do_not_mutate_vfs(self):
        commands = (
            'mv docs docs/sub',
            'mv notes.txt notes.txt',
            'mv notes.txt missing/file',
            'mv missing archive',
            'mv / archive',
            'mv notes.txt docs/sub/readme.txt',
        )
        for command in commands:
            with self.subTest(command=command):
                before = dict(self.vfs.entries)
                output, _ = self.shell.execute(command)
                self.assertIn('Ошибка:', output)
                self.assertEqual(self.vfs.entries, before)

    def test_argument_errors_do_not_stop_shell(self):
        for command in ('mkdir', 'mkdir a b', 'mv only', 'mv a b c'):
            with self.subTest(command=command):
                output, should_exit = self.shell.execute(command)
                self.assertIn('используйте', output)
                self.assertFalse(should_exit)

    def test_source_csv_remains_unchanged(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'vfs.csv'
            source = b'path,type,content_base64\ndocs,dir,\n'
            path.write_bytes(source)
            shell = Shell(VirtualFileSystem.from_csv(path))
            shell.execute('mkdir archive')
            shell.execute('mv docs archive')
            self.assertEqual(path.read_bytes(), source)
