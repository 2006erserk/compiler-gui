import os
import stat
import sys
import tempfile
import tkinter as tk
import unittest
from types import SimpleNamespace
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.file_io import FileOperationError, read_text_file, write_text_file  # noqa: E402
from gui import app as app_module  # noqa: E402
from gui import shortcuts  # noqa: E402
from gui.app import UNTITLED_NAME, EditorApp  # noqa: E402
from gui.dialogs import AboutDialog, HelpWindow, SaveChangesDialog, ask_save_changes  # noqa: E402
from gui.help_content import HELP_TOPICS  # noqa: E402

SAVE, DISCARD, CANCEL = SaveChangesDialog.SAVE, SaveChangesDialog.DISCARD, SaveChangesDialog.CANCEL
GO_SAMPLE = "var z complex128 = 3 + 4i\nvar a complex64 = 2.5 - 1.5i\n// комментарий\n"


class AppTestCase(unittest.TestCase):
    def setUp(self):
        self.root = tk.Tk()
        self.app = EditorApp(self.root)
        self.root.update()
        self.tmp = tempfile.TemporaryDirectory()
        self.errors = []
        patchers = (
            mock.patch.object(app_module.messagebox, "showerror",
                              side_effect=lambda *a, **k: self.errors.append(a)),
            mock.patch.object(app_module.filedialog, "askopenfilename", return_value=""),
            mock.patch.object(app_module.filedialog, "asksaveasfilename", return_value=""),
            mock.patch.object(app_module, "ask_save_changes", return_value=CANCEL),
        )
        for patcher in patchers:
            patcher.start()
            self.addCleanup(patcher.stop)

    def tearDown(self):
        try:
            self.root.destroy()
        except tk.TclError:
            pass  # окно уже закрыто тестом
        self.tmp.cleanup()

    # --- вспомогательные методы
    def path(self, name):
        return os.path.join(self.tmp.name, name)

    def make_file(self, name, content=GO_SAMPLE):
        with open(self.path(name), "w", encoding="utf-8") as f:
            f.write(content)
        return self.path(name)

    def type_text(self, text):
        """Ввод текста в позицию курсора."""
        self.app.editor.text.insert("insert", text)
        self.root.update()

    def title(self):
        self.root.update()
        return self.root.title()

    def answer_save_dialog(self, answer):
        return mock.patch.object(app_module, "ask_save_changes", return_value=answer)

    def save_dialog_returns(self, path):
        return mock.patch.object(app_module.filedialog, "asksaveasfilename", return_value=path)

    def open_dialog_returns(self, path):
        return mock.patch.object(app_module.filedialog, "askopenfilename", return_value=path)


