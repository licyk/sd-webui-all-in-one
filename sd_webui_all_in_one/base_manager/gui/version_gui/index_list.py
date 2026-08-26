"""Implementation grouped from the former ``version_gui.py`` module."""

from __future__ import annotations

import time
import tkinter as tk
from tkinter import (
    ttk,
)
from typing import (
    Any,
    Callable,
)

from .filters import normalize_search_keyword
from .inputs import EnhancedEntry


class AdaptiveIndexList(ttk.Frame):
    """
    Canvas 绘制的自适应列表

    使用 Canvas 绘制行和列, 支持搜索框、纵向滚动、行高自适应、
    列宽拖拽和部分 Treeview 兼容接口。
    """

    _HEADER_HEIGHT = 36
    _MIN_ROW_HEIGHT = 34
    _MIN_COLUMN_WIDTH = 48
    _RESIZE_HITBOX = 5
    _CELL_PAD_X = 8
    _CELL_PAD_Y = 7

    def __init__(
        self,
        master: tk.Misc,
        columns: tuple[str, ...],
        headings: dict[str, str],
        widths: dict[str, int],
        search_placeholder: str | None = None,
    ) -> None:
        """
        初始化自适应列表

        Args:
            master (tk.Misc):
                父组件
            columns (tuple[str, ...]):
                列 ID
            headings (dict[str, str]):
                列标题
            widths (dict[str, int]):
                初始列宽
            search_placeholder (str | None):
                搜索框占位文本, 为 None 时不显示搜索框
        """
        super().__init__(master)
        self.columns = columns
        self.headings = headings
        self._preferred_widths = dict(widths)
        self.widths = dict(widths)
        self.search_placeholder = search_placeholder
        self.search_var = tk.StringVar()
        self._selected_id: str | None = None
        self._row_items: dict[str, list[int]] = {}
        self._row_backgrounds: dict[str, int] = {}
        self._row_text_items: dict[str, list[int]] = {}
        self._row_tags: dict[str, str] = {}
        self._row_indexes: dict[str, int] = {}
        self._row_values: dict[str, tuple[str, ...]] = {}
        self._row_order: list[str] = []
        self._redraw_job: str | None = None
        self._draw_batch_job: str | None = None
        self._search_change_job: str | None = None
        self._draw_cursor = 0
        self._double_click_callback: Callable[[], object] | None = None
        self._content_width = sum(self.widths.get(column, 120) for column in self.columns)
        self._content_height = 0
        self._pending_scroll_top: float | None = None
        self._empty_clear_scroll_job: str | None = None
        self._mouse_over = False
        self._resizing_column: str | None = None
        self._resize_start_x = 0
        self._resize_start_width = 0
        self._configure_theme_colors()
        # 兼容旧代码中的 `widget.tree.insert(...)` / `widget.tree.selection()` 调用。
        self.tree = self

        self.search_entry = EnhancedEntry(self, textvariable=self.search_var, placeholder=search_placeholder)
        if search_placeholder:
            self.search_entry.pack(fill=tk.X, padx=8, pady=(8, 6))
        self._last_search_keyword = self.search_keyword()

        table_frame = ttk.Frame(self)
        table_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 8))
        self.header_canvas = tk.Canvas(table_frame, height=self._HEADER_HEIGHT, highlightthickness=0, borderwidth=0, bg=self._row_colors[0], takefocus=1)
        self.canvas = tk.Canvas(table_frame, highlightthickness=0, borderwidth=0, bg=self._row_colors[0], takefocus=1)
        self.v_scroll = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self._on_scrollbar_yview)
        self.canvas.configure(yscrollcommand=self.v_scroll.set)

        self.header_canvas.grid(row=0, column=0, sticky="ew")
        self.canvas.grid(row=1, column=0, sticky="nsew")
        self.v_scroll.grid(row=1, column=1, sticky="ns")
        table_frame.rowconfigure(1, weight=1)
        table_frame.columnconfigure(0, weight=1)
        table_frame.bind("<Configure>", self._on_table_configure)

        for widget in (self, self.header_canvas, self.canvas):
            widget.bind("<Enter>", lambda _event: self._set_mouse_over(True))
            widget.bind("<Leave>", lambda _event: self._set_mouse_over(False))
            # 只绑定当前组件，避免弹窗销毁后留下 bind_all 全局回调。
            widget.bind("<MouseWheel>", self._on_mousewheel)
            widget.bind("<Button-4>", self._on_mousewheel)
            widget.bind("<Button-5>", self._on_mousewheel)
        self.header_canvas.bind("<Motion>", self._on_header_motion)
        self.header_canvas.bind("<ButtonPress-1>", self._on_header_press)
        self.header_canvas.bind("<B1-Motion>", self._on_header_drag)
        self.header_canvas.bind("<ButtonRelease-1>", self._on_header_release)

        self._draw_header()

    def _configure_theme_colors(
        self,
    ) -> None:
        is_dark = "dark" in ttk.Style(self).theme_use().lower()
        if is_dark:
            self._row_colors = ("#1f1f1f", "#262626")
            self._selected_bg = "#1f6feb"
            self._header_bg = "#2d2d2d"
            self._grid_color = "#3a3a3a"
            self._header_grid_color = "#4a4a4a"
            self._text_color = "#f3f3f3"
        else:
            self._row_colors = ("#ffffff", "#f7f7f7")
            self._selected_bg = "#0a64ad"
            self._header_bg = "#f3f3f3"
            self._grid_color = "#eeeeee"
            self._header_grid_color = "#dddddd"
            self._text_color = "#1f1f1f"
        self._selected_text_color = "#ffffff"

    def search_keyword(
        self,
    ) -> str:
        """
        获取规范化后的真实搜索关键词。

        Returns:
            str: 去掉占位符语义后的搜索关键词。
        """
        return normalize_search_keyword(self.search_var.get(), self.search_placeholder or "")

    def bind_search_change(
        self,
        callback: Callable[[], object],
        debounce_ms: int = 200,
    ) -> str:
        """
        绑定真实搜索关键词变化回调。

        Args:
            callback (Callable[[], object]):
                搜索关键词变化时执行的回调。
            debounce_ms (int):
                搜索变化回调延迟执行时间，单位为毫秒。

        Returns:
            str: Tk 变量监听 ID。
        """
        self._last_search_keyword = self.search_keyword()

        def _on_search_var_changed(*_args: str) -> None:
            keyword = self.search_keyword()
            if keyword == self._last_search_keyword:
                return
            self._last_search_keyword = keyword
            if self._search_change_job is not None:
                try:
                    self.after_cancel(self._search_change_job)
                except tk.TclError:
                    pass
                self._search_change_job = None
            if debounce_ms <= 0:
                callback()
                return

            def _run_callback() -> None:
                self._search_change_job = None
                callback()

            self._search_change_job = self.after(debounce_ms, _run_callback)

        return self.search_var.trace_add("write", _on_search_var_changed)

    def _clear_placeholder(
        self,
        placeholder: str,
    ) -> None:
        if self.search_var.get() == placeholder:
            self.search_var.set("")

    def _draw_header(
        self,
    ) -> None:
        self.header_canvas.delete("all")
        x = 0
        for column in self.columns:
            width = self.widths.get(column, 120)
            self.header_canvas.create_rectangle(
                x,
                0,
                x + width,
                self._HEADER_HEIGHT,
                fill=self._header_bg,
                outline=self._header_grid_color,
            )
            self.header_canvas.create_text(
                x + width / 2,
                self._HEADER_HEIGHT / 2,
                text=self.headings.get(column, column),
                font="TkHeadingFont",
                fill=self._text_color,
                anchor="center",
                width=max(40, width - self._CELL_PAD_X * 2),
            )
            x += width
        self.header_canvas.configure(scrollregion=(0, 0, self._content_width, self._HEADER_HEIGHT))

    def _on_table_configure(
        self,
        event: tk.Event,
    ) -> None:
        width = max(1, event.width - self.v_scroll.winfo_width())
        if width == self._content_width:
            return
        yview = self.canvas.yview()
        self._fit_columns_to_width(width)
        self._draw_header()
        self._redraw_rows()
        self.canvas.yview_moveto(yview[0])

    def _fit_columns_to_width(
        self,
        available_width: int,
    ) -> None:
        """
        根据可视宽度计算实际列宽

        Args:
            available_width (int):
                可用列表宽度
        """
        preferred = {column: max(self._MIN_COLUMN_WIDTH, self._preferred_widths.get(column, 120)) for column in self.columns}
        preferred_total = sum(preferred.values())
        min_total = self._MIN_COLUMN_WIDTH * len(self.columns)
        if available_width <= 0:
            return
        if available_width <= min_total:
            self.widths = {column: self._MIN_COLUMN_WIDTH for column in self.columns}
            self._content_width = min_total
            return
        if preferred_total == available_width:
            self.widths = preferred
            self._content_width = available_width
            return
        if preferred_total < available_width:
            extra = available_width - preferred_total
            widths: dict[str, int] = {}
            assigned = 0
            for index, column in enumerate(self.columns):
                if index == len(self.columns) - 1:
                    width = available_width - assigned
                else:
                    width = preferred[column] + round(extra * preferred[column] / preferred_total)
                widths[column] = width
                assigned += width
            self.widths = widths
            self._content_width = available_width
            return

        excess = preferred_total - available_width
        shrinkable_total = sum(width - self._MIN_COLUMN_WIDTH for width in preferred.values())
        widths = {}
        assigned = 0
        for index, column in enumerate(self.columns):
            if index == len(self.columns) - 1:
                width = available_width - assigned
            else:
                shrinkable = preferred[column] - self._MIN_COLUMN_WIDTH
                shrink = round(excess * shrinkable / shrinkable_total) if shrinkable_total else 0
                width = max(self._MIN_COLUMN_WIDTH, preferred[column] - shrink)
            widths[column] = width
            assigned += width
        self.widths = widths
        self._content_width = sum(widths.values())

    def _column_edges(self) -> list[tuple[str, int]]:
        edges: list[tuple[str, int]] = []
        x = 0
        for column in self.columns[:-1]:
            x += self.widths.get(column, 120)
            edges.append((column, x))
        return edges

    def _resize_column_at(self, x: float) -> str | None:
        for column, edge_x in self._column_edges():
            if abs(x - edge_x) <= self._RESIZE_HITBOX:
                return column
        return None

    def _on_header_motion(
        self,
        event: tk.Event,
    ) -> None:
        if self._resizing_column is not None:
            return
        x = self.header_canvas.canvasx(event.x)
        cursor = "sb_h_double_arrow" if self._resize_column_at(x) is not None else ""
        self.header_canvas.configure(cursor=cursor)

    def _on_header_press(
        self,
        event: tk.Event,
    ) -> None:
        x = self.header_canvas.canvasx(event.x)
        column = self._resize_column_at(x)
        if column is None:
            return
        self._resizing_column = column
        self._resize_start_x = int(x)
        self._resize_start_width = self._preferred_widths.get(column, self.widths.get(column, 120))
        self.header_canvas.configure(cursor="sb_h_double_arrow")

    def _on_header_drag(
        self,
        event: tk.Event,
    ) -> None:
        if self._resizing_column is None:
            return
        x = int(self.header_canvas.canvasx(event.x))
        width = max(self._MIN_COLUMN_WIDTH, self._resize_start_width + x - self._resize_start_x)
        if width == self._preferred_widths.get(self._resizing_column, 120):
            return
        yview = self.canvas.yview()
        self._preferred_widths[self._resizing_column] = width
        self._fit_columns_to_width(max(1, self.canvas.winfo_width()))
        self._draw_header()
        self._redraw_rows()
        self.canvas.yview_moveto(yview[0])

    def _on_header_release(
        self,
        _event: tk.Event,
    ) -> None:
        self._resizing_column = None
        self.header_canvas.configure(cursor="")

    def _set_mouse_over(
        self,
        mouse_over: bool,
    ) -> None:
        self._mouse_over = mouse_over
        try:
            if mouse_over and self.canvas.winfo_exists():
                self.canvas.focus_set()
        except tk.TclError:
            pass

    def _on_mousewheel(
        self,
        event: tk.Event | None,
    ) -> None:
        try:
            if not self.winfo_ismapped() or not self._mouse_over:
                return
        except tk.TclError:
            return
        if event is None:
            return
        self._cancel_scroll_restore_for_user_scroll()
        if getattr(event, "num", None) == 4:
            self.canvas.yview_scroll(-3, "units")
        elif getattr(event, "num", None) == 5:
            self.canvas.yview_scroll(3, "units")
        else:
            delta = getattr(event, "delta", 0)
            if delta:
                self.canvas.yview_scroll(int(-1 * (delta / 120)), "units")

    def _on_scrollbar_yview(
        self,
        *args: str,
    ) -> None:
        self._cancel_scroll_restore_for_user_scroll()
        self.canvas.yview(*args)

    def clear(
        self,
    ) -> None:
        """
        清空列表内容
        """
        self._remember_scroll_position()
        self._cancel_pending_draws()
        self.canvas.delete("all")
        self._row_items.clear()
        self._row_backgrounds.clear()
        self._row_text_items.clear()
        self._row_tags.clear()
        self._row_indexes.clear()
        self._row_values.clear()
        self._row_order.clear()
        self._selected_id = None
        self._content_height = 0
        self.canvas.configure(scrollregion=(0, 0, self._content_width, self._content_height))
        self._schedule_empty_clear_scroll_reset()

    def delete(
        self,
        *item_ids: str,
    ) -> None:
        """
        删除指定行

        Args:
            *item_ids (str):
                行 ID
        """
        if not item_ids:
            return
        for item_id in item_ids:
            if item_id in self._row_values:
                del self._row_values[item_id]
            if item_id in self._row_order:
                self._row_order.remove(item_id)
        if self._selected_id in item_ids:
            self._selected_id = None
        self._redraw_rows()

    def get_children(self) -> tuple[str, ...]:
        """
        获取所有行 ID

        Returns:
            tuple[str, ...]: 行 ID 列表
        """
        return tuple(self._row_order)

    def insert(self, *args: Any, **kwargs: Any) -> str:
        """
        插入一行

        支持简化调用和 Treeview 风格调用。

        Args:
            *args (Any):
                位置参数
            **kwargs (Any):
                关键字参数

        Returns:
            str: 行 ID

        Raises:
            TypeError:
                传入的行数据格式不受支持时抛出。
        """
        if "iid" in kwargs or "values" in kwargs:
            item_id = str(kwargs.get("iid") or len(self._row_order))
            values = tuple(str(value) for value in kwargs.get("values", ()))
        elif len(args) >= 2 and isinstance(args[1], tuple):
            item_id = str(args[0])
            values = tuple(str(value) for value in args[1])
        elif len(args) >= 3:
            item_id = str(kwargs.get("iid") or len(self._row_order))
            values = tuple(str(value) for value in kwargs.get("values", args[2] if len(args) > 2 else ()))
        else:
            raise TypeError("insert() expects either (item_id, values) or Treeview-style arguments")
        self._row_values[item_id] = values
        if item_id not in self._row_order:
            self._row_order.append(item_id)
        self._cancel_empty_clear_scroll_reset()
        self._schedule_redraw()
        return item_id

    def item(self, item_id: str, **kwargs: Any) -> dict[str, tuple[str, ...]] | None:
        """
        读取或更新行值

        Args:
            item_id (str):
                行 ID
            **kwargs (Any):
                行属性

        Returns:
            dict[str, tuple[str, ...]] | None: 行值信息, 更新时返回 None
        """
        item_id = str(item_id)
        if "values" in kwargs:
            self._row_values[item_id] = tuple(str(value) for value in kwargs["values"])
            if item_id not in self._row_order:
                self._row_order.append(item_id)
            self._cancel_empty_clear_scroll_reset()
            self._schedule_redraw()
            return None
        return {"values": self._row_values.get(item_id, ())}

    def exists(self, item_id: str) -> bool:
        """
        判断行是否存在

        Args:
            item_id (str):
                行 ID

        Returns:
            bool: 行是否存在
        """
        return str(item_id) in self._row_values

    def selection(self) -> tuple[str, ...]:
        """
        获取当前选中行

        Returns:
            tuple[str, ...]: 当前选中行 ID
        """
        return (self._selected_id,) if self._selected_id is not None else ()

    def selection_set(
        self,
        item_id: str,
    ) -> None:
        """
        设置当前选中行

        Args:
            item_id (str):
                行 ID
        """
        if self.exists(item_id):
            self._select(str(item_id))

    def focus(self, item_id: str | None = None) -> str:  # ty: ignore[invalid-method-override]
        """
        读取或设置焦点行

        Args:
            item_id (str | None):
                行 ID

        Returns:
            str: 当前焦点行 ID
        """
        if item_id is not None and self.exists(item_id):
            self._select(str(item_id))
        return self._selected_id or ""

    def _redraw_rows(
        self,
    ) -> None:
        self._schedule_redraw()

    def _cancel_pending_draws(
        self,
    ) -> None:
        for job in (self._redraw_job, self._draw_batch_job):
            if job is None:
                continue
            try:
                self.after_cancel(job)
            except tk.TclError:
                pass
        self._redraw_job = None
        self._draw_batch_job = None

    def _schedule_empty_clear_scroll_reset(
        self,
    ) -> None:
        self._cancel_empty_clear_scroll_reset()
        self._empty_clear_scroll_job = self.after_idle(self._clear_pending_scroll_if_empty)

    def _cancel_empty_clear_scroll_reset(
        self,
    ) -> None:
        if self._empty_clear_scroll_job is None:
            return
        try:
            self.after_cancel(self._empty_clear_scroll_job)
        except tk.TclError:
            pass
        self._empty_clear_scroll_job = None

    def _clear_pending_scroll_if_empty(
        self,
    ) -> None:
        self._empty_clear_scroll_job = None
        if not self._row_order:
            self._pending_scroll_top = None

    def _schedule_redraw(
        self,
    ) -> None:
        try:
            exists = self.winfo_exists()
        except tk.TclError:
            return
        if not exists:
            return
        if self._redraw_job is not None:
            return
        self._redraw_job = self.after_idle(self._begin_incremental_redraw)

    def _begin_incremental_redraw(
        self,
    ) -> None:
        self._redraw_job = None
        try:
            exists = self.winfo_exists()
        except tk.TclError:
            return
        if not exists:
            return
        if self._draw_batch_job is not None:
            try:
                self.after_cancel(self._draw_batch_job)
            except tk.TclError:
                pass
            self._draw_batch_job = None
        self._remember_scroll_position()
        self.canvas.delete("all")
        self._row_items.clear()
        self._row_backgrounds.clear()
        self._row_text_items.clear()
        self._row_tags.clear()
        self._row_indexes.clear()
        self._content_height = 0
        self._draw_cursor = 0
        self.canvas.configure(scrollregion=(0, 0, self._content_width, self._content_height))
        self._draw_next_batch()

    def _draw_next_batch(
        self,
    ) -> None:
        self._draw_batch_job = None
        try:
            exists = self.winfo_exists()
        except tk.TclError:
            return
        if not exists:
            return
        start_time = time.perf_counter()
        while self._draw_cursor < len(self._row_order):
            item_id = self._row_order[self._draw_cursor]
            values = self._row_values.get(item_id)
            self._draw_cursor += 1
            if values is None:
                continue
            self._draw_row(item_id, values)
            if time.perf_counter() - start_time >= 0.012:
                break
        self._restore_scroll_position()
        if self._draw_cursor < len(self._row_order):
            self._draw_batch_job = self.after(1, self._draw_next_batch)
            return
        if self._selected_id and self.exists(self._selected_id):
            self._select(self._selected_id)
        self._restore_scroll_position(final=True)

    def _remember_scroll_position(
        self,
    ) -> None:
        if self._pending_scroll_top is not None:
            return
        try:
            self._pending_scroll_top = max(0.0, float(self.canvas.canvasy(0)))
        except tk.TclError:
            self._pending_scroll_top = None

    def _restore_scroll_position(
        self,
        final: bool = False,
    ) -> None:
        if self._pending_scroll_top is None:
            return
        try:
            viewport_height = max(1, self.canvas.winfo_height())
            max_top = max(0, self._content_height - viewport_height)
            target_top = min(self._pending_scroll_top, max_top)
            if self._content_height > 0:
                self.canvas.yview_moveto(target_top / max(1, self._content_height))
        except tk.TclError:
            pass
        if final:
            self._pending_scroll_top = None

    def _cancel_scroll_restore_for_user_scroll(
        self,
    ) -> None:
        self._pending_scroll_top = None

    def _draw_row(
        self,
        item_id: str,
        values: tuple[str, ...],
    ) -> None:
        row_index = len(self._row_items)
        bg = self._row_colors[row_index % 2]
        y = self._content_height
        row_tag = f"adaptive_row_{row_index}"
        text_items: list[int] = []
        x = 0
        row_height = self._MIN_ROW_HEIGHT
        for index, column in enumerate(self.columns):
            width = self.widths.get(column, 120)
            text = values[index] if index < len(values) else ""
            text_item = self.canvas.create_text(
                x + self._CELL_PAD_X,
                y + self._CELL_PAD_Y,
                text=text,
                font="TkDefaultFont",
                anchor="nw",
                justify=tk.LEFT,
                fill=self._text_color,
                width=max(40, width - self._CELL_PAD_X * 2),
                tags=(row_tag, "cell_text"),
            )
            bbox = self.canvas.bbox(text_item)
            if bbox is not None:
                row_height = max(row_height, bbox[3] - bbox[1] + self._CELL_PAD_Y * 2)
            text_items.append(text_item)
            x += width

        background = self.canvas.create_rectangle(
            0,
            y,
            self._content_width,
            y + row_height,
            fill=bg,
            outline=self._grid_color,
            tags=(row_tag, "row_background"),
        )
        self.canvas.tag_lower(background)

        x = 0
        separator_items: list[int] = []
        for column in self.columns:
            width = self.widths.get(column, 120)
            separator_items.append(self.canvas.create_line(x, y, x, y + row_height, fill=self._grid_color, tags=(row_tag, "grid_line")))
            x += width
        separator_items.append(self.canvas.create_line(self._content_width, y, self._content_width, y + row_height, fill=self._grid_color, tags=(row_tag, "grid_line")))

        self._row_items[item_id] = [background, *text_items, *separator_items]
        self._row_backgrounds[item_id] = background
        self._row_text_items[item_id] = text_items
        self._row_tags[row_tag] = item_id
        self._row_indexes[item_id] = row_index
        self.canvas.tag_bind(row_tag, "<Button-1>", lambda _event, iid=item_id: self._select(iid))
        self.canvas.tag_bind(row_tag, "<Double-1>", lambda _event: self._handle_double_click())
        if item_id == self._selected_id:
            self.canvas.itemconfigure(background, fill=self._selected_bg)
            for text_item in text_items:
                self.canvas.itemconfigure(text_item, fill=self._selected_text_color)
        self._content_height += row_height
        self.canvas.configure(scrollregion=(0, 0, self._content_width, self._content_height))

    def _select(
        self,
        item_id: str,
    ) -> None:
        previous_id = self._selected_id
        if previous_id == item_id:
            return
        self._selected_id = item_id
        if previous_id is not None:
            self._set_row_selected(previous_id, False)
        self._set_row_selected(item_id, True)

    def _set_row_selected(
        self,
        item_id: str,
        selected: bool,
    ) -> None:
        if item_id not in self._row_backgrounds:
            return
        row_index = self._row_indexes.get(item_id)
        if row_index is None:
            return
        bg = self._selected_bg if selected else self._row_colors[row_index % 2]
        text_color = self._selected_text_color if selected else self._text_color
        self.canvas.itemconfigure(self._row_backgrounds[item_id], fill=bg)
        for text_item in self._row_text_items.get(item_id, []):
            self.canvas.itemconfigure(text_item, fill=text_color)

    def selected_item_id(self) -> str | None:
        """
        获取当前选中行 ID

        Returns:
            str | None: 当前选中行 ID
        """
        return self._selected_id

    def bind_double_click(
        self,
        callback: Callable[[], object],
    ) -> None:
        """
        绑定双击回调

        Args:
            callback (Callable[[], object]):
                双击回调
        """
        self._double_click_callback = callback

    def destroy(
        self,
    ) -> None:
        """
        销毁列表并取消待执行绘制任务
        """
        self._cancel_pending_draws()
        self._cancel_empty_clear_scroll_reset()
        super().destroy()

    def bind(  # ty: ignore[invalid-method-override]
        self,
        sequence: str | None = None,
        func: Callable[[tk.Event | None], Any] | None = None,
        add: str | None = None,
    ) -> str | None:
        """
        绑定事件回调

        Args:
            sequence (str | None):
                事件序列
            func (Callable[[tk.Event | None], Any] | None):
                事件回调
            add (str | None):
                是否追加绑定

        Returns:
            str | None: Tk 绑定 ID
        """
        if sequence == "<Double-1>" and func is not None:
            self._double_click_callback = lambda: func(None)
            return None
        return super().bind(sequence, func, add)  # ty: ignore[no-matching-overload]

    def _handle_double_click(
        self,
    ) -> None:
        if self._double_click_callback is not None:
            self._double_click_callback()


class SearchableTree(AdaptiveIndexList):
    """
    兼容旧 SearchableTree 名称的 Canvas 列表

    旧 GUI 代码使用 SearchableTree 名称, 新实现保留该类名以减少调用方改动。
    """
