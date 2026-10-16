"""通用工具函数测试"""

import builtins
import os
import urllib.error

import pytest

from sd_webui_all_in_one import utils


def test_utils_jupyter_loading_paths_ports_and_network(monkeypatch, tmp_path):
    ZMQInteractiveShell = type("ZMQInteractiveShell", (), {})
    monkeypatch.setattr(utils, "get_ipython", lambda: ZMQInteractiveShell(), raising=False)
    assert utils.in_jupyter() is True

    script = tmp_path / "demo.py"
    script.write_text("VALUE = 42\n", encoding="utf-8")
    assert utils.exec_from_path(script)["VALUE"] == 42

    package_root = tmp_path / "pkgroot"
    module_path = package_root / "pkg" / "mod.py"
    module_path.parent.mkdir(parents=True)
    module_path.write_text("NAME = 'ok'\n", encoding="utf-8")
    monkeypatch.syspath_prepend(package_root.as_posix())
    assert utils.load_source_directly("pkg.mod")["NAME"] == "ok"

    origin = {"PYTHONPATH": "old"}
    env = utils.append_python_path(tmp_path, origin_env=origin)
    assert env["PYTHONPATH"] == tmp_path.as_posix() + os.pathsep + "old"
    assert origin["PYTHONPATH"] == "old"
    assert utils.normalized_filepath("relative").is_absolute()

    used_ports = {9000, 9001}
    monkeypatch.setattr(utils, "is_port_in_use", lambda port: port in used_ports)
    assert utils.find_port(9000) == 9002

    class GoodResponse:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

    monkeypatch.setattr(utils.urllib.request, "urlopen", lambda *_args, **_kwargs: GoodResponse())
    assert utils.network_gfw_test(timeout=1) is True

    monkeypatch.setattr(utils.urllib.request, "urlopen", lambda *_args, **_kwargs: (_ for _ in ()).throw(urllib.error.URLError("blocked")))
    assert utils.network_gfw_test(timeout=1) is False


def test_clear_jupyter_output_import_failure_is_wrapped(monkeypatch):
    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "IPython.display":
            raise ImportError("missing")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    with pytest.raises(RuntimeError, match="Jupyter"):
        utils.clear_jupyter_output()
