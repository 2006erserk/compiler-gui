#!/usr/bin/env python3
"""Точка входа: python3 main.py"""

import sys


def main() -> int:
    try:
        import tkinter as tk
    except ImportError:
        print(
            "Ошибка: модуль tkinter не найден.\n"
            "В Ubuntu установите его командой:\n"
            "    sudo apt install python3-tk",
            file=sys.stderr,
        )
        return 1

    from gui.app import EditorApp

    root = tk.Tk()
    EditorApp(root)
    root.mainloop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
