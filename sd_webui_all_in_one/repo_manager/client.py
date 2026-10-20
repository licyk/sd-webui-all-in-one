"""HuggingFace / ModelScope API 客户端与 Token 管理"""

import os
from threading import Lock
from typing import TYPE_CHECKING, Any, cast

from sd_webui_all_in_one.repo_manager.utils import _callable_accepts_keyword
from sd_webui_all_in_one.repo_manager.dependencies import (
    _ensure_huggingface_hub,
    _ensure_modelscope,
)

if TYPE_CHECKING:
    from huggingface_hub import HfApi
    from modelscope import HubApi


_API_NOT_INITIALIZED = object()
"""API 客户端未初始化标记"""


class RepoApiClient:
    """HuggingFace / ModelScope API 客户端基类, 负责 Token 配置和 API 客户端懒初始化"""

    def __init__(
        self,
        hf_token: str | None = None,
        ms_token: str | None = None,
    ) -> None:
        """HuggingFace / ModelScope 仓库管理器初始化

        Args:
            hf_token (str | None):
                HugggingFace Token, 不为`None`时配置`HF_TOKEN`环境变量
            ms_token (str | None):
                ModelScope Token, 不为`None`时配置`MODELSCOPE_API_TOKEN`环境变量
        """
        self._hf_api: "HfApi | object" = _API_NOT_INITIALIZED
        self._ms_api: "HubApi | object" = _API_NOT_INITIALIZED
        self._hf_api_lock = Lock()
        self._ms_api_lock = Lock()
        self.hf_token: str | None = hf_token
        self.ms_token: str | None = ms_token
        if hf_token is not None:
            os.environ["HF_TOKEN"] = hf_token
        if ms_token is not None:
            os.environ["MODELSCOPE_API_TOKEN"] = ms_token

    def _get_hf_api_lock(self) -> Lock:
        """获取 HuggingFace API 懒初始化锁"""
        lock = getattr(self, "_hf_api_lock", None)
        if lock is None:
            lock = Lock()
            self._hf_api_lock = lock
        return lock

    def _get_ms_api_lock(self) -> Lock:
        """获取 ModelScope API 懒初始化锁"""
        lock = getattr(self, "_ms_api_lock", None)
        if lock is None:
            lock = Lock()
            self._ms_api_lock = lock
        return lock

    def _init_hf_api(self) -> "HfApi":
        """初始化 HuggingFace API 客户端"""
        _ensure_huggingface_hub()
        from huggingface_hub import HfApi

        return HfApi(token=self.hf_token)

    def _init_ms_api(self) -> "HubApi":
        """初始化 ModelScope API 客户端"""
        _ensure_modelscope()
        from modelscope import HubApi

        if self.ms_token is None:
            return HubApi()

        if _callable_accepts_keyword(HubApi, "token"):
            return HubApi(token=self.ms_token)

        ms_api = HubApi()
        ms_api.login(self.ms_token)
        return ms_api

    def get_ms_git_token(self) -> str | None:
        """获取 ModelScope Git access token

        Returns:
            (str | None):
                ModelScope 的 Git Token
        """
        _ensure_modelscope("modelscope.hub.api")
        from modelscope.hub.api import ModelScopeConfig

        git_token = ModelScopeConfig.get_git_token()
        if git_token or not self.ms_token:
            return git_token

        login_result = self.ms_api.login(self.ms_token)
        if isinstance(login_result, tuple):
            login_git_token = login_result[0]
            if isinstance(login_git_token, str) and login_git_token:
                return login_git_token
        if isinstance(login_result, str) and login_result:
            return login_result

        return ModelScopeConfig.get_git_token() or self.ms_token

    def get_hf_token(self) -> str | None:
        """获取当前配置的 HuggingFace Token

        Returns:
            (str | None):
                HuggingFace Token
        """
        return self.hf_token

    def get_ms_token(self) -> str | None:
        """获取当前配置的 ModelScope Token

        Returns:
            (str | None):
                ModelScope Token
        """
        return self.ms_token

    def configure_tokens(
        self,
        hf_token: str | None = None,
        ms_token: str | None = None,
    ) -> None:
        """配置 HuggingFace / ModelScope Token

        Args:
            hf_token (str | None):
                HuggingFace Token, 为`None`时保持当前配置
            ms_token (str | None):
                ModelScope Token, 为`None`时保持当前配置
        """
        if hf_token is not None and hf_token != self.hf_token:
            self.hf_token = hf_token
            os.environ["HF_TOKEN"] = hf_token
            self._hf_api = _API_NOT_INITIALIZED

        if ms_token is not None and ms_token != self.ms_token:
            self.ms_token = ms_token
            os.environ["MODELSCOPE_API_TOKEN"] = ms_token
            self._ms_api = _API_NOT_INITIALIZED

    @property
    def hf_api(self) -> "HfApi":
        """HuggingFace API 客户端实例, 首次访问时懒初始化

        Returns:
            HfApi:
                HuggingFace API 客户端实例
        """
        if getattr(self, "_hf_api", _API_NOT_INITIALIZED) is _API_NOT_INITIALIZED:
            with self._get_hf_api_lock():
                if getattr(self, "_hf_api", _API_NOT_INITIALIZED) is _API_NOT_INITIALIZED:
                    self._hf_api = self._init_hf_api()
        return cast("HfApi", self._hf_api)

    @hf_api.setter
    def hf_api(self, value: Any) -> None:
        self._hf_api = value

    @property
    def ms_api(self) -> "HubApi":
        """ModelScope API 客户端实例, 首次访问时懒初始化

        Returns:
            HubApi:
                ModelScope API 客户端实例
        """
        if getattr(self, "_ms_api", _API_NOT_INITIALIZED) is _API_NOT_INITIALIZED:
            with self._get_ms_api_lock():
                if getattr(self, "_ms_api", _API_NOT_INITIALIZED) is _API_NOT_INITIALIZED:
                    self._ms_api = self._init_ms_api()
        return cast("HubApi", self._ms_api)

    @ms_api.setter
    def ms_api(self, value: Any) -> None:
        self._ms_api = value