class FileOperationsTest(AppTestCase):
    def test_initial_state(self):
        self.assertEqual(self.app.editor.get_text(), "")
        self.assertFalse(self.app.editor.is_modified())
        self.assertIn(UNTITLED_NAME, self.title())
        self.assertFalse(self.title().startswith("*"))

    def test_typing_marks_document_modified(self):
        self.type_text("var z complex128 = 3 + 4i")
        self.assertTrue(self.app.editor.is_modified())
        self.assertTrue(self.title().startswith("*"))

    def test_undo_to_saved_state_clears_modified_flag(self):
        path = self.make_file("a.go")
        self.app.load_file(path)
        self.type_text("x")
        self.assertTrue(self.app.editor.is_modified())
        self.app.commands["undo"]()
        self.root.update()
        self.assertEqual(self.app.editor.get_text(), GO_SAMPLE)
        self.assertFalse(self.app.editor.is_modified())
        self.assertFalse(self.title().startswith("*"))

    def test_open_file(self):
        path = self.make_file("decl.go")
        with self.open_dialog_returns(path):
            self.app.commands["open"]()
        self.assertEqual(self.app.editor.get_text(), GO_SAMPLE)
        self.assertFalse(self.app.editor.is_modified())
        self.assertTrue(self.title().startswith("decl.go — "))
        self.assertEqual(self.app.current_path, path)

    def test_open_crlf_and_bom_file(self):
        path = self.path("win.txt")
        with open(path, "wb") as f:
            f.write("﻿строка 1\r\nстрока 2\r\n".encode("utf-8"))
        self.assertTrue(self.app.load_file(path))
        self.assertEqual(self.app.editor.get_text(), "строка 1\nстрока 2\n")

    def test_open_cancelled_dialog_keeps_document(self):
        self.type_text("текст")
        with self.answer_save_dialog(DISCARD), self.open_dialog_returns(""):
            self.app.commands["open"]()
        self.assertEqual(self.app.editor.get_text(), "текст")

    def test_undo_after_open_does_not_erase_file_content(self):
        self.app.load_file(self.make_file("a.go"))
        self.app.commands["undo"]()
        self.assertEqual(self.app.editor.get_text(), GO_SAMPLE)

    def test_open_errors_are_reported_and_document_kept(self):
        self.type_text("мой текст")
        binary = self.path("bin.dat")
        with open(binary, "wb") as f:
            f.write(b"\xff\xfe\x00\x81\x90")
        for bad_path in (binary, self.path("missing.go"), self.tmp.name):
            self.errors.clear()
            self.assertFalse(self.app.load_file(bad_path))
            self.assertEqual(len(self.errors), 1, bad_path)
            self.assertEqual(self.app.editor.get_text(), "мой текст")
            self.assertTrue(self.app.editor.is_modified())
            self.assertIsNone(self.app.current_path)

    def test_save_new_document_asks_for_name(self):
        self.type_text("var b complex128 = 5i\nкириллица")
        target = self.path("new.go")
        with self.save_dialog_returns(target) as dialog:
            self.assertTrue(self.app.commands["save"]())
        dialog.assert_called_once()
        with open(target, encoding="utf-8") as f:
            self.assertEqual(f.read(), "var b complex128 = 5i\nкириллица")
        self.assertFalse(self.app.editor.is_modified())
        self.assertTrue(self.title().startswith("new.go — "))

    def test_save_existing_document_writes_without_dialog(self):
        path = self.make_file("a.go")
        self.app.load_file(path)
        self.type_text("// добавлено\n")
        with mock.patch.object(app_module.filedialog, "asksaveasfilename") as dialog:
            self.assertTrue(self.app.commands["save"]())
        dialog.assert_not_called()
        self.assertEqual(read_text_file(path), "// добавлено\n" + GO_SAMPLE)
        self.assertFalse(self.app.editor.is_modified())

    def test_save_as_switches_to_new_file(self):
        original = self.make_file("a.go")
        self.app.load_file(original)
        copy_path = self.path("copy.txt")
        with self.save_dialog_returns(copy_path):
            self.assertTrue(self.app.commands["save_as"]())
        self.assertEqual(self.app.current_path, copy_path)
        self.assertTrue(self.title().startswith("copy.txt — "))
        self.assertEqual(read_text_file(copy_path), GO_SAMPLE)

    def test_save_as_cancelled(self):
        self.type_text("x")
        with self.save_dialog_returns(""):
            self.assertFalse(self.app.commands["save_as"]())
        self.assertTrue(self.app.editor.is_modified())
        self.assertIsNone(self.app.current_path)

    def test_save_error_keeps_modified_state(self):
        self.type_text("x")
        with self.save_dialog_returns(self.path("no_such_dir/file.go")):
            self.assertFalse(self.app.commands["save"]())
        self.assertEqual(len(self.errors), 1)
        self.assertTrue(self.app.editor.is_modified())
        self.assertIsNone(self.app.current_path)

    @unittest.skipIf(hasattr(os, "geteuid") and os.geteuid() == 0, "root игнорирует права доступа")
    def test_save_to_read_only_file_reports_error(self):
        path = self.make_file("ro.go")
        os.chmod(path, stat.S_IRUSR)
        self.app.load_file(path)
        self.type_text("x")
        self.assertFalse(self.app.commands["save"]())
        self.assertEqual(len(self.errors), 1)
        self.assertIn("прав", self.errors[0][1])
        self.assertTrue(self.app.editor.is_modified())


