"""仓库管理器测试辅助工具"""

from sd_webui_all_in_one.repo_manager import RepoManager


def repo_manager_with_apis():
    manager = RepoManager.__new__(RepoManager)
    manager.hf_token = None
    manager.ms_token = "ms-token"
    return manager
