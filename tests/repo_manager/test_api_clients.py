"""仓库管理器 API 客户端懒加载与令牌测试"""

import os
import sys
import types

import pytest

from sd_webui_all_in_one.repo_manager import client as client_module
from sd_webui_all_in_one.repo_manager import dependencies as dependencies_module
from sd_webui_all_in_one.repo_manager import RepoManager


def test_repo_manager_init_defers_optional_api_imports(monkeypatch):
    import_calls = []

    def fake_import_module(name):
        import_calls.append(name)
        raise AssertionError(f"{name} should not be imported during RepoManager init")

    monkeypatch.setattr(dependencies_module.importlib, "import_module", fake_import_module)

    manager = RepoManager(hf_token="hf-token", ms_token="ms-token")

    assert import_calls == []
    assert manager.hf_token == "hf-token"
    assert manager.ms_token == "ms-token"


def test_repo_manager_huggingface_api_lazy_init_and_cache(monkeypatch):
    import_calls = []
    init_calls = []

    class FakeHfApi:
        def __init__(self, token=None):
            init_calls.append(token)

    hf_module = types.ModuleType("huggingface_hub")
    hf_module.HfApi = FakeHfApi
    monkeypatch.setitem(sys.modules, "huggingface_hub", hf_module)

    def fake_import_module(name):
        import_calls.append(name)
        assert name == "huggingface_hub"
        return hf_module

    monkeypatch.setattr(dependencies_module.importlib, "import_module", fake_import_module)

    manager = RepoManager(hf_token="hf-token")
    assert import_calls == []

    first_api = manager.hf_api
    second_api = manager.hf_api

    assert first_api is second_api
    assert isinstance(first_api, FakeHfApi)
    assert init_calls == ["hf-token"]
    assert import_calls == ["huggingface_hub"]


def test_repo_manager_modelscope_api_lazy_init_login_and_cache(monkeypatch):
    import_calls = []
    init_calls = []
    login_calls = []

    class FakeMsApi:
        def __init__(self):
            init_calls.append("init")

        def login(self, access_token):
            login_calls.append(access_token)

    modelscope_module = types.ModuleType("modelscope")
    modelscope_module.HubApi = FakeMsApi
    monkeypatch.setitem(sys.modules, "modelscope", modelscope_module)

    def fake_import_module(name):
        import_calls.append(name)
        assert name == "modelscope"
        return modelscope_module

    monkeypatch.setattr(dependencies_module.importlib, "import_module", fake_import_module)

    manager = RepoManager(ms_token="ms-token")
    assert import_calls == []

    first_api = manager.ms_api
    second_api = manager.ms_api

    assert first_api is second_api
    assert isinstance(first_api, FakeMsApi)
    assert init_calls == ["init"]
    assert login_calls == ["ms-token"]
    assert import_calls == ["modelscope"]


def test_repo_manager_modelscope_api_prefers_constructor_token(monkeypatch):
    import_calls = []
    init_calls = []
    login_calls = []

    class FakeMsApi:
        def __init__(self, token=None):
            init_calls.append(token)

        def login(self, access_token):
            login_calls.append(access_token)

    modelscope_module = types.ModuleType("modelscope")
    modelscope_module.HubApi = FakeMsApi
    monkeypatch.setitem(sys.modules, "modelscope", modelscope_module)

    def fake_import_module(name):
        import_calls.append(name)
        assert name == "modelscope"
        return modelscope_module

    monkeypatch.setattr(dependencies_module.importlib, "import_module", fake_import_module)

    manager = RepoManager(ms_token="ms-token")

    first_api = manager.ms_api
    second_api = manager.ms_api

    assert first_api is second_api
    assert isinstance(first_api, FakeMsApi)
    assert init_calls == ["ms-token"]
    assert login_calls == []
    assert import_calls == ["modelscope"]


def test_repo_manager_get_ms_git_token_delegates_without_initializing_api(monkeypatch):
    ensure_calls = []
    token_calls = []

    class FakeModelScopeConfig:
        @staticmethod
        def get_git_token():
            token_calls.append(True)
            return "git-token"

    modelscope_module = types.ModuleType("modelscope")
    modelscope_module.__path__ = []
    hub_module = types.ModuleType("modelscope.hub")
    hub_module.__path__ = []
    api_module = types.ModuleType("modelscope.hub.api")
    api_module.ModelScopeConfig = FakeModelScopeConfig
    monkeypatch.setitem(sys.modules, "modelscope", modelscope_module)
    monkeypatch.setitem(sys.modules, "modelscope.hub", hub_module)
    monkeypatch.setitem(sys.modules, "modelscope.hub.api", api_module)
    monkeypatch.setattr(client_module, "_ensure_modelscope", lambda module_name="modelscope": ensure_calls.append(module_name))

    manager = RepoManager()
    monkeypatch.setattr(manager, "_init_ms_api", lambda: pytest.fail("get_ms_git_token should not initialize HubApi"))

    assert manager.get_ms_git_token() == "git-token"
    assert ensure_calls == ["modelscope.hub.api"]
    assert token_calls == [True]