class UnsavedChangesTest(AppTestCase):
    def test_new_without_changes_does_not_ask(self):
        with self.answer_save_dialog(CANCEL) as dialog:
            self.app.commands["new"]()
        dialog.assert_not_called()

    def test_open_unchanged_file_then_new_does_not_ask(self):
        self.app.load_file(self.make_file("a.go"))
        with self.answer_save_dialog(CANCEL) as dialog:
            self.app.commands["new"]()
        dialog.assert_not_called()
        self.assertEqual(self.app.editor.get_text(), "")
        self.assertIn(UNTITLED_NAME, self.title())

    def test_new_cancel_keeps_document(self):
        self.type_text("важный текст")
        with self.answer_save_dialog(CANCEL):
            self.app.commands["new"]()
        self.assertEqual(self.app.editor.get_text(), "важный текст")
        self.assertTrue(self.app.editor.is_modified())

    def test_new_discard(self):
        self.type_text("черновик")
        self.app.output.append("старое сообщение")
        with self.answer_save_dialog(DISCARD):
            self.app.commands["new"]()
        self.assertEqual(self.app.editor.get_text(), "")
        self.assertFalse(self.app.editor.is_modified())
        self.assertEqual(self.app.output.text.get("1.0", "end-1c"), "")

    def test_new_save_then_cancel_save_dialog_aborts(self):
        self.type_text("черновик")
        with self.answer_save_dialog(SAVE), self.save_dialog_returns(""):
            self.app.commands["new"]()
        self.assertEqual(self.app.editor.get_text(), "черновик")
        self.assertTrue(self.app.editor.is_modified())

    def test_new_save_success_then_creates_document(self):
        self.type_text("черновик")
        target = self.path("saved.go")
        with self.answer_save_dialog(SAVE), self.save_dialog_returns(target):
            self.app.commands["new"]()
        self.assertEqual(read_text_file(target), "черновик")
        self.assertEqual(self.app.editor.get_text(), "")
        self.assertIsNone(self.app.current_path)

    def test_open_with_failed_save_aborts(self):
        self.type_text("черновик")
        with self.answer_save_dialog(SAVE), \
                self.save_dialog_returns(self.path("missing_dir/x.go")), \
                mock.patch.object(app_module.filedialog, "askopenfilename") as open_dialog:
            self.app.commands["open"]()
        open_dialog.assert_not_called()
        self.assertEqual(self.app.editor.get_text(), "черновик")

    def test_exit_cancel_keeps_window(self):
        self.type_text("черновик")
        with self.answer_save_dialog(CANCEL):
            self.app.commands["exit"]()
        self.assertTrue(self.root.winfo_exists())

    def test_window_close_button_uses_same_check(self):
        self.type_text("черновик")
        close_handler = self.root.protocol("WM_DELETE_WINDOW")
        with self.answer_save_dialog(CANCEL) as dialog:
            self.root.tk.call(close_handler)
        dialog.assert_called_once()
        self.assertTrue(self.root.winfo_exists())

    def test_exit_discard_closes_window(self):
        self.type_text("черновик")
        with self.answer_save_dialog(DISCARD):
            self.app.commands["exit"]()
        with self.assertRaises(tk.TclError):
            self.root.winfo_exists()

    def test_exit_without_changes_closes_without_question(self):
        with self.answer_save_dialog(CANCEL) as dialog:
            self.app.commands["exit"]()
        dialog.assert_not_called()
        with self.assertRaises(tk.TclError):
            self.root.winfo_exists()

    def test_real_save_changes_dialog_buttons(self):
        for button_text, expected in (("Сохранить", SAVE), ("Не сохранять", DISCARD),
                                      ("Отмена", CANCEL)):
            def press(text=button_text):
                dialog = next(w for w in self.root.winfo_children()
                              if isinstance(w, SaveChangesDialog))
                self.assertEqual(dialog.title(), "Несохранённые изменения")
                buttons = [w for w in dialog.winfo_children()[0].winfo_children()[-1].winfo_children()]
                self.assertEqual([b.cget("text") for b in buttons],
                                 ["Сохранить", "Не сохранять", "Отмена"])
                next(b for b in buttons if b.cget("text") == text).invoke()
            self.root.after(300, press)
            self.assertEqual(ask_save_changes(self.root, "файл.go"), expected)

    def test_real_save_changes_dialog_escape_cancels(self):
        def press_escape():
            dialog = next(w for w in self.root.winfo_children() if isinstance(w, SaveChangesDialog))
            dialog.event_generate("<Escape>")
        self.root.after(300, press_escape)
        self.assertEqual(ask_save_changes(self.root, "файл.go"), CANCEL)


