import json
import os
import sys
import types
import warnings
from pathlib import Path

import pytest

from sd_webui_all_in_one.notebook_manager import base_manager as notebook_base
from sd_webui_all_in_one.notebook_manager import comfyui_manager
from sd_webui_all_in_one.notebook_manager import fooocus_manager
from sd_webui_all_in_one.notebook_manager import invokeai_manager
from sd_webui_all_in_one.notebook_manager import qwen_tts_webui_manager
from sd_webui_all_in_one.notebook_manager import sd_scripts_manager
from sd_webui_all_in_one.notebook_manager import sd_trainer_manager
from sd_webui_all_in_one.notebook_manager import sd_trainer_scripts_manager


class FakeRepoManager:
    def __init__(self, hf_token=None, ms_token=None):
        self.hf_token = hf_token
        self.ms_token = ms_token


class FakeTunnelManager:
    def __init__(self, workspace, port):
        self.workspace = workspace
        self.port = port

    def stop_all(self):
        pass


class FakeTCMalloc:
    def __init__(self, workspace):
        self.workspace = workspace

    def configure_tcmalloc(self):
        return True


@pytest.fixture(autouse=True)
def fake_base_dependencies(monkeypatch):
    monkeypatch.setattr(notebook_base, "RepoManager", FakeRepoManager)
    monkeypatch.setattr(notebook_base, "TunnelManager", FakeTunnelManager)
    monkeypatch.setattr(notebook_base, "TCMalloc", FakeTCMalloc)


def test_product_notebook_launch_commands_and_run_delegate(monkeypatch, tmp_path):
    cases = [
        (comfyui_manager.ComfyUIManager, "ComfyUI", "main.py"),
        (fooocus_manager.FooocusManager, "Fooocus", "launch.py"),
        (qwen_tts_webui_manager.QwenTTSWebUIManager, "Qwen TTS WebUI", "launch.py"),
        (sd_trainer_manager.SDTrainerManager, "SD Trainer", "gui.py"),
    ]

    for cls, name, script in cases:
        manager = cls(tmp_path / name, "app")
        calls = []
        manager.launch = lambda **kwargs: calls.append(kwargs)
        command = manager.get_launch_command('--listen --theme "dark mode"')

        assert Path(sys.executable).as_posix() in command
        assert ((tmp_path / name / "app" / script).as_posix()) in command
        assert "--listen" in command

        manager.run(params=["--port", "7861"], display_mode="terminal")
        assert calls == [
            {
                "name": name,
                "base_path": tmp_path / name / "app",
                "cmd": manager.get_launch_command(["--port", "7861"]),
                "display_mode": "terminal",
            }
        ]


def test_sd_trainer_launch_command_prefers_kohya_gui_when_gui_missing(tmp_path):
    manager = sd_trainer_manager.SDTrainerManager(tmp_path, "trainer")
    trainer_path = tmp_path / "trainer"
    trainer_path.mkdir(parents=True)
    (trainer_path / "kohya_gui.py").write_text("print('ok')", encoding="utf-8")

    command = manager.get_launch_command()

    assert (trainer_path / "kohya_gui.py").as_posix() in command


@pytest.mark.parametrize(
    ("cls", "model_path"),
    [
        (comfyui_manager.ComfyUIManager, "models/loras"),
        (fooocus_manager.FooocusManager, "models/loras"),
    ],
)
def test_image_product_model_download_helpers_delegate(monkeypatch, tmp_path, cls, model_path):
    manager = cls(tmp_path, "app")
    calls = []
    manager.get_model = lambda **kwargs: calls.append(kwargs) or kwargs["path"] / (kwargs["filename"] or "file.bin")

    result = manager.get_sd_model("https://example.test/model.bin", filename="model.safetensors", model_type="loras")
    manager.get_sd_model_from_list(
        [
            {"url": "https://example.test/a.bin", "type": "loras", "filename": "a.safetensors"},
            {"url": "https://example.test/b.bin"},
        ]
    )

    assert result == tmp_path / "app" / model_path / "model.safetensors"
    assert calls[0] == {
        "url": "https://example.test/model.bin",
        "path": tmp_path / "app" / model_path,
        "filename": "model.safetensors",
        "tool": "aria2",
    }
    assert calls[1]["path"] == tmp_path / "app" / model_path
    assert calls[2]["path"] == tmp_path / "app" / "models/checkpoints"


