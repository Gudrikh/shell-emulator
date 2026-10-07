"""Графический интерфейс эмулятора."""

import argparse
import getpass
import socket
import tkinter as tk
from tkinter.scrolledtext import ScrolledText

from src.shell import Shell
from src.vfs import VirtualFileSystem, VfsError


class EmulatorApp:
    """Обрабатывает ввод команд в окне."""

    def __init__(self, root, vfs_path, prompt, startup_script, vfs):
        """Создаёт окно и запускает стартовый скрипт."""
        self.root = root
        self.vfs_path = vfs_path
        self.prompt = prompt
        self.shell = Shell(vfs)

        username = getpass.getuser()
        hostname = socket.gethostname()
        self.root.title(
            f"Эмулятор - [{username}@{hostname}]"
        )
        self.root.geometry("800x500")

        self.output = ScrolledText(
            root,
            state="disabled",
            wrap=tk.WORD,
        )
        self.output.pack(
            fill=tk.BOTH,
            expand=True,
            padx=10,
            pady=10,
        )

        self.input = tk.Entry(root)
        self.input.pack(
            fill=tk.X,
            padx=10,
            pady=(0, 10),
        )
        self.input.bind("<Return>", self._handle_command)
        self.input.focus_set()

        self._append("Доступные команды: ls, cd, exit.")
        if startup_script:
            self._run_startup_script(startup_script)

    def _append(self, text):
        """Добавляет строку в область вывода."""
        self.output.configure(state="normal")
        self.output.insert(tk.END, text + "\n")
        self.output.configure(state="disabled")
        self.output.see(tk.END)

    def _execute_command(self, command):
        """Выполняет команду и показывает результат."""
        self._append(self.prompt + command)
        result, should_exit = self.shell.execute(command)

        if result:
            self._append(result)
        if should_exit:
            self.root.destroy()

        return should_exit

    def _handle_command(self, event):
        """Обрабатывает команду, введённую в окне."""
        command = self.input.get()
        self.input.delete(0, tk.END)
        self._execute_command(command)
        return "break"

    def _run_startup_script(self, script_path):
        """Читает скрипт, пропуская пустые строки и комментарии."""
        try:
            with open(script_path, encoding="utf-8") as script:
                for raw_line in script:
                    command = raw_line.strip()
                    if not command or command.startswith("#"):
                        continue
                    if self._execute_command(command):
                        return
        except (OSError, UnicodeError) as error:
            self._append(f"Ошибка стартового скрипта: {error}")


def parse_arguments():
    """Читает параметры командной строки."""
    parser = argparse.ArgumentParser(
        description="Графический эмулятор командной оболочки."
    )
    parser.add_argument(
        "--vfs",
        default="data/vfs.csv",
        help="Путь к CSV-файлу виртуальной файловой системы.",
    )
    parser.add_argument(
        "--prompt",
        default=None,
        help="Приглашение перед вводом команд.",
    )
    parser.add_argument(
        "--script",
        default=None,
        help="Путь к стартовому скрипту.",
    )
    return parser.parse_args()


def main():
    """Загружает VFS и запускает графическое приложение."""
    args = parse_arguments()

    username = getpass.getuser()
    hostname = socket.gethostname()
    default_prompt = f"{username}@{hostname}:~$ "
    prompt = args.prompt if args.prompt is not None else default_prompt

    print(f"Путь к VFS: {args.vfs}")
    print(f"Приглашение: {prompt}")
    print(f"Стартовый скрипт: {args.script or 'не задан'}")

    try:
        vfs = VirtualFileSystem.from_csv(args.vfs)
    except VfsError as error:
        print(f"Ошибка загрузки VFS: {error}")
        return

    print(f"Загружено объектов VFS: {len(vfs.entries)}")

    root = tk.Tk()
    EmulatorApp(root, args.vfs, prompt, args.script, vfs)
    root.mainloop()


if __name__ == "__main__":
    main()