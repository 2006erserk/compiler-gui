"""Диалоговые окна: несохранённые изменения, «О программе», справка."""

import platform
import tkinter as tk
from tkinter import font as tkfont
from tkinter import ttk

from . import app_info
from .help_content import HELP_TOPICS
from .widgets import ScrolledTextFrame


def _place_over(window, parent):
    """По центру над родителем."""
    window.update_idletasks()
    x = parent.winfo_rootx() + (parent.winfo_width() - window.winfo_reqwidth()) // 2
    y = parent.winfo_rooty() + (parent.winfo_height() - window.winfo_reqheight()) // 3
    window.geometry(f"+{max(x, 0)}+{max(y, 0)}")


def _make_modal(window, parent):
    """Пока окно открыто, главное окно недоступно."""
    window.transient(parent)
    if parent.winfo_viewable():
        window.wait_visibility()
        try:
            window.grab_set()
        except tk.TclError:
            pass  # без захвата ввода окно всё равно работает


def _bold_font(size_delta=0):
    font = tkfont.nametofont("TkDefaultFont").copy()
    font.configure(weight="bold", size=font.cget("size") + size_delta)
    return font


# ------------------------------------------------- несохранённые изменения

class SaveChangesDialog(tk.Toplevel):
    """«Сохранить изменения?»: Сохранить / Не сохранять / Отмена."""

    SAVE = "save"
    DISCARD = "discard"
    CANCEL = "cancel"

    def __init__(self, parent, document_name: str):
        super().__init__(parent)
        self.result = self.CANCEL
        self.title("Несохранённые изменения")
        self.resizable(False, False)

        self._title_font = _bold_font()
        body = ttk.Frame(self, padding=16)
        body.pack(fill="both", expand=True)

        ttk.Label(body, image="::tk::icons::warning").grid(
            row=0, column=0, rowspan=2, sticky="n", padx=(0, 14))
        ttk.Label(body, text=f"Документ «{document_name}» был изменён.",
                  font=self._title_font).grid(row=0, column=1, sticky="w")
        ttk.Label(body, justify="left", wraplength=380,
                  text="Сохранить изменения?\n"
                       "Если не сохранить документ, внесённые изменения будут потеряны.",
                  ).grid(row=1, column=1, sticky="w", pady=(6, 0))

        buttons = ttk.Frame(body)
        buttons.grid(row=2, column=0, columnspan=2, sticky="e", pady=(18, 0))
        save_button = ttk.Button(buttons, text="Сохранить", default="active",
                                 command=lambda: self._choose(self.SAVE))
        save_button.pack(side="left", padx=3)
        ttk.Button(buttons, text="Не сохранять",
                   command=lambda: self._choose(self.DISCARD)).pack(side="left", padx=3)
        ttk.Button(buttons, text="Отмена",
                   command=lambda: self._choose(self.CANCEL)).pack(side="left", padx=3)

        self.protocol("WM_DELETE_WINDOW", lambda: self._choose(self.CANCEL))
        self.bind("<Escape>", lambda _event: self._choose(self.CANCEL))
        self.bind("<Return>", self._invoke_focused_button)

        _place_over(self, parent)
        _make_modal(self, parent)
        save_button.focus_set()

    def _invoke_focused_button(self, _event=None):
        widget = self.focus_get()
        if isinstance(widget, ttk.Button):
            widget.invoke()

    def _choose(self, result):
        self.result = result
        self.destroy()


def ask_save_changes(parent, document_name: str) -> str:
    """Возвращает SAVE, DISCARD или CANCEL."""
    dialog = SaveChangesDialog(parent, document_name)
    parent.wait_window(dialog)
    return dialog.result


# ------------------------------------------------------------ О программе

