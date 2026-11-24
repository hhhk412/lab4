"""Точка входа в приложение «Астероиды»."""

import tkinter as tk

from src.app import AsteroidsApp


def main() -> None:
    """Создать корневое окно Tkinter и запустить игровой цикл."""
    root = tk.Tk()
    AsteroidsApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