def test_repo_manager_get_ms_git_token_logs_in_when_persisted_token_is_missing(monkeypatch):
    ensure_calls = []
    login_calls = []

    class FakeModelScopeConfig:
        @staticmethod
        def get_git_token():
            return None

    class FakeMsApi:
        def login(self, token):
            login_calls.append(token)
            return ("login-git-token", object())

    modelscope_module = types.ModuleType("modelscope")
    modelscope_module.__path__ = []
    hub_module = types.ModuleType("modelscope.hub")
    hub_module.__path__ = []
    api_module = types.ModuleType("modelscope.hub.api")
    api_module.ModelScopeConfig = FakeModelScopeConfig
    monkeypatch.setitem(sys.modules, "modelscope", modelscope_module)
    monkeypatch.setitem(sys.modules, "modelscope.hub", hub_module)
    monkeypatch.setitem(sys.modules, "modelscope.hub.api", api_module)
    monkeypatch.setattr(client_module, "_ensure_modelscope", lambda module_name="modelscope": ensure_calls.append(module_name))

    manager = RepoManager(ms_token="ms-token")
    manager.ms_api = FakeMsApi()

    assert manager.get_ms_git_token() == "login-git-token"
    assert ensure_calls == ["modelscope.hub.api"]
    assert login_calls == ["ms-token"]


def test_repo_manager_get_ms_git_token_reads_persisted_token_after_login(monkeypatch):
    token_values = iter((None, "persisted-git-token"))
    login_calls = []

    class FakeModelScopeConfig:
        @staticmethod
        def get_git_token():
            return next(token_values)

    class FakeMsApi:
        def login(self, token):
            login_calls.append(token)
            return None

    modelscope_module = types.ModuleType("modelscope")
    modelscope_module.__path__ = []
    hub_module = types.ModuleType("modelscope.hub")
    hub_module.__path__ = []
    api_module = types.ModuleType("modelscope.hub.api")
    api_module.ModelScopeConfig = FakeModelScopeConfig
    monkeypatch.setitem(sys.modules, "modelscope", modelscope_module)
    monkeypatch.setitem(sys.modules, "modelscope.hub", hub_module)
    monkeypatch.setitem(sys.modules, "modelscope.hub.api", api_module)
    monkeypatch.setattr(client_module, "_ensure_modelscope", lambda module_name="modelscope": None)

    manager = RepoManager(ms_token="ms-token")
    manager.ms_api = FakeMsApi()

    assert manager.get_ms_git_token() == "persisted-git-token"
    assert login_calls == ["ms-token"]


def test_repo_manager_get_ms_git_token_does_not_initialize_api_without_any_token(monkeypatch):
    class FakeModelScopeConfig:
        @staticmethod
        def get_git_token():
            return None

    modelscope_module = types.ModuleType("modelscope")
    modelscope_module.__path__ = []
    hub_module = types.ModuleType("modelscope.hub")
    hub_module.__path__ = []
    api_module = types.ModuleType("modelscope.hub.api")
    api_module.ModelScopeConfig = FakeModelScopeConfig
    monkeypatch.setitem(sys.modules, "modelscope", modelscope_module)
    monkeypatch.setitem(sys.modules, "modelscope.hub", hub_module)
    monkeypatch.setitem(sys.modules, "modelscope.hub.api", api_module)
    monkeypatch.setattr(client_module, "_ensure_modelscope", lambda module_name="modelscope": None)

    manager = RepoManager()
    monkeypatch.setattr(manager, "_init_ms_api", lambda: pytest.fail("get_ms_git_token should not initialize HubApi"))

    assert manager.get_ms_git_token() is None


def test_repo_manager_token_accessors_return_current_tokens():
    manager = RepoManager(hf_token="hf-token", ms_token="ms-token")

    assert manager.get_hf_token() == "hf-token"
    assert manager.get_ms_token() == "ms-token"

    manager.configure_tokens(hf_token="updated-hf-token", ms_token="updated-ms-token")

    assert manager.get_hf_token() == "updated-hf-token"
    assert manager.get_ms_token() == "updated-ms-token"