class AboutDialog(tk.Toplevel):
    """Окно «О программе»."""

    def __init__(self, parent):
        super().__init__(parent)
        self.title("О программе")
        self.resizable(False, False)

        self._title_font = _bold_font(size_delta=4)
        body = ttk.Frame(self, padding=20)
        body.pack(fill="both", expand=True)

        ttk.Label(body, text=app_info.APP_NAME, font=self._title_font).pack(anchor="w")
        ttk.Label(body, text=f"Версия {app_info.APP_VERSION}").pack(anchor="w", pady=(2, 12))

        ttk.Label(body, text=app_info.APP_PURPOSE, wraplength=440, justify="left").pack(anchor="w")
        ttk.Label(body, text=app_info.COURSE_INFO, wraplength=440, justify="left").pack(
            anchor="w", pady=(8, 12))

        details = ttk.Frame(body)
        details.pack(anchor="w")
        rows = (
            ("Язык реализации:", app_info.IMPLEMENTATION_LANGUAGE),
            ("Среда выполнения:",
             f"Python {platform.python_version()}, Tk {self.tk.call('info', 'patchlevel')}"),
            ("Автор:", app_info.AUTHOR),
            ("Группа:", app_info.GROUP),
        )
        for row, (caption, value) in enumerate(rows):
            ttk.Label(details, text=caption).grid(row=row, column=0, sticky="w", padx=(0, 10))
            ttk.Label(details, text=value).grid(row=row, column=1, sticky="w")

        ok_button = ttk.Button(body, text="OK", default="active", command=self.destroy)
        ok_button.pack(anchor="e", pady=(16, 0))

        self.bind("<Return>", lambda _event: self.destroy())
        self.bind("<Escape>", lambda _event: self.destroy())
        _place_over(self, parent)
        _make_modal(self, parent)
        ok_button.focus_set()


# ------------------------------------------------------------------ Справка

class HelpWindow(tk.Toplevel):
    """Немодальное окно справки: разделы слева, текст справа."""

    def __init__(self, parent, text_font):
        super().__init__(parent)
        self.title(f"Справка — {app_info.APP_NAME}")
        self.geometry("900x620")
        self.minsize(520, 340)

        paned = ttk.PanedWindow(self, orient="horizontal")
        paned.pack(fill="both", expand=True)

        topics_frame = ttk.Frame(paned, padding=(6, 6, 0, 6))
        ttk.Label(topics_frame, text="Разделы").pack(anchor="w", pady=(0, 4))
        self.topics = tk.Listbox(topics_frame, activestyle="none", exportselection=False,
                                 width=32, borderwidth=1, relief="solid", highlightthickness=0)
        self.topics.pack(fill="both", expand=True)
        paned.add(topics_frame, weight=0)

        self._fonts = {
            "body": tkfont.nametofont("TkDefaultFont").copy(),
            "title": _bold_font(size_delta=3),
            "code": text_font,
        }

        content = ScrolledTextFrame(paned, wrap="word", width=1, height=1, padx=16, pady=10,
                                    font=self._fonts["body"],
                                    borderwidth=1, relief="solid", highlightthickness=0,
                                    background="#ffffff", foreground="#000000",
                                    exportselection=False, cursor="arrow")
        paned.add(content, weight=1)
        self.text = content.text

        self._configure_tags()
        self._fill_content()

        self.topics.bind("<<ListboxSelect>>", self._on_topic_selected)
        self.bind("<Escape>", lambda _event: self.destroy())
        self.topics.selection_set(0)
        self.topics.focus_set()

    def _configure_tags(self):
        self.text.tag_configure("title", font=self._fonts["title"], spacing1=14, spacing3=8)
        self.text.tag_configure("paragraph", spacing3=6)
        self.text.tag_configure("bullet", lmargin1=12, lmargin2=28, spacing3=3)
        self.text.tag_configure("code", font=self._fonts["code"], lmargin1=24, lmargin2=24,
                                background="#f2f2f2")

    def _fill_content(self):
        for index, (title, body) in enumerate(HELP_TOPICS):
            self.topics.insert("end", title)
            self.text.mark_set(f"topic{index}", "end-1c")
            self.text.mark_gravity(f"topic{index}", "left")
            self.text.insert("end", title + "\n", "title")
            for line in body.strip("\n").split("\n"):
                if line.startswith("    "):
                    tag = "code"
                elif line.startswith("• "):
                    tag = "bullet"
                else:
                    tag = "paragraph"
                self.text.insert("end", line + "\n", tag)
        self.text.configure(state="disabled")

    def _on_topic_selected(self, _event=None):
        selection = self.topics.curselection()
        if selection:
            self.text.yview(f"topic{selection[0]}")

    def show(self):
        """Поднять уже открытое окно."""
        self.deiconify()
        self.lift()
        self.focus_set()
