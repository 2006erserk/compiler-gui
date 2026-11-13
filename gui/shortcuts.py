"""Горячие клавиши: общие для обработчиков, подписей меню и подсказок."""

from __future__ import annotations

import sys

SHIFT_MASK = 0x0001

# (буква, Shift) -> команда из EditorApp.commands
CONTROL_SHORTCUTS = {
    ("n", False): "new",
    ("o", False): "open",
    ("s", False): "save",
    ("s", True): "save_as",
    ("z", False): "undo",
    ("z", True): "redo",
    ("y", False): "redo",
    ("x", False): "cut",
    ("c", False): "copy",
    ("v", False): "paste",
    ("a", False): "select_all",
}

# Подписи сочетаний в меню и подсказках.
ACCELERATOR_LABELS = {
    "new": "Ctrl+N",
    "open": "Ctrl+O",
    "save": "Ctrl+S",
    "save_as": "Ctrl+Shift+S",
    "undo": "Ctrl+Z",
    "redo": "Ctrl+Y",
    "cut": "Ctrl+X",
    "copy": "Ctrl+C",
    "paste": "Ctrl+V",
    "select_all": "Ctrl+A",
    "help": "F1",
}

# Работают, даже когда фокус не в редакторе.
WINDOW_COMMANDS = frozenset({"new", "open", "save", "save_as"})

# Коды клавиш X11
_X11_KEYCODE_LETTERS = {
    38: "a",
    54: "c",
    57: "n",
    32: "o",
    39: "s",
    55: "v",
    53: "x",
    29: "y",
    52: "z",
}
_USE_X11_KEYCODES = sys.platform.startswith("linux")


def command_for_event(event) -> str | None:
    letter = _letter_from_event(event)
    if letter is None:
        return None
    shift = bool(event.state & SHIFT_MASK)
    return CONTROL_SHORTCUTS.get((letter, shift))


def _letter_from_event(event) -> str | None:
    keysym = event.keysym
    if len(keysym) == 1 and "a" <= keysym.lower() <= "z":
        return keysym.lower()
    if _USE_X11_KEYCODES:
        return _X11_KEYCODE_LETTERS.get(event.keycode)
    return None
