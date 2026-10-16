"""可选依赖安装测试"""

from sd_webui_all_in_one import optional_dependency


def test_install_optional_dependency_uses_mirror_config(monkeypatch):
    calls = []

    monkeypatch.setattr(optional_dependency, "get_auto_pypi_mirror_config", lambda: {"PIP_INDEX_URL": "https://example.test/simple"})
    monkeypatch.setattr(optional_dependency, "pip_install", lambda *args, **kwargs: calls.append((args, kwargs)))

    optional_dependency.install_optional_dependency("demo-package")

    assert calls == [(("demo-package",), {"custom_env": {"PIP_INDEX_URL": "https://example.test/simple"}})]


def test_try_install_optional_dependency_returns_false_on_install_error(monkeypatch):
    monkeypatch.setattr(optional_dependency, "get_auto_pypi_mirror_config", lambda: {"PIP_INDEX_URL": "https://example.test/simple"})
    monkeypatch.setattr(optional_dependency, "pip_install", lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("install failed")))

    assert optional_dependency.try_install_optional_dependency("demo-package") is False
