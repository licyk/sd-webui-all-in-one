"""TCMalloc 优化测试"""

import os
import subprocess

from sd_webui_all_in_one.optimize import tcmalloc


def test_tcmalloc_common_colab_and_idempotent(monkeypatch, tmp_path):
    outputs = {
        ("ldd", "--version"): "ldd (GNU libc) 2.35\n",
        ("ldconfig", "-p"): "libtcmalloc_minimal.so.4 (libc6,x86-64) => /usr/lib/libtcmalloc_minimal.so.4\n",
    }

    def fake_run(command, **kwargs):
        return subprocess.CompletedProcess(command, 0, stdout=outputs[tuple(command)], stderr="")

    # 被测代码直接写入 os.environ; LD_PRELOAD 原本不存在时 delenv 不会记录任何状态,
    # 先 setenv 让 monkeypatch 记录原始状态, 保证测试结束后移除写入的值, 避免泄漏给后续测试
    # (Windows 上 Git 自带的 sh.exe 会按 LD_PRELOAD 加载不存在的库而崩溃)
    monkeypatch.setenv("LD_PRELOAD", "")
    monkeypatch.delenv("LD_PRELOAD")
    monkeypatch.setattr(tcmalloc, "is_colab_environment", lambda: False)
    monkeypatch.setattr(tcmalloc.subprocess, "run", fake_run)

    assert tcmalloc.get_tcmalloc_path() == "/usr/lib/libtcmalloc_minimal.so.4"

    origin = {"LD_PRELOAD": "existing.so"}
    env = tcmalloc.apply_tcmalloc_preload("/usr/lib/libtcmalloc_minimal.so.4", origin_env=origin)
    assert env["LD_PRELOAD"] == "existing.so:/usr/lib/libtcmalloc_minimal.so.4"
    assert origin["LD_PRELOAD"] == "existing.so"
    assert tcmalloc.get_tcmalloc_var(origin_env=origin) == "existing.so:/usr/lib/libtcmalloc_minimal.so.4"

    info = tcmalloc.get_tcmalloc_info(origin_env=origin)
    assert info is not None
    assert info.path == "/usr/lib/libtcmalloc_minimal.so.4"
    assert info.ld_preload == "existing.so:/usr/lib/libtcmalloc_minimal.so.4"

    manager = tcmalloc.TCMalloc(tmp_path)

    assert manager.configure_tcmalloc_common() is True
    assert os.environ["LD_PRELOAD"] == "/usr/lib/libtcmalloc_minimal.so.4"

    monkeypatch.setattr(tcmalloc, "is_colab_environment", lambda: True)
    monkeypatch.setenv("LD_PRELOAD", "existing.so")
    assert tcmalloc.get_tcmalloc_path().endswith("libtcmalloc_minimal.so.4")
    colab_var = tcmalloc.get_tcmalloc_var(origin_env={"LD_PRELOAD": "base.so"})
    assert colab_var is not None
    assert colab_var.startswith("base.so:")
    assert colab_var.endswith("libtcmalloc_minimal.so.4")

    manager = tcmalloc.TCMalloc(tmp_path)
    assert manager.configure_tcmalloc() is True
    assert "existing.so:" in os.environ["LD_PRELOAD"]
    assert os.environ["LD_PRELOAD"].endswith("libtcmalloc_minimal.so.4")

    monkeypatch.setattr(manager, "configure_tcmalloc_colab", lambda: (_ for _ in ()).throw(AssertionError("already configured")))
    assert manager.configure_tcmalloc() is True


def test_tcmalloc_common_handles_missing_glibc(monkeypatch, tmp_path):
    monkeypatch.setattr(tcmalloc.subprocess, "run", lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("no ldd")))
    assert tcmalloc.get_common_tcmalloc_path() is None
    assert tcmalloc.TCMalloc(tmp_path).configure_tcmalloc_common() is False


def test_tcmalloc_common_requires_libpthread_before_glibc_234(monkeypatch):
    outputs = {
        ("ldd", "--version"): "ldd (GNU libc) 2.33\n",
        ("ldconfig", "-p"): "\n".join(
            [
                "libtcmalloc_minimal.so.4 (libc6,x86-64) => /usr/lib/libtcmalloc_minimal.so.4",
                "libtcmalloc.so.4 (libc6,x86-64) => /usr/lib/libtcmalloc.so.4",
            ]
        ),
        ("ldd", "/usr/lib/libtcmalloc_minimal.so.4"): "libc.so.6 => /usr/lib/libc.so.6\n",
        ("ldd", "/usr/lib/libtcmalloc.so.4"): "libpthread.so.0 => /usr/lib/libpthread.so.0\n",
    }
    calls = []

    def fake_run(command, **kwargs):
        calls.append(tuple(command))
        return subprocess.CompletedProcess(command, 0, stdout=outputs[tuple(command)], stderr="")

    monkeypatch.setattr(tcmalloc.subprocess, "run", fake_run)

    assert tcmalloc.get_common_tcmalloc_path() == "/usr/lib/libtcmalloc.so.4"
    assert ("ldd", "/usr/lib/libtcmalloc_minimal.so.4") in calls
    assert ("ldd", "/usr/lib/libtcmalloc.so.4") in calls


def test_tcmalloc_common_handles_missing_candidates(monkeypatch):
    outputs = {
        ("ldd", "--version"): "ldd (GNU libc) 2.35\n",
        ("ldconfig", "-p"): "libc.so.6 (libc6,x86-64) => /usr/lib/libc.so.6\n",
    }

    def fake_run(command, **kwargs):
        return subprocess.CompletedProcess(command, 0, stdout=outputs[tuple(command)], stderr="")

    monkeypatch.setattr(tcmalloc, "is_colab_environment", lambda: False)
    monkeypatch.setattr(tcmalloc.subprocess, "run", fake_run)

    assert tcmalloc.get_common_tcmalloc_path() is None
    assert tcmalloc.get_tcmalloc_info() is None
    assert tcmalloc.get_tcmalloc_var() is None
