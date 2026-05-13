import builtins
import os
import socket
import subprocess
import sys
import types
import urllib.error
from pathlib import Path

import pytest

from sd_webui_all_in_one import colab_tools
from sd_webui_all_in_one import kaggle_tools
from sd_webui_all_in_one import proxy
from sd_webui_all_in_one import utils
from sd_webui_all_in_one.optimize import cuda_malloc
from sd_webui_all_in_one.optimize import tcmalloc


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


def test_proxy_platform_parsers_and_env(monkeypatch, tmp_path):
    class FakeReg:
        def __enter__(self):
            return object()

        def __exit__(self, *_args):
            return False

    fake_winreg = types.SimpleNamespace(
        HKEY_CURRENT_USER=1,
        KEY_READ=2,
        OpenKey=lambda *_args: FakeReg(),
        QueryValueEx=lambda _reg, name: (1, None) if name == "ProxyEnable" else ("http=127.0.0.1:7890;socks=127.0.0.1:1080", None),
    )
    monkeypatch.setitem(sys.modules, "winreg", fake_winreg)
    assert proxy.get_windows_proxy_address() == "http://127.0.0.1:7890"

    gsettings = {
        ("gsettings", "get", "org.gnome.system.proxy", "mode"): "'manual'\n",
        ("gsettings", "get", "org.gnome.system.proxy.http", "host"): "'localhost'\n",
        ("gsettings", "get", "org.gnome.system.proxy.http", "port"): "8080\n",
    }
    monkeypatch.setattr(proxy, "run_cmd", lambda command, live=False: gsettings[tuple(command)])
    assert proxy.get_linux_proxy_address() == "http://localhost:8080"

    monkeypatch.setattr(proxy, "run_cmd", lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("no gsettings")))
    kde_config = tmp_path / ".config" / "kioslaverc"
    kde_config.parent.mkdir()
    kde_config.write_text("[Proxy Settings]\nProxyType=1\nsocksProxy=socks://127.0.0.1 1080\n", encoding="utf-8")
    monkeypatch.setattr(proxy, "Path", lambda value: kde_config if value == "~/.config/kioslaverc" else Path(value))
    assert proxy.get_linux_proxy_address() == "socks://127.0.0.1:1080"

    mac_output = "HTTPSEnable : 1\nHTTPSProxy : proxy.local\nHTTPSPort : 4443\n"
    monkeypatch.setattr(proxy, "run_cmd", lambda *_args, **_kwargs: mac_output)
    assert proxy.get_macos_proxy_address() == "http://proxy.local:4443"

    monkeypatch.setattr(proxy.sys, "platform", "darwin")
    assert proxy.get_system_proxy_address() == "http://proxy.local:4443"

    proxy.set_proxy("http://proxy.local:8080")
    assert os.environ["HTTP_PROXY"] == "http://proxy.local:8080"
    assert os.environ["HTTPS_PROXY"] == "http://proxy.local:8080"
    proxy.clean_proxy()
    assert "HTTP_PROXY" not in os.environ
    assert "HTTPS_PROXY" not in os.environ


def test_proxy_connectivity_uses_tcp_socket(monkeypatch):
    events = []

    class FakeSocket:
        def settimeout(self, timeout):
            events.append(("timeout", timeout))

        def connect(self, address):
            events.append(("connect", address))

        def close(self):
            events.append("close")

    monkeypatch.setattr(proxy.socket, "socket", lambda *_args: FakeSocket())
    assert proxy.test_proxy_connectivity("http://127.0.0.1:7890", timeout=2) is True
    assert ("connect", ("127.0.0.1", 7890)) in events

    assert proxy.test_proxy_connectivity("not-a-proxy") is False

    class BadSocket(FakeSocket):
        def connect(self, address):
            raise socket.error("closed")

    monkeypatch.setattr(proxy.socket, "socket", lambda *_args: BadSocket())
    assert proxy.test_proxy_connectivity("socks://127.0.0.1:1080") is False


