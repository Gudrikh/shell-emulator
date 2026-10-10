"""Проверки ключей ls и их сочетаний."""

import unittest

from src.shell import Shell
from src.vfs import VirtualFileSystem, VfsEntry


class LsOptionsTests(unittest.TestCase):
    """Проверяет скрытые имена, подробный и рекурсивный вывод."""

    def setUp(self):
        paths = {
            'docs': ('dir', b''),
            'docs/nested': ('dir', b''),
            'docs/nested/readme.txt': ('file', b'abc'),
            '.hidden': ('file', b'secret'),
            '.private': ('dir', b''),
            '.private/inside.txt': ('file', b'data'),
            'notes.txt': ('file', b'Note'),
            '-a': ('file', b'dash'),
        }
        entries = {
            path: VfsEntry(path, kind, content)
            for path, (kind, content) in paths.items()
        }
        self.shell = Shell(VirtualFileSystem(entries))

    def test_default_hides_dot_names(self):
        output, _ = self.shell.execute('ls')
        self.assertNotIn('.hidden', output)
        self.assertNotIn('.private', output)

    def test_all_shows_dot_names(self):
        output, _ = self.shell.execute('ls -a')
        self.assertIn('.hidden', output)
        self.assertIn('.private/', output)

    def test_long_lists_kind_and_byte_size(self):
        output, _ = self.shell.execute('ls -l notes.txt')
        self.assertEqual(output, 'file 4 notes.txt')

    def test_long_lists_directory_contents(self):
        output, _ = self.shell.execute('ls -l docs')
        self.assertEqual(output, 'dir 0 nested')

    def test_combined_and_separate_flags_agree(self):
        combined, _ = self.shell.execute('ls -alR')
        separate, _ = self.shell.execute('ls -a -l -R')
        self.assertEqual(combined, separate)
        self.assertIn('file 6 .hidden', combined)
        self.assertIn('/.private:', combined)

    def test_recursive_walks_nested_directories(self):
        output, _ = self.shell.execute('ls -R docs')
        self.assertIn('/docs:', output)
        self.assertIn('/docs/nested:\nreadme.txt', output)
        self.assertNotIn('/.private:', output)

    def test_recursive_hides_hidden_subtrees(self):
        output, _ = self.shell.execute('ls -R')
        self.assertNotIn('inside.txt', output)

    def test_flag_after_path_is_supported(self):
        output, _ = self.shell.execute('ls docs -R')
        expected, _ = self.shell.execute('ls -R docs')
        self.assertEqual(output, expected)

    def test_double_dash_allows_option_like_filename(self):
        output, _ = self.shell.execute('ls -- -a')
        self.assertEqual(output, '-a')

    def test_unknown_flag_returns_error(self):
        output, should_exit = self.shell.execute('ls -z')
        self.assertIn('неизвестный ключ ls', output)
        self.assertFalse(should_exit)

    def test_unknown_combined_flag_returns_error(self):
        output, _ = self.shell.execute('ls -az')
        self.assertIn('неизвестный ключ ls', output)

    def test_relative_path_works_with_flags(self):
        self.shell.execute('cd docs')
        output, _ = self.shell.execute('ls -l nested/readme.txt')
        self.assertEqual(output, 'file 3 readme.txt')
