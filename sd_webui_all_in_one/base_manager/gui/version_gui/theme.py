"""Implementation grouped from the former ``version_gui.py`` module."""

from __future__ import annotations

import os
import subprocess
import sys
import tkinter as tk
from tkinter import font as tkfont
from tkinter import (
    ttk,
)
from typing import (
    TypeVar,
)
from sd_webui_all_in_one.config import ROOT_PATH

T = TypeVar("T")


def detect_system_theme() -> str:
    """
    检测系统深浅色主题

    Returns:
        str: 系统主题名称, 无法检测时返回 light
    """
    if sys.platform == "win32":
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
