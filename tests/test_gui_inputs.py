from __future__ import annotations

import tkinter as tk
from types import SimpleNamespace

import pytest

from sd_webui_all_in_one.base_manager.gui.version_gui import (
    AdaptiveIndexList,
    EnhancedEntry,
    install_text_context_menu,
)


@pytest.fixture
def tk_root():
    try:
        root = tk.Tk()
    except tk.TclError as exc:
        pytest.skip(f"Tk display unavailable: {exc}")
    root.withdraw()
    try:
        yield root
    finally:
        root.destroy()


@pytest.mark.parametrize("sequence", ("delete", "backspace"))
def test_enhanced_entry_deletes_full_selection(tk_root: tk.Tk, sequence: str) -> None:
    var = tk.StringVar(tk_root, value="abcdef")
    entry = EnhancedEntry(tk_root, textvariable=var)
    entry.pack()
    tk_root.update_idletasks()

    entry._select_all(tk.Event())  # pylint: disable=protected-access
    assert entry.selection_present()

    event = tk.Event()
    event.keysym = sequence
    result = entry._delete_selected_text(event)  # pylint: disable=protected-access
    assert result == "break"
    assert var.get() == ""


def test_enhanced_entry_replaces_full_selection(tk_root: tk.Tk) -> None:
    var = tk.StringVar(tk_root, value="abcdef")
    entry = EnhancedEntry(tk_root, textvariable=var)
    entry.pack()
    tk_root.update_idletasks()

    entry._select_all(tk.Event())  # pylint: disable=protected-access
    result = entry._replace_selection_on_keypress(SimpleNamespace(char="Z"))  # pylint: disable=protected-access

    assert result == "break"
    assert var.get() == "Z"


def test_enhanced_entry_clear_button_ignores_placeholder(tk_root: tk.Tk) -> None:
    var = tk.StringVar(tk_root)
    entry = EnhancedEntry(tk_root, textvariable=var, placeholder="搜索内容...")
    entry.pack()
    tk_root.update_idletasks()

    assert var.get() == "搜索内容..."
    assert entry.clear_button.place_info() == {}

    var.set("real text")
    tk_root.update_idletasks()
    assert entry.clear_button.place_info() != {}

    entry._clear_text(None)  # pylint: disable=protected-access
    tk_root.update_idletasks()
    assert var.get() == ""
    assert entry.clear_button.place_info() == {}


def test_enhanced_entry_context_menu_commands(tk_root: tk.Tk) -> None:
    var = tk.StringVar(tk_root, value="abc")
    entry = EnhancedEntry(tk_root, textvariable=var)
    entry.pack()
    tk_root.update_idletasks()

    entry.selection_range(0, 2)
    entry.context_menu.invoke(1)
    assert tk_root.clipboard_get() == "ab"

    entry.selection_clear()
    entry.icursor(tk.END)
    tk_root.clipboard_clear()
    tk_root.clipboard_append("Z")
    entry.context_menu.invoke(2)
    assert var.get() == "abcZ"

    entry.selection_range(0, 1)
    entry.context_menu.invoke(0)
    assert var.get() == "bcZ"
    assert tk_root.clipboard_get() == "a"


def test_text_context_menu_commands(tk_root: tk.Tk) -> None:
    text = tk.Text(tk_root)
    text.pack()
    menu = install_text_context_menu(text, editable=True)
    text.insert("1.0", "hello")

    text.tag_add(tk.SEL, "1.0", "1.5")
    menu.invoke(1)
    assert tk_root.clipboard_get() == "hello"

    text.tag_remove(tk.SEL, "1.0", tk.END)
    text.mark_set(tk.INSERT, "end-1c")
    tk_root.clipboard_clear()
    tk_root.clipboard_append("!")
    menu.invoke(2)
    assert text.get("1.0", "end-1c") == "hello!"

    text.tag_add(tk.SEL, "1.0", "1.5")
    menu.invoke(0)
    assert text.get("1.0", "end-1c") == "!"
    assert tk_root.clipboard_get() == "hello"


def test_readonly_text_context_menu_states(tk_root: tk.Tk) -> None:
    text = tk.Text(tk_root)
    text.pack()
    text.insert("1.0", "readonly")
    text.tag_add(tk.SEL, "1.0", "1.4")
    text.configure(state=tk.DISABLED)
    menu = install_text_context_menu(text, editable=False)

    refresh_menu = getattr(text, "_refresh_text_context_menu")
    refresh_menu()

    assert menu.entrycget(0, "state") == tk.DISABLED
    assert menu.entrycget(1, "state") == tk.NORMAL
    assert menu.entrycget(2, "state") == tk.DISABLED


def test_adaptive_index_list_preserves_scroll_after_refresh(tk_root: tk.Tk) -> None:
    widget = AdaptiveIndexList(
        tk_root,
        columns=("name",),
        headings={"name": "名称"},
        widths={"name": 240},
    )
    widget.pack(fill=tk.BOTH, expand=True)
    widget.canvas.configure(width=240, height=120)

    for index in range(80):
        widget.insert(str(index), (f"item {index}",))
    tk_root.update()

    widget.canvas.yview_moveto(0.45)
    before = widget.canvas.canvasy(0)
    assert before > 0

    widget.clear()
    for index in range(80):
        widget.insert(str(index), (f"new item {index}",))
    tk_root.update()

    after = widget.canvas.canvasy(0)
    assert after > 0
    assert after == pytest.approx(before, abs=widget._MIN_ROW_HEIGHT)  # pylint: disable=protected-access


def test_adaptive_index_list_user_scroll_cancels_refresh_restore(tk_root: tk.Tk) -> None:
    widget = AdaptiveIndexList(
        tk_root,
        columns=("name",),
        headings={"name": "名称"},
        widths={"name": 240},
    )
    widget.pack(fill=tk.BOTH, expand=True)
    widget.canvas.configure(width=240, height=120)

    for index in range(80):
        widget.insert(str(index), (f"item {index}",))
    tk_root.update()

    widget.canvas.yview_moveto(0.45)
    widget._pending_scroll_top = widget.canvas.canvasy(0)  # pylint: disable=protected-access

    widget._on_scrollbar_yview("moveto", "0.2")  # pylint: disable=protected-access
    user_scroll_top = widget.canvas.canvasy(0)
    widget._restore_scroll_position()  # pylint: disable=protected-access

    assert widget._pending_scroll_top is None  # pylint: disable=protected-access
    assert widget.canvas.canvasy(0) == user_scroll_top
