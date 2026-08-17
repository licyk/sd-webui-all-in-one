from pathlib import Path
from types import SimpleNamespace

import sd_webui_all_in_one as package
from sd_webui_all_in_one import env_manager


def test_generate_proxy_env_vars():
    assert env_manager.generate_proxy_env_vars() == {
        "NO_PROXY": "localhost,127.0.0.1,::1",
    }
    assert env_manager.generate_proxy_env_vars("http://proxy.local:8080") == {
        "NO_PROXY": "localhost,127.0.0.1,::1",
        "HTTP_PROXY": "http://proxy.local:8080",
        "HTTPS_PROXY": "http://proxy.local:8080",
    }


def test_apply_proxy_uses_generated_environment(monkeypatch):
    calls = []

    def generate_proxy_env_vars(proxy_address=None):
        calls.append(proxy_address)
        if proxy_address is None:
            return {"TEST_NO_PROXY": "localhost"}
        return {"TEST_HTTP_PROXY": proxy_address, "TEST_HTTPS_PROXY": proxy_address}

    monkeypatch.setattr(package, "SD_WEBUI_ALL_IN_ONE_PROXY", True)
    monkeypatch.setattr(package, "generate_proxy_env_vars", generate_proxy_env_vars)
    monkeypatch.setattr(package, "get_system_proxy_address", lambda: "http://proxy.local:8080")
    monkeypatch.setattr(package, "test_proxy_connectivity", lambda proxy_address: True)
    monkeypatch.delenv("TEST_NO_PROXY", raising=False)
    monkeypatch.delenv("TEST_HTTP_PROXY", raising=False)
    monkeypatch.delenv("TEST_HTTPS_PROXY", raising=False)

    package._apply_proxy()

    assert calls == [None, "http://proxy.local:8080"]
    assert package.os.environ["TEST_NO_PROXY"] == "localhost"
    assert package.os.environ["TEST_HTTP_PROXY"] == "http://proxy.local:8080"
    assert package.os.environ["TEST_HTTPS_PROXY"] == "http://proxy.local:8080"


def test_generate_cache_path_env_vars_preserves_existing_values():
    cache_path = Path("C:/cache")
    origin_env = {"HF_HOME": "/custom/huggingface"}

    env = env_manager.generate_cache_path_env_vars(cache_path, origin_env)

    assert origin_env == {"HF_HOME": "/custom/huggingface"}
    assert env["CACHE_HOME"] == cache_path.as_posix()
    assert env["HF_HOME"] == "/custom/huggingface"
    assert env["MODELSCOPE_CACHE"] == (cache_path / "modelscope" / "hub").as_posix()
    assert env["UV_CACHE_DIR"] == (cache_path / "uv").as_posix()


def test_apply_cache_path_uses_generated_environment(monkeypatch):
    monkeypatch.setattr(package, "SD_WEBUI_ALL_IN_ONE_SET_CACHE_PATH", True)
    monkeypatch.setattr(package, "generate_cache_path_env_vars", lambda cache_path: {"TEST_CACHE_HOME": "/cache"})
    monkeypatch.delenv("TEST_CACHE_HOME", raising=False)

    package._apply_cache_path()

    assert package.os.environ["TEST_CACHE_HOME"] == "/cache"


def test_generate_config_file_env_vars():
    config_dir = Path("C:/config")
    env = env_manager.generate_config_file_env_vars(config_dir)

    assert env == {
        "PIP_CONFIG_FILE": (config_dir / "pip.ini").as_posix(),
        "UV_CONFIG_FILE": (config_dir / "uv.toml").as_posix(),
        "GIT_CONFIG_GLOBAL": (config_dir / ".gitconfig").as_posix(),
    }


def test_apply_config_file_uses_generated_environment(monkeypatch):
    config_dir = Path("C:/config")
    config_env = {
        "PIP_CONFIG_FILE": (config_dir / "custom-pip.ini").as_posix(),
        "UV_CONFIG_FILE": (config_dir / "custom-uv.toml").as_posix(),
        "GIT_CONFIG_GLOBAL": (config_dir / "custom-gitconfig").as_posix(),
    }
    writes = []
    monkeypatch.setattr(package, "SD_WEBUI_ALL_IN_ONE_DESKTOP_MODE", True)
    monkeypatch.setattr(package, "_temp_dir", SimpleNamespace(name=config_dir))
    monkeypatch.setattr(package, "generate_config_file_env_vars", lambda config_dir: config_env)
    monkeypatch.setattr(Path, "write_text", lambda self, data, encoding: writes.append((self, data, encoding)))

    package._apply_config_file()

    assert all(package.os.environ[key] == value for key, value in config_env.items())
    assert writes == [
        (Path(config_env["PIP_CONFIG_FILE"]), "", "utf-8"),
        (Path(config_env["UV_CONFIG_FILE"]), "", "utf-8"),
        (Path(config_env["GIT_CONFIG_GLOBAL"]), package.DEFAULT_GIT_CONFIG, "utf-8"),
    ]
