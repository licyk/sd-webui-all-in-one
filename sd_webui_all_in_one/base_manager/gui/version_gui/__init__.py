"""Shared Tkinter version-manager widgets and utilities."""

from sd_webui_all_in_one.base_manager.gui.version_gui.dialogs import (
    CommitSwitchDialog as CommitSwitchDialog,
    BranchSwitchDialog as BranchSwitchDialog,
)
from sd_webui_all_in_one.base_manager.gui.version_gui.filters import (
    normalize_search_keyword as normalize_search_keyword,
    commit_matches_keyword as commit_matches_keyword,
    package_version_matches_keyword as package_version_matches_keyword,
)
from sd_webui_all_in_one.base_manager.gui.version_gui.index_list import (
    AdaptiveIndexList as AdaptiveIndexList,
    SearchableTree as SearchableTree,
)
from sd_webui_all_in_one.base_manager.gui.version_gui.inputs import (
    EnhancedEntry as EnhancedEntry,
    install_text_context_menu as install_text_context_menu,
)
from sd_webui_all_in_one.base_manager.gui.version_gui.tasks import (
    GuiActionsMixinContext as GuiActionsMixinContext,
    BackgroundResult as BackgroundResult,
    BackgroundTaskMixin as BackgroundTaskMixin,
)
from sd_webui_all_in_one.base_manager.gui.version_gui.theme import (
    T as T,
    detect_system_theme as detect_system_theme,
    apply_gui_theme as apply_gui_theme,
    apply_window_icon as apply_window_icon,
    configure_gui_fonts as configure_gui_fonts,
)

__all__ = [name for name in globals() if not name.startswith("_")]
