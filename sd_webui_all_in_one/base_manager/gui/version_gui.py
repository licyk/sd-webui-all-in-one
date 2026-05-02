"""通用 Tkinter 版本管理组件"""

# pylint: disable=too-many-return-statements,too-many-ancestors,too-many-instance-attributes
# pylint: disable=too-many-arguments,too-many-positional-arguments,too-many-locals

from __future__ import annotations

import os
import queue
import subprocess
import sys
import threading
import traceback
import tkinter as tk
from dataclasses import dataclass
from tkinter import font as tkfont
from tkinter import messagebox, ttk
from typing import Any, Callable, Generic, TypeVar

from sd_webui_all_in_one.base_manager.version_manager import (
    BranchInfo,
    CommitInfo,
)
from sd_webui_all_in_one.config import ROOT_PATH


T = TypeVar("T")


def detect_system_theme() -> str:
    """
    检测系统深浅色主题

    Returns:
        str: 系统主题名称, 无法检测时返回 light
    """
    if sys.platform.startswith("win"):
        try:
            import winreg  # pylint: disable=import-error,import-outside-toplevel

            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize") as key:
                value, _value_type = winreg.QueryValueEx(key, "AppsUseLightTheme")
            return "light" if int(value) else "dark"
        except Exception:
            return "light"

    if sys.platform == "darwin":
        try:
            result = subprocess.run(
                ["defaults", "read", "-g", "AppleInterfaceStyle"],
                capture_output=True,
                text=True,
                timeout=1,
                check=False,
            )
            return "dark" if "dark" in result.stdout.lower() else "light"
        except Exception:
            return "light"

    gtk_theme = os.environ.get("GTK_THEME", "").lower()
    if "dark" in gtk_theme:
        return "dark"
    try:
        result = subprocess.run(
            ["gsettings", "get", "org.gnome.desktop.interface", "color-scheme"],
            capture_output=True,
            text=True,
            timeout=1,
            check=False,
        )
        return "dark" if "dark" in result.stdout.lower() else "light"
    except Exception:
        return "light"


def apply_gui_theme(root: tk.Tk, theme: str | None = "auto") -> bool:
    """
    应用本地 Sun Valley ttk 主题

    Args:
        root (tk.Tk):
            Tk 根窗口
        theme (str | None):
            主题名称, 为 auto 或 system 时自动跟随系统主题

    Returns:
        bool: 是否成功应用主题
    """
    try:
        from sd_webui_all_in_one.base_manager.gui import sv_ttk

        selected_theme = detect_system_theme() if theme in {None, "auto", "system"} else theme
        sv_ttk.set_theme(selected_theme or "light", root=root)
        return True
    except Exception:
        return False


def apply_window_icon(root: tk.Tk | tk.Toplevel) -> bool:
    """
    应用版本管理窗口图标

    Args:
        root (tk.Tk | tk.Toplevel):
            Tk 窗口

    Returns:
        bool: 是否成功应用图标
    """

    icon_path = ROOT_PATH / "base_manager" / "gui" / "app.png"
    if not icon_path.is_file():
        return False
    try:
        icon = tk.PhotoImage(file=icon_path.as_posix())
        root.iconphoto(True, icon)
        setattr(root, "_version_manager_icon", icon)
        return True
    except tk.TclError:
        return False


def configure_gui_fonts(
    root: tk.Misc,
    style: ttk.Style | None = None,
) -> None:
    """
    统一 Tk 和 ttk 组件字体

    Args:
        root (tk.Misc):
            Tk 组件或根窗口
        style (ttk.Style | None):
            ttk 样式对象, 为 None 时自动创建
    """
    preferred_fonts = (
        "Microsoft YaHei UI",
        "Microsoft YaHei",
        "PingFang SC",
        "Noto Sans CJK SC",
        "Noto Sans SC",
        "Source Han Sans SC",
        "WenQuanYi Micro Hei",
        "Segoe UI",
    )
    available_fonts = set(tkfont.families(root))
    default_font = tkfont.nametofont("TkDefaultFont")
    font_family = next((item for item in preferred_fonts if item in available_fonts), default_font.actual("family"))

    named_fonts = (
        "TkDefaultFont",
        "TkTextFont",
        "TkMenuFont",
        "TkHeadingFont",
        "TkCaptionFont",
        "TkSmallCaptionFont",
        "TkIconFont",
        "TkTooltipFont",
        "SunValleyCaptionFont",
        "SunValleyBodyFont",
        "SunValleyBodyStrongFont",
        "SunValleyBodyLargeFont",
        "SunValleySubtitleFont",
        "SunValleyTitleFont",
        "SunValleyTitleLargeFont",
        "SunValleyDisplayFont",
    )
    for font_name in named_fonts:
        try:
            tkfont.nametofont(font_name).configure(family=font_family)
        except tk.TclError:
            continue

    if style is None:
        style = ttk.Style(root)
    style.configure(".", font="TkDefaultFont")
    style.configure("TLabel", font="TkDefaultFont")
    style.configure("TButton", font="TkDefaultFont")
    style.configure("TEntry", font="TkDefaultFont")
    style.configure("TCheckbutton", font="TkDefaultFont")
    style.configure("TRadiobutton", font="TkDefaultFont")
    style.configure("TNotebook.Tab", font="TkDefaultFont")
    style.configure("Treeview", font="TkDefaultFont", rowheight=28)
    style.configure("Treeview.Heading", font="TkHeadingFont")