def test_sd_trainer_and_invokeai_model_download_helpers_delegate(tmp_path):
    trainer = sd_trainer_manager.SDTrainerManager(tmp_path, "trainer")
    invoke = invokeai_manager.InvokeAIManager(tmp_path, "invoke")

    trainer_calls = []
    invoke_calls = []
    trainer.get_model = lambda **kwargs: trainer_calls.append(kwargs)
    invoke.get_model = lambda **kwargs: invoke_calls.append(kwargs)

    trainer.get_sd_model_from_list([{"url": "https://example.test/a.bin", "filename": "a.safetensors"}])
    invoke.get_sd_model_from_list(["https://example.test/b.bin"])

    assert trainer_calls == [
        {
            "url": "https://example.test/a.bin",
            "path": tmp_path / "trainer" / "sd-models",
            "filename": "a.safetensors",
            "tool": "aria2",
        }
    ]
    assert invoke_calls == [
        {"url": "https://example.test/b.bin", "path": tmp_path / "invoke" / "sd-models", "filename": None, "tool": "aria2"}
    ]


def test_mount_drive_links_expected_product_paths(monkeypatch, tmp_path):
    cases = [
        (comfyui_manager.ComfyUIManager, "comfyui_output", ["output", "user", "input", "extra_model_paths.yaml"]),
        (fooocus_manager.FooocusManager, "fooocus_output", ["outputs", "presets", "language", "wildcards", "config.txt"]),
        (qwen_tts_webui_manager.QwenTTSWebUIManager, "qwen_tts_webui_output", ["outputs", "config.json"]),
        (sd_trainer_manager.SDTrainerManager, "sd_trainer_output", ["outputs", "output", "config", "train", "logs"]),
    ]

    for cls, drive_dir, expected_links in cases:
        manager = cls(tmp_path / drive_dir, "app")
        calls = []
        manager.mount_google_drive_for_notebook = lambda: True
        manager.link_to_google_drive = lambda **kwargs: calls.append(kwargs)
        manager.mount_drive(extras=[{"link_dir": "extra"}])

        assert calls[0]["base_dir"] == tmp_path / drive_dir / "app"
        assert calls[0]["drive_path"] == Path("/content/drive") / "MyDrive" / drive_dir
        assert [item["link_dir"] for item in calls[0]["links"]] == expected_links + ["extra"]


def test_invokeai_mount_drive_sets_root_and_import_model_is_quiet(monkeypatch, tmp_path):
    manager = invokeai_manager.InvokeAIManager(tmp_path, "invoke")
    imported = []

    manager.mount_google_drive_for_notebook = lambda: True
    monkeypatch.setattr(invokeai_manager, "Path", lambda value: tmp_path / "content" / "drive" if value == "/content/drive" else Path(value))
    monkeypatch.setattr(invokeai_manager, "get_file_list", lambda _path: [tmp_path / "model.safetensors"])
    monkeypatch.setattr(invokeai_manager, "import_model_to_invokeai", lambda models: imported.extend(models))

    manager.mount_drive()
    assert os.environ["INVOKEAI_ROOT"] == (tmp_path / "content" / "drive" / "MyDrive" / "invokeai_output").as_posix()

    manager.import_model()
    assert imported == [tmp_path / "model.safetensors"]


