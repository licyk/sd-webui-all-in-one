"""Implementation grouped from the former ``version_gui.py`` module."""

from __future__ import annotations

import sys
import tkinter as tk
from tkinter import (
    ttk,
)
from typing import (
    Any,
    Callable,
)


class EnhancedEntry(ttk.Frame):
    """
    增强单行输入框

    在 ttk.Entry 外层增加清除按钮、右键菜单和统一的选区编辑行为。
    """

    _CONTROL_MASK = 0x0004

    def __init__(
        self,
        master: tk.Misc,
        textvariable: tk.Variable | None = None,
        placeholder: str | None = None,
        show_clear_button: bool = True,
        **kwargs: Any,
    ) -> None:
        super().__init__(master)
        kwargs.setdefault("exportselection", False)
        self.placeholder = placeholder
        self.show_clear_button = show_clear_button
        self.variable = textvariable if textvariable is not None else tk.StringVar(master=self)
        self.entry = ttk.Entry(self, textvariable=self.variable, **kwargs)
        self.entry.pack(fill=tk.X, expand=True)
        self.clear_button = ttk.Label(self, text="x", width=2, anchor=tk.CENTER, cursor="hand2")
        self.context_menu = tk.Menu(self, tearoff=False)
        self.context_menu.add_command(label="剪切", command=self._cut_selection)
        self.context_menu.add_command(label="复制", command=self._copy_selection)
        self.context_menu.add_command(label="粘贴", command=self._paste_clipboard)
        self._trace_id: str | None = None

        if self.placeholder and not str(self.variable.get()):
            self.variable.set(self.placeholder)
        self._trace_id = self.variable.trace_add("write", lambda *_args: self._sync_clear_button())
        self._install_bindings()
        self._sync_clear_button()

    def bind(  # type: ignore[override]  # ty: ignore[invalid-method-override]
        self,
        sequence: str | None = None,
        func: Callable[[tk.Event], object] | None = None,
        add: bool | str | None = None,
    ) -> str | None:
        """
        将输入相关事件绑定到底层 Entry，保留复合控件的透明使用方式。

        Args:
            sequence (str | None):
                Tk 事件序列。
            func (Callable[[tk.Event], object] | None):
                事件回调。
            add (bool | str | None):
                是否追加绑定, 默认为追加以保留内置输入行为。

        Returns:
            str | None: Tk 绑定 ID。
        """
        add_arg = "+" if add is None else add
        return self.entry.bind(sequence, func, add_arg)  # ty: ignore[no-matching-overload]

    def get(self) -> str:
        """
        获取输入框文本。

        Returns:
            str: 输入框当前文本。
        """
        return self.entry.get()

    def insert(self, index: int | str, string: str) -> None:
        """
        在指定位置插入文本。

        Args:
            index (int | str):
                插入位置。
            string (str):
                要插入的文本。
        """
        self.entry.insert(index, string)
        self._sync_clear_button()

    def delete(self, first: int | str, last: int | str | None = None) -> None:
        """
        删除指定范围内的文本。

        Args:
            first (int | str):
                起始位置。
            last (int | str | None):
                结束位置, 为 None 时只删除起始位置字符。
        """
        if last is None:
            self.entry.delete(first)
        else:
            self.entry.delete(first, last)
        self._sync_clear_button()

    def index(self, index: int | str) -> int:
        """
        返回指定索引对应的位置。

        Args:
            index (int | str):
                Tk 输入框索引。

        Returns:
            int: 解析后的数字索引。
        """
        return self.entry.index(index)

    def icursor(self, index: int | str) -> None:
        """
        移动输入光标到指定位置。

        Args:
            index (int | str):
                目标光标位置。
        """
        self.entry.icursor(index)

    def selection_range(self, start: int | str, end: int | str) -> None:
        """
        选中指定范围内的文本。

        Args:
            start (int | str):
                选区起始位置。
            end (int | str):
                选区结束位置。
        """
        self.entry.selection_range(start, end)

    def selection_clear(self) -> None:  # ty: ignore[invalid-method-override]
        """清除输入框文本选区。"""
        self.entry.selection_clear()

    def selection_present(self) -> bool:
        """
        检查输入框是否存在文本选区。

        Returns:
            bool: 是否存在文本选区。
        """
        return bool(self.entry.selection_present())

    def focus_set(self) -> None:
        """将键盘焦点移动到底层输入框。"""
        self.entry.focus_set()

    def focus(self) -> None:
        """将键盘焦点移动到底层输入框。"""
        self.entry.focus()

    def destroy(self) -> None:
        """销毁输入框并移除变量监听。"""
        if self._trace_id is not None:
            try:
                self.variable.trace_remove("write", self._trace_id)
            except tk.TclError:
                pass
            self._trace_id = None
        super().destroy()

    def _install_bindings(self) -> None:
        if sys.platform == "darwin":
            for sequence in ("<Command-KeyPress-a>", "<Command-KeyPress-A>"):
                self.entry.bind(sequence, self._select_all)
        self.entry.bind("<Delete>", self._delete_selected_text)
        self.entry.bind("<BackSpace>", self._delete_selected_text)
        self.entry.bind("<KeyPress>", self._replace_selection_on_keypress, add="+")
        self.entry.bind("<FocusIn>", self._clear_placeholder, add="+")
        self.entry.bind("<FocusOut>", self._restore_placeholder, add="+")
        self.entry.bind("<Button-3>", self._show_context_menu, add="+")
        self.entry.bind("<Control-Button-1>", self._show_context_menu, add="+")
        self.clear_button.bind("<Button-1>", self._clear_text)

    def _select_all(self, _event: tk.Event) -> str:
        self.entry.selection_range(0, tk.END)
        self.entry.icursor(tk.END)
        return "break"

    def _delete_selected_text(self, _event: tk.Event) -> str | None:
        if not self._has_selection():
            return None
        self._delete_selection()
        self._emit_changed()
        return "break"

    def _replace_selection_on_keypress(self, event: tk.Event) -> str | None:
        if self._is_select_all_event(event):
            return self._select_all(event)
        char = getattr(event, "char", "")
        if not char or ord(char[0]) < 32 or not self._is_editable():
            return None
        if self._placeholder_active():
            self.variable.set("")
        if not self._has_selection():
            return None
        self._delete_selection()
        self.entry.insert(tk.INSERT, char)
        self._emit_changed()
        return "break"

    @classmethod
    def _is_select_all_event(cls, event: tk.Event) -> bool:
        keysym = str(getattr(event, "keysym", "")).lower()
        if keysym != "a":
            return False
        try:
            state = int(getattr(event, "state", 0) or 0)
        except (TypeError, ValueError):
            return False
        return bool(state & cls._CONTROL_MASK)

    def _clear_placeholder(self, _event: tk.Event) -> None:
        if self._placeholder_active():
            self.variable.set("")

    def _restore_placeholder(self, _event: tk.Event) -> None:
        if self.placeholder and not str(self.variable.get()).strip():
            self.variable.set(self.placeholder)

    def _clear_text(self, _event: tk.Event | None = None) -> str:
        if not self._is_editable():
            return "break"
        self.variable.set("")
        self.entry.focus_set()
        self._emit_changed()
        return "break"

    def _show_context_menu(self, event: tk.Event) -> str:
        self._refresh_context_menu()
        try:
            self.context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.context_menu.grab_release()
        return "break"

    def _refresh_context_menu(self) -> None:
        has_selection = self._has_selection()
        editable = self._is_editable()
        can_paste = editable and self._clipboard_text() is not None
        self.context_menu.entryconfigure(0, state=tk.NORMAL if editable and has_selection else tk.DISABLED)
        self.context_menu.entryconfigure(1, state=tk.NORMAL if has_selection else tk.DISABLED)
        self.context_menu.entryconfigure(2, state=tk.NORMAL if can_paste else tk.DISABLED)

    def _cut_selection(self) -> None:
        if not self._is_editable() or not self._copy_selection():
            return
        self._delete_selection()
        self._emit_changed()

    def _copy_selection(self) -> bool:
        text = self._selected_text()
        if text is None:
            return False
        self.entry.clipboard_clear()
        self.entry.clipboard_append(text)
        return True

    def _paste_clipboard(self) -> None:
        if not self._is_editable():
            return
        text = self._clipboard_text()
        if text is None:
            return
        if self._placeholder_active():
            self.variable.set("")
        if self._has_selection():
            self._delete_selection()
        self.entry.insert(tk.INSERT, text)
        self._emit_changed()

    def _has_selection(self) -> bool:
        try:
            return bool(self.entry.selection_present())
        except tk.TclError:
            return False

    def _selected_text(self) -> str | None:
        try:
            return self.entry.get()[self.entry.index(tk.SEL_FIRST) : self.entry.index(tk.SEL_LAST)]
        except tk.TclError:
            return None

    def _delete_selection(self) -> None:
        self.entry.delete(tk.SEL_FIRST, tk.SEL_LAST)

    def _clipboard_text(self) -> str | None:
        try:
            return self.entry.clipboard_get()
        except tk.TclError:
            return None

    def _is_editable(self) -> bool:
        states = set(self.entry.state())
        return "disabled" not in states and "readonly" not in states

    def _placeholder_active(self) -> bool:
        return self.placeholder is not None and str(self.variable.get()) == self.placeholder

    def _sync_clear_button(self) -> None:
        value = str(self.variable.get())
        should_show = self.show_clear_button and self._is_editable() and bool(value) and not self._placeholder_active()
        if should_show:
            self.clear_button.place(relx=1.0, rely=0.5, x=-8, anchor=tk.E)
        else:
            self.clear_button.place_forget()

    def _emit_changed(self) -> None:
        self._sync_clear_button()
        self.entry.event_generate("<<EnhancedEntryChanged>>")