def test_colab_and_kaggle_helpers_with_fake_modules(monkeypatch, tmp_path):
    monkeypatch.setattr(colab_tools, "Path", lambda _path: types.SimpleNamespace(exists=lambda: True))
    assert colab_tools.is_colab_environment() is True

    drive_calls = []
    fake_colab = types.ModuleType("google.colab")
    fake_colab.drive = types.SimpleNamespace(mount=lambda path: drive_calls.append(path))
    fake_colab.userdata = types.SimpleNamespace(get=lambda key: f"secret-{key}")
    monkeypatch.setitem(sys.modules, "google", types.ModuleType("google"))
    monkeypatch.setitem(sys.modules, "google.colab", fake_colab)

    mount_path = tmp_path / "drive"
    colab_tools.mount_google_drive(mount_path)
    assert drive_calls == [mount_path.as_posix()]
    assert colab_tools.get_colab_secret("TOKEN") == "secret-TOKEN"

    class FakeSecretsClient:
        def get_secret(self, key):
            return f"kaggle-{key}"

    monkeypatch.setitem(sys.modules, "kaggle_secrets", types.SimpleNamespace(UserSecretsClient=FakeSecretsClient))
    assert kaggle_tools.get_kaggle_secret("TOKEN") == "kaggle-TOKEN"

    copied = []
    fake_inputs = [tmp_path / "input-a", tmp_path / "input-b"]
    for path in fake_inputs:
        path.mkdir()

    class FakePathFactory:
        def __call__(self, value):
            if value == "/kaggle/input":
                return types.SimpleNamespace(is_dir=lambda: True, iterdir=lambda: iter(fake_inputs))
            return Path(value)

    monkeypatch.setattr(kaggle_tools, "Path", FakePathFactory())
    monkeypatch.setattr(kaggle_tools, "copy_files", lambda src, dst: copied.append((src, dst)))

    out = tmp_path / "out"
    kaggle_tools.import_kaggle_input(out)
    assert copied == [(fake_inputs[0], out), (fake_inputs[1], out)]


def test_cuda_malloc_detection_and_env_merge(monkeypatch):
    monkeypatch.setattr(cuda_malloc, "get_gpu_names", lambda: {"NVIDIA GeForce RTX 4090"})
    assert cuda_malloc.is_nvidia_device() is True
    assert cuda_malloc.cuda_malloc_supported() is True
    assert cuda_malloc.get_pytorch_cuda_alloc_conf(is_cuda=True) == "cuda_malloc"

    monkeypatch.setattr(cuda_malloc, "get_gpu_names", lambda: {"GeForce GTX 1650"})
    assert cuda_malloc.cuda_malloc_supported() is False
    assert cuda_malloc.get_pytorch_cuda_alloc_conf(is_cuda=True) == "pytorch_malloc"

    monkeypatch.setattr(cuda_malloc, "get_gpu_names", lambda: {"AMD Radeon"})
    assert cuda_malloc.is_nvidia_device() is False
    assert cuda_malloc.get_pytorch_cuda_alloc_conf(is_cuda=True) is None

    origin = {"PYTORCH_CUDA_ALLOC_CONF": "old", "PYTORCH_ALLOC_CONF": ""}
    env = cuda_malloc.apply_pytorch_alloc_conf("backend:cudaMallocAsync", origin_env=origin)
    assert env["PYTORCH_CUDA_ALLOC_CONF"] == "backend:cudaMallocAsync,old"
    assert env["PYTORCH_ALLOC_CONF"] == "backend:cudaMallocAsync"
    assert origin["PYTORCH_CUDA_ALLOC_CONF"] == "old"


def test_tcmalloc_common_colab_and_idempotent(monkeypatch, tmp_path):
    outputs = {
        ("ldd", "--version"): "ldd (GNU libc) 2.35\n",
        ("ldconfig", "-p"): "libtcmalloc_minimal.so.4 (libc6,x86-64) => /usr/lib/libtcmalloc_minimal.so.4\n",
    }

    def fake_run(command, **kwargs):
        return subprocess.CompletedProcess(command, 0, stdout=outputs[tuple(command)], stderr="")

    monkeypatch.delenv("LD_PRELOAD", raising=False)
    monkeypatch.setattr(tcmalloc.subprocess, "run", fake_run)
    manager = tcmalloc.TCMalloc(tmp_path)

    assert manager.configure_tcmalloc_common() is True
    assert os.environ["LD_PRELOAD"] == "/usr/lib/libtcmalloc_minimal.so.4"

    monkeypatch.setattr(tcmalloc, "is_colab_environment", lambda: True)
    monkeypatch.setenv("LD_PRELOAD", "existing.so")
    manager = tcmalloc.TCMalloc(tmp_path)
    assert manager.configure_tcmalloc() is True
    assert "existing.so:" in os.environ["LD_PRELOAD"]
    assert os.environ["LD_PRELOAD"].endswith("libtcmalloc_minimal.so.4")

    monkeypatch.setattr(manager, "configure_tcmalloc_colab", lambda: (_ for _ in ()).throw(AssertionError("already configured")))
    assert manager.configure_tcmalloc() is True


def test_tcmalloc_common_handles_missing_glibc(monkeypatch, tmp_path):
    monkeypatch.setattr(tcmalloc.subprocess, "run", lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("no ldd")))
    assert tcmalloc.TCMalloc(tmp_path).configure_tcmalloc_common() is False
