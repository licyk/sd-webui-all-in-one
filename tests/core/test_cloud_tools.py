"""Colab / Kaggle 工具测试"""

import sys
import types
from pathlib import Path

from sd_webui_all_in_one import colab_tools, kaggle_tools


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
