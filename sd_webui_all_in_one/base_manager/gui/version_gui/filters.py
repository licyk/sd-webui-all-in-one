"""Implementation grouped from the former ``version_gui.py`` module."""

from __future__ import annotations

from sd_webui_all_in_one.base_manager.version_manager import (
    CommitInfo,
    PackageVersionInfo,
)


def normalize_search_keyword(value: str, placeholder: str = "") -> str:
    """
    规范化搜索关键词并忽略占位符文本。

    Args:
        value (str):
            搜索框当前文本。
        placeholder (str):
            搜索框占位符文本。

    Returns:
        str: 规范化后的搜索关键词。
    """
    keyword = value.strip().lower()
    if placeholder and keyword == placeholder.strip().lower():
        return ""
    return keyword


def commit_matches_keyword(commit: CommitInfo, keyword: str) -> bool:
    """
    判断 Git 提交信息是否匹配搜索关键词。

    Args:
        commit (CommitInfo):
            Git 提交信息。
        keyword (str):
            搜索关键词。

    Returns:
        bool: 是否匹配。
    """
    keyword = normalize_search_keyword(keyword)
    if not keyword:
        return True
    haystack = f"{commit.commit} {commit.message} {commit.date}".lower()
    return keyword in haystack


def package_version_matches_keyword(version: PackageVersionInfo, keyword: str) -> bool:
    """
    判断 PyPI 版本信息是否匹配搜索关键词。

    Args:
        version (PackageVersionInfo):
            PyPI 版本信息。
        keyword (str):
            搜索关键词。

    Returns:
        bool: 是否匹配。
    """
    keyword = normalize_search_keyword(keyword)
    if not keyword:
        return True
    haystack = f"{version.version} {version.summary} {version.upload_time}".lower()
    return keyword in haystack