class EditingTest(AppTestCase):
    def setUp(self):
        super().setUp()
        self.text = self.app.editor.text
        self.app.editor.set_text("var z complex128 = 3 + 4i")

    def select(self, start, end):
        self.text.tag_remove("sel", "1.0", "end")
        self.text.tag_add("sel", start, end)
        self.text.mark_set("insert", end)

    def test_copy(self):
        self.select("1.4", "1.5")
        self.app.commands["copy"]()
        self.assertEqual(self.root.clipboard_get(), "z")
        self.assertEqual(self.app.editor.get_text(), "var z complex128 = 3 + 4i")

    def test_cut_and_undo(self):
        self.select("1.0", "1.4")
        self.app.commands["cut"]()
        self.assertEqual(self.root.clipboard_get(), "var ")
        self.assertEqual(self.app.editor.get_text(), "z complex128 = 3 + 4i")
        self.app.commands["undo"]()
        self.assertEqual(self.app.editor.get_text(), "var z complex128 = 3 + 4i")
        self.app.commands["redo"]()
        self.assertEqual(self.app.editor.get_text(), "z complex128 = 3 + 4i")

    def test_paste_at_cursor(self):
        self.root.clipboard_clear()
        self.root.clipboard_append("// комментарий ")
        self.text.mark_set("insert", "1.0")
        self.app.commands["paste"]()
        self.assertEqual(self.app.editor.get_text(), "// комментарий var z complex128 = 3 + 4i")

    def test_paste_replaces_selection_and_undo_is_one_step(self):
        self.root.clipboard_clear()
        self.root.clipboard_append("complex64")
        self.select("1.6", "1.16")
        self.app.commands["paste"]()
        self.assertEqual(self.app.editor.get_text(), "var z complex64 = 3 + 4i")
        self.app.commands["undo"]()
        self.assertEqual(self.app.editor.get_text(), "var z complex128 = 3 + 4i")

    def test_delete_selection(self):
        self.select("1.16", "1.25")
        self.app.commands["delete"]()
        self.assertEqual(self.app.editor.get_text(), "var z complex128")

    def test_select_all(self):
        self.app.editor.set_text("строка 1\nстрока 2")
        self.app.commands["select_all"]()
        self.assertEqual(self.text.get("sel.first", "sel.last"), "строка 1\nстрока 2")

    def test_operations_without_selection_or_text_do_nothing(self):
        self.root.clipboard_clear()
        self.root.clipboard_append("буфер")
        for name in ("copy", "cut", "delete"):
            self.app.commands[name]()
        self.assertEqual(self.root.clipboard_get(), "буфер")
        self.assertEqual(self.app.editor.get_text(), "var z complex128 = 3 + 4i")

        self.app.editor.set_text("")
        for name in ("undo", "redo", "copy", "cut", "delete", "select_all"):
            self.app.commands[name]()
        self.root.clipboard_clear()
        self.app.commands["paste"]()  # пустой буфер обмена
        self.assertEqual(self.app.editor.get_text(), "")
        self.assertEqual(self.errors, [])

    def test_multiple_undo_redo(self):
        self.app.editor.set_text("")
        for chunk in ("var ", "x ", "complex64"):
            self.text.insert("end", chunk)
            self.text.edit_separator()
        self.app.commands["undo"]()
        self.app.commands["undo"]()
        self.assertEqual(self.app.editor.get_text(), "var ")
        self.app.commands["redo"]()
        self.assertEqual(self.app.editor.get_text(), "var x ")