def test_repo_manager_configure_tokens_updates_environment_and_invalidates_cached_apis(monkeypatch):
    monkeypatch.delenv("HF_TOKEN", raising=False)
    monkeypatch.delenv("MODELSCOPE_API_TOKEN", raising=False)
    manager = RepoManager()
    hf_api = object()
    ms_api = object()
    manager.hf_api = hf_api
    manager.ms_api = ms_api

    manager.configure_tokens(hf_token="hf-token", ms_token="ms-token")

    assert manager.hf_token == "hf-token"
    assert manager.ms_token == "ms-token"
    assert manager._hf_api is client_module._API_NOT_INITIALIZED
    assert manager._ms_api is client_module._API_NOT_INITIALIZED
    assert os.environ["HF_TOKEN"] == "hf-token"
    assert os.environ["MODELSCOPE_API_TOKEN"] == "ms-token"


def test_repo_manager_configure_tokens_keeps_existing_tokens_for_none(monkeypatch):
    manager = RepoManager(hf_token="hf-token", ms_token="ms-token")
    hf_api = object()
    ms_api = object()
    manager.hf_api = hf_api
    manager.ms_api = ms_api
    monkeypatch.setenv("HF_TOKEN", "hf-token")
    monkeypatch.setenv("MODELSCOPE_API_TOKEN", "ms-token")

    manager.configure_tokens(hf_token=None, ms_token=None)

    assert manager.hf_token == "hf-token"
    assert manager.ms_token == "ms-token"
    assert manager._hf_api is hf_api
    assert manager._ms_api is ms_api
    assert os.environ["HF_TOKEN"] == "hf-token"
    assert os.environ["MODELSCOPE_API_TOKEN"] == "ms-token"


def test_repo_manager_huggingface_api_installs_missing_dependency_before_reimport(monkeypatch):
    installed = False
    import_calls = []
    install_calls = []

    class FakeHfApi:
        def __init__(self, token=None):
            self.token = token

    hf_module = types.ModuleType("huggingface_hub")
    hf_module.HfApi = FakeHfApi

    def fake_import_module(name):
        import_calls.append(name)
        assert name == "huggingface_hub"
        if not installed:
            raise ImportError("huggingface_hub missing")
        monkeypatch.setitem(sys.modules, "huggingface_hub", hf_module)
        return hf_module

    def fake_install_optional_dependency(package_name, display_name=None):
        nonlocal installed
        installed = True
        install_calls.append((package_name, display_name))

    monkeypatch.setattr(dependencies_module.importlib, "import_module", fake_import_module)
    monkeypatch.setattr(dependencies_module, "install_optional_dependency", fake_install_optional_dependency)

    manager = RepoManager(hf_token="hf-token")

    assert manager.hf_api.token == "hf-token"
    assert import_calls == ["huggingface_hub", "huggingface_hub"]
    assert install_calls == [("huggingface_hub", "huggingface_hub")]


def test_repo_manager_modelscope_api_installs_missing_dependency_before_reimport(monkeypatch):
    installed = False
    import_calls = []
    install_calls = []
    login_calls = []

    class FakeMsApi:
        def login(self, access_token):
            login_calls.append(access_token)

    modelscope_module = types.ModuleType("modelscope")
    modelscope_module.HubApi = FakeMsApi

    def fake_import_module(name):
        import_calls.append(name)
        assert name == "modelscope"
        if not installed:
            raise ImportError("modelscope missing")
        monkeypatch.setitem(sys.modules, "modelscope", modelscope_module)
        return modelscope_module

    def fake_install_optional_dependency(package_name, display_name=None):
        nonlocal installed
        installed = True
        install_calls.append((package_name, display_name))

    monkeypatch.setattr(dependencies_module.importlib, "import_module", fake_import_module)
    monkeypatch.setattr(dependencies_module, "install_optional_dependency", fake_install_optional_dependency)

    manager = RepoManager(ms_token="ms-token")

    assert manager.ms_api is manager.ms_api
    assert import_calls == ["modelscope", "modelscope"]
    assert install_calls == [("modelscope", "modelscope")]
    assert login_calls == ["ms-token"]


@pytest.mark.parametrize("install_fails", [False, True])
def test_repo_manager_lazy_import_failure_raises_runtime_error(monkeypatch, install_fails):
    def fake_import_module(name):
        assert name == "huggingface_hub"
        raise ImportError("huggingface_hub missing")

    def fake_install_optional_dependency(package_name, display_name=None):
        assert package_name == "huggingface_hub"
        assert display_name == "huggingface_hub"
        if install_fails:
            raise RuntimeError("install failed")

    monkeypatch.setattr(dependencies_module.importlib, "import_module", fake_import_module)
    monkeypatch.setattr(dependencies_module, "install_optional_dependency", fake_install_optional_dependency)

    manager = RepoManager()

    with pytest.raises(RuntimeError, match="huggingface_hub"):
        manager.hf_api
