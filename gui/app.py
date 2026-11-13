"""Главное окно: сборка интерфейса, команды и работа с документом."""

import os
import traceback
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from tkinter import font as tkfont

from core.file_io import FileOperationError, read_text_file, write_text_file

from . import app_info, shortcuts
from .dialogs import AboutDialog, HelpWindow, SaveChangesDialog, ask_save_changes
from .editor import EditorPanel
from .menu import build_menubar
from .output import OutputPanel
from .toolbar import Toolbar

UNTITLED_NAME = "Новый документ"

OPEN_FILE_TYPES = (
    ("Файлы Go и текстовые файлы", ("*.go", "*.txt")),
    ("Файлы Go", "*.go"),
    ("Текстовые файлы", "*.txt"),
    ("Все файлы", "*"),
)
SAVE_FILE_TYPES = (
    ("Файлы Go", "*.go"),
    ("Текстовые файлы", "*.txt"),
    ("Все файлы", "*"),
)

INITIAL_WIDTH = 1000          # увеличивается до ширины панели инструментов
INITIAL_HEIGHT = 680
MIN_WINDOW_WIDTH = 560
MIN_WINDOW_HEIGHT = 420
MIN_PANE_HEIGHT = 60          # редактор и результаты не схлопываются меньше этого
SASH_THICKNESS = 7
INITIAL_EDITOR_SHARE = 0.68   # начальная доля высоты редактора


class EditorApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.current_path = None   # None — документ ещё не сохранялся
        self._last_directory = os.getcwd()
        self._help_window = None

        # Общие обработчики для меню, панели и горячих клавиш.
        # None или отсутствие ключа — команда неактивна.
        self.commands = {
            # Файл
            "new": self.new_document,
            "open": self.open_document,
            "save": self.save_document,
            "save_as": self.save_document_as,
            "exit": self.exit_app,
            # Правка
            "undo": self._editor_action(lambda: self.editor.undo()),
            "redo": self._editor_action(lambda: self.editor.redo()),
            "cut": self._editor_action(lambda: self.editor.cut()),
            "copy": self._editor_action(lambda: self.editor.copy()),
            "paste": self._editor_action(lambda: self.editor.paste()),
            "delete": self._editor_action(lambda: self.editor.delete_selection()),
            "select_all": self._editor_action(lambda: self.editor.select_all()),
            "run": None,
            "help": self.show_help,
            "about": self.show_about,
        }

        self._setup_window()
        self._build_ui()
        self._bind_shortcuts()
        self.update_title()
        self.editor.focus()

    # построение окна

    def _setup_window(self):
        self.root.protocol("WM_DELETE_WINDOW", self.exit_app)
        self.root.report_callback_exception = self._report_unexpected_error

        style = ttk.Style(self.root)
        if "clam" in style.theme_names():
            style.theme_use("clam")
        style.configure("Toolbar.TButton", padding=(6, 3), width=0)
        style.configure("TPanedwindow", background="#c8c8c8")
        style.configure("Sash", sashthickness=SASH_THICKNESS, gripcount=12)

        self.text_font = tkfont.nametofont("TkFixedFont").copy()
        self.text_font.configure(size=11)

    def _build_ui(self):
        build_menubar(self.root, self.commands)

        self.toolbar = Toolbar(self.root, self.commands)
        self.toolbar.pack(side="top", fill="x")
        ttk.Separator(self.root, orient="horizontal").pack(side="top", fill="x")

        self.paned = ttk.PanedWindow(self.root, orient="vertical")
        self.paned.pack(side="top", fill="both", expand=True)

        self.editor = EditorPanel(self.paned, self.text_font)
        self.output = OutputPanel(self.paned, self.text_font)
        self.paned.add(self.editor, weight=3)  # при растягивании место делится 3:1
        self.paned.add(self.output, weight=1)

        self.editor.on_modified_changed(self.update_title)

        screen_width = self.root.winfo_screenwidth()
        width = min(max(INITIAL_WIDTH, self.toolbar.natural_width()), screen_width - 80)
        self.root.geometry(f"{width}x{INITIAL_HEIGHT}")
        self.root.minsize(max(MIN_WINDOW_WIDTH, self.toolbar.min_width()), MIN_WINDOW_HEIGHT)

        for sequence in ("<B1-Motion>", "<ButtonRelease-1>"):
            self.paned.bind(sequence, lambda _event: self.root.after_idle(self._keep_panes_visible),
                            add="+")
        self.root.after_idle(self._set_initial_sash_position)

    def _set_initial_sash_position(self):
        height = self.paned.winfo_height()
        if height > 1:
            self.paned.sashpos(0, int(height * INITIAL_EDITOR_SHARE))

    def _keep_panes_visible(self):
        height = self.paned.winfo_height()
        position = self.paned.sashpos(0)
        limited = max(MIN_PANE_HEIGHT, min(position, height - MIN_PANE_HEIGHT - SASH_THICKNESS))
        if limited != position:
            self.paned.sashpos(0, limited)

    def _bind_shortcuts(self):
        self.editor.text.bind("<Control-KeyPress>", self._on_editor_control_key)
        self.output.text.bind("<Control-KeyPress>", self._on_output_control_key)
        self.root.bind("<Control-KeyPress>", self._on_window_control_key)
        self.root.bind("<F1>", lambda _event: self.show_help())

    def _on_editor_control_key(self, event):
        name = shortcuts.command_for_event(event)
        if name is None:
            return None
        self.commands[name]()
        return "break"

    def _on_output_control_key(self, event):
        name = shortcuts.command_for_event(event)
        if name == "copy":
            self.output.copy()
        elif name == "select_all":
            self.output.select_all()
        elif name in shortcuts.WINDOW_COMMANDS:
            self.commands[name]()
        else:
            return None
        return "break"

    def _on_window_control_key(self, event):
        name = shortcuts.command_for_event(event)
        if name in shortcuts.WINDOW_COMMANDS:
            self.commands[name]()
            return "break"
        return None

    # документ

    @property
    def document_name(self) -> str:
        if self.current_path is None:
            return UNTITLED_NAME
        return os.path.basename(self.current_path)

    def update_title(self):
        marker = "*" if self.editor.is_modified() else ""
        self.root.title(f"{marker}{self.document_name} — {app_info.APP_NAME}")

    def confirm_discard_changes(self) -> bool:
        """True — можно продолжать: изменений нет, они сохранены или отброшены."""
        if not self.editor.is_modified():
            return True
        answer = ask_save_changes(self.root, self.document_name)
        if answer == SaveChangesDialog.SAVE:
            return self.save_document()
        return answer == SaveChangesDialog.DISCARD

    # меню «Файл»

    def new_document(self):
        if not self.confirm_discard_changes():
            return
        self.editor.set_text("")
        self.current_path = None
        self.output.clear()
        self.update_title()
        self.editor.focus()

    def open_document(self):
        if not self.confirm_discard_changes():
            return
        path = filedialog.askopenfilename(
            parent=self.root,
            title="Открыть",
            initialdir=self._last_directory,
            filetypes=OPEN_FILE_TYPES,
        )
        if path:
            self.load_file(path)
        self.editor.focus()

    def load_file(self, path: str) -> bool:
        """При ошибке текущий документ не меняется."""
        try:
            content = read_text_file(path)
        except FileOperationError as error:
            messagebox.showerror("Ошибка открытия файла", str(error), parent=self.root)
            return False
        self.editor.set_text(content)
        self._set_current_path(path)
        self.output.clear()
        return True

    def save_document(self) -> bool:
        """True, если сохранено."""
        if self.current_path is None:
            return self.save_document_as()
        return self._write_document(self.current_path)

    def save_document_as(self) -> bool:
        """True, если сохранено."""
        if self.current_path is None:
            initial_directory = self._last_directory
            initial_file = "untitled.go"
        else:
            initial_directory, initial_file = os.path.split(self.current_path)
        path = filedialog.asksaveasfilename(
            parent=self.root,
            title="Сохранить как",
            initialdir=initial_directory,
            initialfile=initial_file,
            filetypes=SAVE_FILE_TYPES,
        )
        if not path:
            return False  # диалог отменён
        return self._write_document(path)

    def _write_document(self, path: str) -> bool:
        try:
            write_text_file(path, self.editor.get_text())
        except FileOperationError as error:
            messagebox.showerror("Ошибка сохранения файла", str(error), parent=self.root)
            return False
        self.editor.mark_saved()
        self._set_current_path(path)
        return True

    def _set_current_path(self, path: str):
        self.current_path = os.path.abspath(path)
        self._last_directory = os.path.dirname(self.current_path)
        self.update_title()

    def exit_app(self):
        if self.confirm_discard_changes():
            self.root.destroy()

    # меню «Правка»

    def _editor_action(self, action):
        """После операции фокус возвращается в редактор."""
        def run():
            action()
            self.editor.focus()
        return run

    # меню «Справка»

    def show_help(self):
        if self._help_window is not None and self._help_window.winfo_exists():
            self._help_window.show()
        else:
            self._help_window = HelpWindow(self.root, self.text_font)

    def show_about(self):
        AboutDialog(self.root)

    # прочее

    def _report_unexpected_error(self, exc_type, exc_value, exc_traceback):
        """Непредвиденное исключение: показать ошибку, не падая."""
        traceback.print_exception(exc_type, exc_value, exc_traceback)
        messagebox.showerror(
            "Непредвиденная ошибка",
            f"Во время выполнения команды произошла ошибка:\n{exc_value}\n\n"
            "Программа продолжит работу. Рекомендуется сохранить документ.",
            parent=self.root,
        )