@dataclass(slots=True)
class BackgroundResult(Generic[T]):
    """
    后台任务结果

    Attributes:
        callback (Callable[[T], None] | None):
            任务成功回调
        error_callback (Callable[[BaseException], None] | None):
            任务失败回调
        value (T | None):
            任务返回值
        error (BaseException | None):
            任务异常
        traceback_text (str | None):
            异常追踪信息
        message (str):
            任务状态文本
    """

    callback: Callable[[T], None] | None
    error_callback: Callable[[BaseException], None] | None
    value: T | None = None
    error: BaseException | None = None
    traceback_text: str | None = None
    message: str = ""


class BackgroundTaskMixin:
    """
    Tkinter 后台任务辅助类

    将耗时任务放入后台线程执行, 并通过队列把结果投递回 Tk 主线程,
    避免 Git、网络和文件操作阻塞界面。
    """

    def __init__(
        self,
    ) -> None:
        self._task_queue: queue.Queue[BackgroundResult[Any]] = queue.Queue()
        self._busy_count = 0

    def _install_task_poller(
        self,
        root: tk.Misc,
    ) -> None:
        """
        安装后台任务轮询器

        Args:
            root (tk.Misc):
                用于调度 after 回调的 Tk 组件
        """
        root.after(100, self._poll_tasks)

    def run_background(
        self,
        message: str,
        func: Callable[[], T],
        callback: Callable[[T], None] | None = None,
        error_callback: Callable[[BaseException], None] | None = None,
    ) -> None:
        """
        在线程中执行任务并把结果投递回主线程

        Args:
            message (str):
                任务状态文本
            func (Callable[[], T]):
                后台执行函数
            callback (Callable[[T], None] | None):
                成功回调
            error_callback (Callable[[BaseException], None] | None):
                失败回调
        """
        self._busy_count += 1
        self.set_status(message)
        self.set_busy_state(True)

        def _target() -> None:
            try:
                value = func()
                self._task_queue.put(BackgroundResult(callback=callback, error_callback=error_callback, value=value, message=message))
            except BaseException as e:  # pylint: disable=broad-exception-caught
                self._task_queue.put(
                    BackgroundResult(
                        callback=callback,
                        error_callback=error_callback,
                        error=e,
                        traceback_text=traceback.format_exc(),
                        message=message,
                    )
                )

        thread = threading.Thread(target=_target, daemon=True)
        thread.start()

    def _poll_tasks(
        self,
    ) -> None:
        while True:
            try:
                result = self._task_queue.get_nowait()
            except queue.Empty:
                break
            self._busy_count = max(0, self._busy_count - 1)
            if result.error is not None:
                if result.error_callback is not None:
                    result.error_callback(result.error)
                else:
                    messagebox.showerror("操作失败", f"{result.error}\n\n{result.traceback_text or ''}".strip())
            elif result.callback is not None:
                result.callback(result.value)
            if self._busy_count == 0:
                self.set_status("就绪")
                self.set_busy_state(False)
        self.after(100, self._poll_tasks)  # type: ignore[attr-defined]

    def set_status(
        self,
        message: str,
    ) -> None:
        """
        设置状态栏文本

        Args:
            message (str):
                状态文本
        """
        raise NotImplementedError

    def set_busy_state(
        self,
        busy: bool,
    ) -> None:
        """
        更新忙碌状态

        Args:
            busy (bool):
                是否处于忙碌状态
        """


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
        self.search_var = tk.StringVar()
        self._selected_id: str | None = None
        self._row_items: dict[str, list[int]] = {}
        self._row_backgrounds: dict[str, int] = {}
        self._row_text_items: dict[str, list[int]] = {}
        self._row_tags: dict[str, str] = {}
        self._row_values: dict[str, tuple[str, ...]] = {}
        self._row_order: list[str] = []
        self._double_click_callback: Callable[[], None] | None = None
        self._content_width = sum(self.widths.get(column, 120) for column in self.columns)
        self._content_height = 0
        self._mouse_over = False
        self._resizing_column: str | None = None
        self._resize_start_x = 0
        self._resize_start_width = 0
        self._configure_theme_colors()
        # 兼容旧代码中的 `widget.tree.insert(...)` / `widget.tree.selection()` 调用。
        self.tree = self

        self.search_entry = ttk.Entry(self, textvariable=self.search_var)
        if search_placeholder:
            self.search_entry.insert(0, search_placeholder)
            self.search_entry.bind("<FocusIn>", lambda _event: self._clear_placeholder(search_placeholder))
            self.search_entry.pack(fill=tk.X, padx=8, pady=(8, 6))

        table_frame = ttk.Frame(self)
        table_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 8))
        self.header_canvas = tk.Canvas(table_frame, height=self._HEADER_HEIGHT, highlightthickness=0, borderwidth=0, bg=self._row_colors[0], takefocus=1)
        self.canvas = tk.Canvas(table_frame, highlightthickness=0, borderwidth=0, bg=self._row_colors[0], takefocus=1)
        self.v_scroll = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.canvas.yview)
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
        if mouse_over and self.canvas.winfo_exists():
            self.canvas.focus_set()

    def _on_mousewheel(
        self,
        event: tk.Event,
    ) -> None:
        try:
            if not self.winfo_ismapped() or not self._mouse_over:
                return
        except tk.TclError:
            return
        if getattr(event, "num", None) == 4:
            self.canvas.yview_scroll(-3, "units")
        elif getattr(event, "num", None) == 5:
            self.canvas.yview_scroll(3, "units")
        else:
            delta = getattr(event, "delta", 0)
            if delta:
                self.canvas.yview_scroll(int(-1 * (delta / 120)), "units")

    def clear(
        self,
    ) -> None:
        """
        清空列表内容
        """
        self.canvas.delete("all")
        self._row_items.clear()
        self._row_backgrounds.clear()
        self._row_text_items.clear()
        self._row_tags.clear()
        self._row_values.clear()
        self._row_order.clear()
        self._selected_id = None
        self._content_height = 0
        self.canvas.configure(scrollregion=(0, 0, self._content_width, self._content_height))

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
        self._draw_row(item_id, values)
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
            self._redraw_rows()
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

    def focus(self, item_id: str | None = None) -> str:
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
        self.canvas.delete("all")
        self._row_items.clear()
        self._row_backgrounds.clear()
        self._row_text_items.clear()
        self._row_tags.clear()
        self._content_height = 0
        for item_id in self._row_order:
            self._draw_row(item_id, self._row_values[item_id])
        if self._selected_id and self.exists(self._selected_id):
            self._select(self._selected_id)

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
        self.canvas.tag_bind(row_tag, "<Button-1>", lambda _event, iid=item_id: self._select(iid))
        self.canvas.tag_bind(row_tag, "<Double-1>", lambda _event: self._handle_double_click())
        self._content_height += row_height
        self.canvas.configure(scrollregion=(0, 0, self._content_width, self._content_height))

    def _select(
        self,
        item_id: str,
    ) -> None:
        self._selected_id = item_id
        for index, current_id in enumerate(self._row_items):
            is_selected = current_id == item_id
            bg = self._selected_bg if current_id == item_id else self._row_colors[index % 2]
            self.canvas.itemconfigure(self._row_backgrounds[current_id], fill=bg)
            text_color = self._selected_text_color if is_selected else self._text_color
            for text_item in self._row_text_items.get(current_id, []):
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
        callback: Callable[[], None],
    ) -> None:
        """
        绑定双击回调

        Args:
            callback (Callable[[], None]):
                双击回调
        """
        self._double_click_callback = callback

    def bind(
        self,
        sequence: str | None = None,
        func: Callable[[tk.Event | None], object] | None = None,
        add: str | None = None,
    ) -> str | None:
        """
        绑定事件回调

        Args:
            sequence (str | None):
                事件序列
            func (Callable[[tk.Event | None], object] | None):
                事件回调
            add (str | None):
                是否追加绑定

        Returns:
            str | None: Tk 绑定 ID
        """
        if sequence == "<Double-1>" and func is not None:
            self._double_click_callback = lambda: func(None)
            return None
        return super().bind(sequence, func, add)

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


