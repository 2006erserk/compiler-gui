"""Область вывода результатов языкового процессора."""

from tkinter import ttk

from .widgets import ScrolledTextFrame


class OutputPanel(ttk.Frame):
    def __init__(self, parent, font):
        super().__init__(parent)
        ttk.Label(self, text="Результаты", padding=(6, 2)).pack(side="top", fill="x")

        scrolled = ScrolledTextFrame(
            self,
            wrap="none",
            font=font,
            width=1,
            height=1,
            padx=6,
            pady=4,
            borderwidth=0,
            highlightthickness=0,
            background="#f7f7f7",
            foreground="#000000",
            selectbackground="#3875d7",
            selectforeground="#ffffff",
            inactiveselectbackground="#a9c4ec",
            exportselection=False,  # не сбрасывать выделение в редакторе
            state="disabled",       # запрет ввода
        )
        scrolled.pack(side="top", fill="both", expand=True)
        self.text = scrolled.text
        # disabled-Text не берёт фокус сам, а без фокуса не работают Ctrl+C / Ctrl+A
        self.text.bind("<Button-1>", lambda _event: self.text.focus_set(), add="+")

    def clear(self) -> None:
        self.text.configure(state="normal")
        self.text.delete("1.0", "end")
        self.text.configure(state="disabled")

    def append(self, message: str) -> None:
        """Добавить строку в конец."""
        self.text.configure(state="normal")
        self.text.insert("end", message + "\n")
        self.text.configure(state="disabled")
        self.text.see("end")

    def copy(self) -> None:
        if not self.text.tag_ranges("sel"):
            return
        selected = self.text.get("sel.first", "sel.last")
        self.text.clipboard_clear()
        self.text.clipboard_append(selected)

    def select_all(self) -> None:
        self.text.tag_add("sel", "1.0", "end-1c")