def install_text_context_menu(widget: tk.Text, editable: bool = True) -> tk.Menu:
    """
    为多行文本框安装剪切、复制、粘贴右键菜单。

    Args:
        widget (tk.Text):
            要安装右键菜单的多行文本框。
        editable (bool):
            是否允许剪切和粘贴。

    Returns:
        tk.Menu: 已安装的右键菜单。
    """

    menu = tk.Menu(widget, tearoff=False)

    def _has_selection() -> bool:
        try:
            widget.index(tk.SEL_FIRST)
            widget.index(tk.SEL_LAST)
            return True
        except tk.TclError:
            return False

    def _selected_text() -> str | None:
        try:
            return widget.get(tk.SEL_FIRST, tk.SEL_LAST)
        except tk.TclError:
            return None

    def _is_editable() -> bool:
        return editable and str(widget.cget("state")) != tk.DISABLED

    def _clipboard_text() -> str | None:
        try:
            return widget.clipboard_get()
        except tk.TclError:
            return None

    def _copy_selection() -> bool:
        text = _selected_text()
        if text is None:
            return False
        widget.clipboard_clear()
        widget.clipboard_append(text)
        return True

    def _cut_selection() -> None:
        if not _is_editable() or not _copy_selection():
            return
        widget.delete(tk.SEL_FIRST, tk.SEL_LAST)

    def _paste_clipboard() -> None:
        if not _is_editable():
            return
        text = _clipboard_text()
        if text is None:
            return
        if _has_selection():
            widget.delete(tk.SEL_FIRST, tk.SEL_LAST)
        widget.insert(tk.INSERT, text)

    def _refresh_menu() -> None:
        has_selection = _has_selection()
        text_editable = _is_editable()
        menu.entryconfigure(0, state=tk.NORMAL if text_editable and has_selection else tk.DISABLED)
        menu.entryconfigure(1, state=tk.NORMAL if has_selection else tk.DISABLED)
        menu.entryconfigure(2, state=tk.NORMAL if text_editable and _clipboard_text() is not None else tk.DISABLED)

    def _show_menu(event: tk.Event) -> str:
        _refresh_menu()
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()
        return "break"

    menu.add_command(label="剪切", command=_cut_selection)
    menu.add_command(label="复制", command=_copy_selection)
    menu.add_command(label="粘贴", command=_paste_clipboard)
    widget.bind("<Button-3>", _show_menu, add="+")
    widget.bind("<Control-Button-1>", _show_menu, add="+")
    setattr(widget, "_text_context_menu", menu)
    setattr(widget, "_refresh_text_context_menu", _refresh_menu)
    return menu