class CommitSwitchDialog(tk.Toplevel):
    """
    提交版本切换弹窗

    显示提交列表并允许用户切换到指定提交。
    """

    def __init__(
        self,
        master: tk.Misc,
        title: str,
        commits: list[CommitInfo],
        on_switch: Callable[[CommitInfo], None],
    ) -> None:
        """
        初始化提交版本切换弹窗

        Args:
            master (tk.Misc):
                父窗口
            title (str):
                弹窗标题
            commits (list[CommitInfo]):
                提交列表
            on_switch (Callable[[CommitInfo], None]):
                切换回调
        """
        super().__init__(master)
        self.title(title)
        apply_window_icon(self)
        self.geometry("900x520")
        self.minsize(720, 360)
        self.on_switch = on_switch
        self.commits = commits
        self.filtered_commits = commits
        self.search_var = tk.StringVar()

        self.transient(master)
        self.grab_set()

        entry = ttk.Entry(self, textvariable=self.search_var)
        entry.pack(fill=tk.X, padx=10, pady=10)
        entry.bind("<KeyRelease>", lambda _event: self._refresh())

        self.tree = AdaptiveIndexList(
            self,
            columns=("commit", "message", "date", "current"),
            headings={"commit": "版本 ID", "message": "更新内容", "date": "日期", "current": "当前"},
            widths={"commit": 110, "message": 520, "date": 180, "current": 70},
        )
        self.tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 8))
        self.tree.bind("<Double-1>", lambda _event: self._switch_selected())

        button_frame = ttk.Frame(self)
        button_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        ttk.Button(button_frame, text="切换", command=self._switch_selected).pack(side=tk.RIGHT)
        ttk.Button(button_frame, text="关闭", command=self.destroy).pack(side=tk.RIGHT, padx=(0, 8))

        self._refresh()

    def _refresh(
        self,
    ) -> None:
        keyword = self.search_var.get().strip().lower()
        self.tree.delete(*self.tree.get_children())
        self.filtered_commits = []
        for commit in self.commits:
            haystack = f"{commit.commit} {commit.message} {commit.date}".lower()
            if keyword and keyword not in haystack:
                continue
            self.filtered_commits.append(commit)
            self.tree.insert(
                "",
                tk.END,
                iid=commit.commit,
                values=(commit.commit, commit.message, commit.date, "✓" if commit.is_current else ""),
            )

    def _switch_selected(
        self,
    ) -> None:
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("请选择版本", "请先选择要切换的版本")
            return
        commit_id = selection[0]
        commit = next(item for item in self.filtered_commits if item.commit == commit_id)
        if commit.is_current:
            self.destroy()
            return
        if not messagebox.askyesno("确认切换", f"确认切换到版本 {commit.commit} 吗？"):
            return
        self.on_switch(commit)
        self.destroy()


