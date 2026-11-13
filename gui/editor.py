"""Область редактирования текста."""

import tkinter as tk

from .widgets import ScrolledTextFrame

TAB_WIDTH_IN_SPACES = 4


class EditorPanel(ScrolledTextFrame):
    """Область редактирования. Если операция невозможна, она ничего не делает."""

    def __init__(self, parent, font):
        super().__init__(
            parent,
            wrap="none",
            undo=True,
            autoseparators=True,
            maxundo=-1,
            font=font,
            width=1,
            height=1,
            padx=6,
            pady=4,
            borderwidth=0,
            highlightthickness=0,
            background="#ffffff",
            foreground="#000000",
            insertbackground="#000000",
            selectbackground="#3875d7",
            selectforeground="#ffffff",
            inactiveselectbackground="#a9c4ec",
        )
        self.text.configure(tabs=(font.measure(" " * TAB_WIDTH_IN_SPACES),))

    # содержимое

    def get_text(self) -> str:
        """Без \\n, который Tk всегда добавляет в конец."""
        return self.text.get("1.0", "end-1c")

    def set_text(self, content: str) -> None:
        """Новый документ: история отмены и признак изменения сбрасываются."""
        self.text.delete("1.0", "end")
        self.text.insert("1.0", content)
        self.text.edit_reset()
        self.text.mark_set("insert", "1.0")
        self.text.see("insert")
        self.mark_saved()

    def is_modified(self) -> bool:
        return bool(self.text.edit_modified())

    def mark_saved(self) -> None:
        """Сбросить признак изменения."""
        self.text.edit_modified(False)

    def on_modified_changed(self, callback) -> None:
        """callback() — при каждой смене признака изменения."""
        self.text.bind("<<Modified>>", lambda _event: callback(), add="+")

    def focus(self) -> None:
        self.text.focus_set()

    # операции правки

    def has_selection(self) -> bool:
        return bool(self.text.tag_ranges("sel"))

    def undo(self) -> None:
        try:
            self.text.edit_undo()
        except tk.TclError:
            return  # нечего отменять
        self.text.see("insert")

    def redo(self) -> None:
        try:
            self.text.edit_redo()
        except tk.TclError:
            return  # нечего повторять
        self.text.see("insert")

    def copy(self) -> None:
        if not self.has_selection():
            return
        selected = self.text.get("sel.first", "sel.last")
        self.text.clipboard_clear()
        self.text.clipboard_append(selected)

    def cut(self) -> None:
        if not self.has_selection():
            return
        self.copy()
        self.delete_selection()

    def paste(self) -> None:
        """Выделенный фрагмент заменяется."""
        try:
            content = self.text.clipboard_get()
        except tk.TclError:
            return
        self.text.configure(autoseparators=False)
        try:
            self.text.edit_separator()
            if self.has_selection():
                self.text.delete("sel.first", "sel.last")
            self.text.insert("insert", content)
            self.text.edit_separator()
        finally:
            self.text.configure(autoseparators=True)
        self.text.see("insert")

    def delete_selection(self) -> None:
        if self.has_selection():
            self.text.delete("sel.first", "sel.last")

    def select_all(self) -> None:
        self.text.tag_add("sel", "1.0", "end-1c")
