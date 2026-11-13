"""Панель инструментов."""

from tkinter import ttk

from .shortcuts import ACCELERATOR_LABELS
from .widgets import ToolTip

TOOLBAR_LAYOUT = (
    ("new", "Создать", "Создать новый документ"),
    ("open", "Открыть", "Открыть файл"),
    ("save", "Сохранить", "Сохранить текущий документ"),
    None,
    ("undo", "Отменить", "Отменить последнее изменение"),
    ("redo", "Повторить", "Повторить отменённое изменение"),
    None,
    ("copy", "Копировать", "Копировать выделенный текст"),
    ("cut", "Вырезать", "Вырезать выделенный текст"),
    ("paste", "Вставить", "Вставить текст из буфера обмена"),
    None,
    ("run", "▶ Пуск", "Запуск синтаксического анализатора\n(будет доступен на следующем этапе)"),
    None,
    ("help", "Справка", "Вызов справки"),
    ("about", "О программе", "Информация о программе"),
)

BUTTON_GAP = 2      # расстояние между соседними кнопками, px
SEPARATOR_GAP = 6   # отступ по бокам от разделителя групп, px
EDGE_PADDING = 4    # отступ от краёв панели, px


class Toolbar(ttk.Frame):
    def __init__(self, parent, commands):
        super().__init__(parent)
        self.buttons = {}
        self._items = [] 
        self._layout = None 
        for item in TOOLBAR_LAYOUT:
            if item is None:
                self._items.append((ttk.Separator(self, orient="vertical"), True))
                continue
            name, label, tooltip = item
            command = commands.get(name)
            button = ttk.Button(
                self,
                text=label,
                command=command,
                takefocus=False,  # фокус ввода остаётся в редакторе
                style="Toolbar.TButton",
            )
            if command is None:
                button.state(["disabled"])
            accelerator = ACCELERATOR_LABELS.get(name)
            ToolTip(button, f"{tooltip} ({accelerator})" if accelerator else tooltip)
            self.buttons[name] = button
            self._items.append((button, False))

        self._row_height = max(b.winfo_reqheight() for b in self.buttons.values())
        self.configure(width=self.natural_width(), height=self._row_height + 2 * EDGE_PADDING)
        self.bind("<Configure>", lambda _event: self._arrange())

    def natural_width(self) -> int:
        """Ширина в одну строку."""
        width = 2 * EDGE_PADDING
        for widget, is_separator in self._items:
            width += widget.winfo_reqwidth() + (2 * SEPARATOR_GAP if is_separator else BUTTON_GAP)
        return width

    def min_width(self) -> int:
        """Ширина самой широкой кнопки."""
        return max(b.winfo_reqwidth() for b in self.buttons.values()) + 2 * EDGE_PADDING

    def _arrange(self):
        available = self.winfo_width() - 2 * EDGE_PADDING
        if available <= 1:
            return
        layout = []
        x, row = 0, 0
        for widget, is_separator in self._items:
            if is_separator:
                if x == 0:
                    continue  # не начинать строку с разделителя
                width = widget.winfo_reqwidth() + 2 * SEPARATOR_GAP
                x_offset = SEPARATOR_GAP
            else:
                width = widget.winfo_reqwidth() + BUTTON_GAP
                x_offset = 0
                if x > 0 and x + width > available:
                    x, row = 0, row + 1
                    # и не заканчивать
                    if layout and layout[-1][1]:
                        layout.pop()
            layout.append((widget, is_separator, x + x_offset, row))
            x += width

        if layout == self._layout:
            return
        self._layout = layout
        for widget, _ in self._items:
            widget.place_forget()
        for widget, is_separator, x, row in layout:
            y = EDGE_PADDING + row * self._row_height
            if is_separator:
                widget.place(x=EDGE_PADDING + x, y=y + 3, height=self._row_height - 6)
            else:
                widget.place(x=EDGE_PADDING + x, y=y)
        rows = layout[-1][3] + 1 if layout else 1
        self.configure(height=rows * self._row_height + 2 * EDGE_PADDING)
