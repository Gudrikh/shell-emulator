"""Графический интерфейс эмулятора."""

import getpass
import socket
import tkinter as tk
from tkinter.scrolledtext import ScrolledText

from src.shell import Shell


class EmulatorApp:
    """Обрабатывает ввод команд в окне."""

    def __init__(self, root):
        """Создаёт элементы интерфейса."""
        self.root = root
        self.shell = Shell()

        username = getpass.getuser()
        hostname = socket.gethostname()

        self.root.title(
            f"Эмулятор - [{username}@{hostname}]"
        )
        self.root.geometry("800x500")
        self.prompt = f"{username}@{hostname}:~$ "

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

    def _append(self, text):
        """Добавляет строку в область вывода."""
        self.output.configure(state="normal")
        self.output.insert(tk.END, text + "\n")
        self.output.configure(state="disabled")
        self.output.see(tk.END)

    def _handle_command(self, event):
        """Выполняет введённую команду."""
        command = self.input.get()
        self.input.delete(0, tk.END)
        self._append(self.prompt + command)

        result, should_exit = self.shell.execute(command)
        if result:
            self._append(result)

        if should_exit:
            self.root.destroy()

        return "break"


def main():
    """Запускает графическое приложение."""
    root = tk.Tk()
    EmulatorApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()