"""Главное меню."""

import tkinter as tk

from .shortcuts import ACCELERATOR_LABELS

MENU_LAYOUT = (
    ("Файл", (
        ("Создать", "new"),
        ("Открыть", "open"),
        ("Сохранить", "save"),
        ("Сохранить как", "save_as"),
        None,
        ("Выход", "exit"),
    )),
    ("Правка", (
        ("Отменить", "undo"),
        ("Повторить", "redo"),
        None,
        ("Вырезать", "cut"),
        ("Копировать", "copy"),
        ("Вставить", "paste"),
        ("Удалить", "delete"),
        None,
        ("Выделить всё", "select_all"),
    )),
    # Станут активными, когда эти команды появятся в EditorApp.commands.
    ("Текст", (
        ("Постановка задачи", "text_task"),
        ("Грамматика", "text_grammar"),
        ("Классификация грамматики", "text_grammar_class"),
        ("Метод анализа", "text_analysis_method"),
        ("Тестовый пример", "text_test_example"),
        ("Список литературы", "text_references"),
        ("Исходный код программы", "text_source_code"),
    )),
    ("Пуск", "run"),
    ("Справка", (
        ("Вызов справки", "help"),
        ("О программе", "about"),
    )),
)


def build_menubar(root, commands) -> tk.Menu:
    """Пункты без команды (нет в commands или None) неактивны."""
    menubar = tk.Menu(root, tearoff=False)
    for title, content in MENU_LAYOUT:
        if isinstance(content, str):
            _add_command(menubar, title, content, commands)
            continue
        submenu = tk.Menu(menubar, tearoff=False)
        for item in content:
            if item is None:
                submenu.add_separator()
            else:
                label, name = item
                _add_command(submenu, label, name, commands)
        menubar.add_cascade(label=title, menu=submenu)
    root.configure(menu=menubar)
    return menubar


def _add_command(menu, label, name, commands):
    command = commands.get(name)
    menu.add_command(
        label=label,
        command=command,
        accelerator=ACCELERATOR_LABELS.get(name, ""),
        state="normal" if command else "disabled",
    )