class InterfaceTest(AppTestCase):
    def menu_entries(self, menu):
        last = menu.index("end")
        entries = []
        for i in range(last + 1):
            if menu.type(i) == "separator":
                continue
            entries.append((menu.entrycget(i, "label"), menu.entrycget(i, "state")))
        return entries

    def test_menu_structure(self):
        menubar = self.root.nametowidget(self.root.cget("menu"))
        top = self.menu_entries(menubar)
        self.assertEqual([label for label, _ in top], ["Файл", "Правка", "Текст", "Пуск", "Справка"])
        self.assertEqual(dict(top)["Пуск"], "disabled")

        def submenu(label):
            for i in range(menubar.index("end") + 1):
                if menubar.type(i) == "cascade" and menubar.entrycget(i, "label") == label:
                    return self.root.nametowidget(menubar.entrycget(i, "menu"))
            raise AssertionError(label)

        self.assertEqual(self.menu_entries(submenu("Файл")), [
            ("Создать", "normal"), ("Открыть", "normal"), ("Сохранить", "normal"),
            ("Сохранить как", "normal"), ("Выход", "normal")])
        self.assertEqual(self.menu_entries(submenu("Правка")), [
            ("Отменить", "normal"), ("Повторить", "normal"), ("Вырезать", "normal"),
            ("Копировать", "normal"), ("Вставить", "normal"), ("Удалить", "normal"),
            ("Выделить всё", "normal")])
        self.assertEqual(self.menu_entries(submenu("Текст")), [
            ("Постановка задачи", "disabled"), ("Грамматика", "disabled"),
            ("Классификация грамматики", "disabled"), ("Метод анализа", "disabled"),
            ("Тестовый пример", "disabled"), ("Список литературы", "disabled"),
            ("Исходный код программы", "disabled")])
        self.assertEqual(self.menu_entries(submenu("Справка")), [
            ("Вызов справки", "normal"), ("О программе", "normal")])

    def test_toolbar_buttons(self):
        buttons = self.app.toolbar.buttons
        self.assertEqual(set(buttons), {"new", "open", "save", "undo", "redo", "copy", "cut",
                                        "paste", "run", "help", "about"})
        self.assertTrue(buttons["run"].instate(["disabled"]))
        for name, button in buttons.items():
            if name != "run":
                self.assertFalse(button.instate(["disabled"]), name)

    def test_toolbar_calls_same_handlers_as_menu(self):
        self.app.editor.set_text("abc")
        self.app.editor.text.tag_add("sel", "1.0", "1.1")
        self.app.toolbar.buttons["cut"].invoke()
        self.assertEqual(self.app.editor.get_text(), "bc")
        self.app.toolbar.buttons["undo"].invoke()
        self.assertEqual(self.app.editor.get_text(), "abc")
        self.app.toolbar.buttons["redo"].invoke()
        self.assertEqual(self.app.editor.get_text(), "bc")
        self.app.toolbar.buttons["paste"].invoke()
        self.assertEqual(self.app.editor.get_text(), "abc")
        target = self.path("tb.go")
        with self.save_dialog_returns(target):
            self.app.toolbar.buttons["save"].invoke()
        self.assertEqual(read_text_file(target), "abc")
        with self.open_dialog_returns(self.make_file("o.go", "opened")):
            self.app.toolbar.buttons["open"].invoke()
        self.assertEqual(self.app.editor.get_text(), "opened")
        self.app.toolbar.buttons["new"].invoke()
        self.assertEqual(self.app.editor.get_text(), "")

    def test_output_is_read_only(self):
        output = self.app.output
        output.text.insert("end", "попытка ввода")
        output.text.delete("1.0", "end")
        self.assertEqual(output.text.get("1.0", "end-1c"), "")
        output.append("Сообщение 1")
        output.append("Сообщение 2")
        self.assertEqual(output.text.get("1.0", "end-1c"), "Сообщение 1\nСообщение 2\n")
        output.text.insert("1.0", "x")  # ручной ввод по-прежнему запрещён
        self.assertEqual(output.text.get("1.0", "end-1c"), "Сообщение 1\nСообщение 2\n")
        self.assertEqual(str(output.text.cget("state")), "disabled")
        output.clear()
        self.assertEqual(output.text.get("1.0", "end-1c"), "")

    def test_typing_into_output_via_keyboard_events_is_ignored(self):
        output = self.app.output.text
        output.focus_force()
        self.root.update()
        output.event_generate("<KeyPress>", keysym="a", keycode=38)
        self.root.update()
        self.assertEqual(output.get("1.0", "end-1c"), "")

    def test_help_window(self):
        self.app.commands["help"]()
        self.root.update()
        help_window = self.app._help_window
        self.assertIsInstance(help_window, HelpWindow)
        self.assertEqual(help_window.topics.size(), len(HELP_TOPICS))
        content = help_window.text.get("1.0", "end")
        for title, _ in HELP_TOPICS:
            self.assertIn(title, content)
        help_window.topics.selection_clear(0, "end")
        help_window.topics.selection_set(len(HELP_TOPICS) - 1)
        help_window.topics.event_generate("<<ListboxSelect>>")
        self.root.update()
        # повторный вызов не создаёт второе окно
        self.app.commands["help"]()
        self.assertIs(self.app._help_window, help_window)
        help_window.destroy()
        self.app.commands["help"]()
        self.assertIsNot(self.app._help_window, help_window)

    def test_about_window(self):
        self.app.commands["about"]()
        self.root.update()
        about = next(w for w in self.root.winfo_children() if isinstance(w, AboutDialog))
        labels = []

        def collect(widget):
            for child in widget.winfo_children():
                try:
                    labels.append(str(child.cget("text")))
                except tk.TclError:
                    pass
                collect(child)
        collect(about)
        joined = "\n".join(labels)
        for expected in ("Go Complex Declaration Editor", "Версия", "Python 3",
                         "Методы трансляции и компиляции"):
            self.assertIn(expected, joined)
        about.destroy()

    def test_window_resizing_and_sash(self):
        self.root.geometry("900x600")
        self.root.update()
        editor_h, output_h = self.app.editor.winfo_height(), self.app.output.winfo_height()
        self.root.geometry("1100x800")
        self.root.update()
        self.assertGreater(self.app.editor.winfo_height(), editor_h)
        self.assertGreater(self.app.output.winfo_height(), output_h)
        self.assertEqual(self.app.paned.winfo_width(), self.root.winfo_width())

        self.app.paned.sashpos(0, 200)
        self.root.update()
        self.assertLess(abs(self.app.editor.winfo_height() - 200), 5)
        # Попытка полностью скрыть область результатов ограничивается.
        self.app.paned.sashpos(0, 10_000)
        self.app._keep_panes_visible()
        self.root.update()
        self.assertGreaterEqual(self.app.output.winfo_height(), app_module.MIN_PANE_HEIGHT - 5)

        min_width, min_height = self.root.minsize()
        self.assertGreater(min_width, 0)
        self.assertGreater(min_height, 0)

    def test_toolbar_wraps_in_narrow_window(self):
        self.root.geometry("600x500")
        self.root.update()
        toolbar = self.app.toolbar
        for button in toolbar.buttons.values():
            self.assertTrue(button.winfo_ismapped())
            self.assertLessEqual(button.winfo_x() + button.winfo_width(), toolbar.winfo_width())
        self.assertGreater(toolbar.winfo_height(), toolbar._row_height + 5)