def test_notebook_check_env_methods_delegate(monkeypatch, tmp_path):
    calls = []
    mappings = [
        (comfyui_manager, comfyui_manager.ComfyUIManager, "check_comfyui_env", "comfyui_path"),
        (fooocus_manager, fooocus_manager.FooocusManager, "check_fooocus_env", "fooocus_path"),
        (qwen_tts_webui_manager, qwen_tts_webui_manager.QwenTTSWebUIManager, "check_qwen_tts_webui_env", "qwen_tts_webui_path"),
        (invokeai_manager, invokeai_manager.InvokeAIManager, "check_invokeai_env", None),
        (sd_trainer_manager, sd_trainer_manager.SDTrainerManager, "check_sd_trainer_env", "sd_trainer_path"),
        (sd_trainer_scripts_manager, sd_trainer_scripts_manager.SDTrainerScriptsManager, "check_sd_scripts_env", "sd_scripts_path"),
    ]

    for module, cls, attr, path_kw in mappings:
        def _record(name):
            return lambda **kwargs: calls.append((name, kwargs))

        monkeypatch.setattr(module, attr, _record(attr))

    monkeypatch.setattr(sd_trainer_manager.SDTrainerManager, "check_protobuf", lambda self, use_uv=True: calls.append(("protobuf", {"use_uv": use_uv})))

    for _module, cls, attr, path_kw in mappings:
        manager = cls(tmp_path, "app")
        manager.check_env(use_uv=False, use_pypi_mirror=True, use_github_mirror=True, custom_github_mirror="mirror")

    assert calls[0][0] == "check_comfyui_env"
    assert calls[0][1]["comfyui_path"] == tmp_path / "app"
    assert calls[3][0] == "check_invokeai_env"
    assert "invokeai_path" not in calls[3][1]
    assert ("protobuf", {"use_uv": False}) in calls


def test_fooocus_config_path_and_pre_download_model(monkeypatch, tmp_path):
    manager = fooocus_manager.FooocusManager(tmp_path, "fooocus")
    preset_dir = tmp_path / "fooocus" / "presets"
    preset_dir.mkdir(parents=True)
    config_path = preset_dir / "demo.json"
    config_path.write_text(
        json.dumps(
            {
                "checkpoint_downloads": {"model.safetensors": "https://example.test/model"},
                "lora_downloads": {"lora.safetensors": "https://example.test/lora"},
            }
        ),
        encoding="utf-8",
    )

    captured = []

    class FakeDownloader:
        def __init__(self, download_func, download_kwargs_list):
            captured.append((download_func, download_kwargs_list))

        def start(self, num_threads):
            captured.append(("start", num_threads))

    monkeypatch.setattr(fooocus_manager, "MultiThreadDownloader", FakeDownloader)
    monkeypatch.setattr(fooocus_manager, "download_file", "download-func")

    assert manager.get_config_path_from_args('--preset demo --listen') == config_path
    manager.pre_download_model("--preset demo", thread_num=3, downloader="urllib")

    assert captured[0][0] == "download-func"
    assert captured[0][1] == [
        {
            "url": "https://example.test/model",
            "path": tmp_path / "fooocus" / "models/checkpoints",
            "save_name": "model.safetensors",
            "tool": "urllib",
            "progress": False,
        },
        {
            "url": "https://example.test/lora",
            "path": tmp_path / "fooocus" / "models/loras",
            "save_name": "lora.safetensors",
            "tool": "urllib",
            "progress": False,
        },
    ]
    assert captured[1] == ("start", 3)


def test_sd_scripts_deprecated_compat_repo_and_helpers(monkeypatch, tmp_path):
    with pytest.warns(DeprecationWarning):
        manager = sd_scripts_manager.SDScriptsManager(tmp_path, "scripts")

    calls = []
    manager.download_files_from_repo = lambda **kwargs: calls.append(("download", kwargs))
    manager.upload_files_to_repo = lambda **kwargs: calls.append(("upload", kwargs))
    manager.download_and_extract = lambda **kwargs: calls.append(("archive", kwargs))
    manager.display_directories_tree = lambda *args, **kwargs: calls.append(("tree", args, kwargs))
    manager.import_file_from_kaggle_input = lambda output_path: calls.append(("kaggle", output_path))

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        manager.repo.download_files_from_repo("huggingface", "owner/repo", tmp_path / "local", folder="aa")
        manager.repo.upload_files_to_repo("modelscope", "owner/repo", tmp_path / "upload", visibility=True)
        manager.download_archive_and_unpack("https://example.test/a.zip", tmp_path / "out", name="a.zip")
        manager.display_model_and_dataset_dir(tmp_path)
        manager.import_kaggle_input(tmp_path / "kaggle")

    assert calls[0] == (
        "download",
        {"api_type": "huggingface", "repo_id": "owner/repo", "local_dir": tmp_path / "local", "repo_type": "model", "folder": "aa", "num_threads": 16},
    )
    assert calls[1][0] == "upload"
    assert calls[2] == ("archive", {"url": "https://example.test/a.zip", "local_dir": tmp_path / "out", "name": "a.zip"})
    assert calls[-1] == ("kaggle", tmp_path / "kaggle")