class BranchSwitchDialog(tk.Toplevel):
    """
    分支切换弹窗

    显示本地和远程分支并允许用户切换到指定分支。
    """

    def __init__(
        self,
        master: tk.Misc,
        title: str,
        branches: list[BranchInfo],
        on_switch: Callable[[BranchInfo], None],
    ) -> None:
        """
        初始化分支切换弹窗

        Args:
            master (tk.Misc):
                父窗口
            title (str):
                弹窗标题
            branches (list[BranchInfo]):
                分支列表
            on_switch (Callable[[BranchInfo], None]):
                切换回调
        """
        super().__init__(master)
        self.title(title)
        apply_window_icon(self)
        self.geometry("460x420")
        self.minsize(360, 300)
        self.branches = branches
        self.on_switch = on_switch
        self.transient(master)
        self.grab_set()

        self.tree = AdaptiveIndexList(
            self,
            columns=("name", "kind", "current"),
            headings={"name": "分支", "kind": "类型", "current": "当前"},
            widths={"name": 260, "kind": 80, "current": 70},
        )
        self.tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        self.tree.bind("<Double-1>", lambda _event: self._switch_selected())

        for branch in self.branches:
            self.tree.insert("", tk.END, iid=branch.name, values=(branch.name, "远程" if branch.is_remote else "本地", "✓" if branch.is_current else ""))

        button_frame = ttk.Frame(self)
        button_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        ttk.Button(button_frame, text="切换", command=self._switch_selected).pack(side=tk.RIGHT)
        ttk.Button(button_frame, text="关闭", command=self.destroy).pack(side=tk.RIGHT, padx=(0, 8))

    def _switch_selected(
        self,
    ) -> None:
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("请选择分支", "请先选择要切换的分支")
            return
        branch_name = selection[0]
        branch = next(item for item in self.branches if item.name == branch_name)
        if branch.is_current:
            self.destroy()
            return
        if not messagebox.askyesno("确认切换", f"确认切换到分支 {branch.name} 吗？"):
            return
        self.on_switch(branch)
        self.destroy()