class ShortcutsTest(AppTestCase):
    def event(self, keysym, keycode, shift=False):
        return SimpleNamespace(keysym=keysym, keycode=keycode, state=0x4 | (0x1 if shift else 0))

    def test_latin_and_cyrillic_layouts(self):
        cases = [
            (("s", 39), "save"), (("Cyrillic_yeru", 39), "save"),
            (("S", 39, True), "save_as"), (("Cyrillic_YERU", 39, True), "save_as"),
            (("c", 54), "copy"), (("Cyrillic_es", 54), "copy"),
            (("v", 55), "paste"), (("x", 53), "cut"), (("a", 38), "select_all"),
            (("z", 52), "undo"), (("Z", 52, True), "redo"), (("y", 29), "redo"),
            (("n", 57), "new"), (("o", 32), "open"), (("q", 24), None),
            (("Control_L", 37), None),
        ]
        for args, expected in cases:
            self.assertEqual(shortcuts.command_for_event(self.event(*args)), expected, args)

    def test_editor_hotkeys_trigger_commands(self):
        # Напрямую: event_generate для клавиш зависит от фокуса на рабочем столе.
        text = self.app.editor.text
        self.assertTrue(text.bind("<Control-KeyPress>"))
        self.assertTrue(self.root.bind("<Control-KeyPress>"))
        self.app.editor.set_text("abc")
        press = self.app._on_editor_control_key

        self.assertEqual(press(self.event("a", 38)), "break")
        self.assertEqual(text.get("sel.first", "sel.last"), "abc")
        self.assertEqual(press(self.event("Cyrillic_che", 53)), "break")  # Ctrl+X, русская раскладка
        self.assertEqual(self.app.editor.get_text(), "")
        self.assertEqual(self.root.clipboard_get(), "abc")
        self.assertEqual(press(self.event("Cyrillic_ya", 52)), "break")   # Ctrl+Z
        self.assertEqual(self.app.editor.get_text(), "abc")
        # Ctrl+O в стандартном tk.Text вставляет перевод строки — здесь открывается диалог.
        with self.open_dialog_returns("") as dialog:
            self.assertEqual(press(self.event("o", 32)), "break")
        dialog.assert_called_once()
        self.assertEqual(self.app.editor.get_text(), "abc")
        # Незнакомые сочетания передаются стандартной обработке Tk.
        self.assertIsNone(press(self.event("q", 24)))

    def test_window_hotkeys_outside_editor(self):
        handler = self.app._on_window_control_key
        with self.open_dialog_returns("") as dialog:
            self.assertEqual(handler(self.event("o", 32)), "break")
        dialog.assert_called_once()
        # Команды правки вне редактора не перехватываются.
        self.assertIsNone(handler(self.event("v", 55)))


class FileIoTest(unittest.TestCase):
    def test_round_trip_utf8(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "x.go")
            text = "var z complex128 = 3 + 4i\n// Привет\n"
            write_text_file(path, text)
            with open(path, "rb") as f:
                self.assertEqual(f.read(), text.encode("utf-8"))
            self.assertEqual(read_text_file(path), text)

    def test_errors(self):
        with self.assertRaises(FileOperationError):
            read_text_file("/nonexistent/file.go")
        with self.assertRaises(FileOperationError):
            write_text_file("/nonexistent/dir/file.go", "x")


if __name__ == "__main__":
    unittest.main()
