"""Shared Tkinter version-manager widgets and utilities."""

from sd_webui_all_in_one.base_manager.gui.version_gui.dialogs import (
    CommitSwitchDialog,
    BranchSwitchDialog,
)
from sd_webui_all_in_one.base_manager.gui.version_gui.filters import (
    normalize_search_keyword,
    commit_matches_keyword,
    package_version_matches_keyword,
)
from sd_webui_all_in_one.base_manager.gui.version_gui.index_list import (
    AdaptiveIndexList,
    SearchableTree,
)
from sd_webui_all_in_one.base_manager.gui.version_gui.inputs import (
    EnhancedEntry,
    install_text_context_menu,
)
from sd_webui_all_in_one.base_manager.gui.version_gui.tasks import (
    GuiActionsMixinContext,
    BackgroundResult,
    BackgroundTaskMixin,
)
from sd_webui_all_in_one.base_manager.gui.version_gui.theme import (
    T,
    detect_system_theme,
    apply_gui_theme,
    apply_window_icon,
    configure_gui_fonts,
)

__all__ = [
    "CommitSwitchDialog",
    "BranchSwitchDialog",
    "normalize_search_keyword",
    "commit_matches_keyword",
    "package_version_matches_keyword",
    "AdaptiveIndexList",
    "SearchableTree",
    "EnhancedEntry",
    "install_text_context_menu",
    "GuiActionsMixinContext",
    "BackgroundResult",
    "BackgroundTaskMixin",
    "T",
    "detect_system_theme",
    "apply_gui_theme",
    "apply_window_icon",
    "configure_gui_fonts",
]
