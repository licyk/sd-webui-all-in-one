import asyncio
import hashlib
import importlib
import importlib.util
import sys
import textwrap
import types

import pytest

from sd_webui_all_in_one_hotpatcher import monkey_zoo, uninstall_import_hook
from sd_webui_all_in_one_hotpatcher_ext.hf_endpoint_mirror import (
    apply_from_config,
    apply_mirror,
    patch_comfyui_wd14_tagger,
    patch_sd_webui_load_file_from_url,
    patch_torchhub,
    patch_torchvision,
    rewrite_huggingface_url,
)


HF_URL = "https://huggingface.co/user/repo/resolve/main/model.bin"
MIRROR_URL = "https://hf.example/user/repo/resolve/main/model.bin"


@pytest.fixture(autouse=True)
def clean_import_state(monkeypatch):
    uninstall_import_hook()
    monkey_zoo.clear()
    monkeypatch.delenv("HF_ENDPOINT", raising=False)
    before_path = list(sys.path)
    yield
    uninstall_import_hook()
    monkey_zoo.clear()
    sys.path[:] = before_path
    for name in list(sys.modules):
        if (
            name == "torch"
            or name.startswith("torch.")
            or name == "torchvision"
            or name.startswith("torchvision.")
            or name == "modules"
            or name.startswith("modules.")
            or name == "ComfyUI-WD14-Tagger"
            or name.startswith("ComfyUI-WD14-Tagger.")
        ):
            sys.modules.pop(name, None)


def write_file(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(content), encoding="utf-8")


def load_module_from_path(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def test_rewrite_huggingface_url_uses_hf_endpoint(monkeypatch):
    assert rewrite_huggingface_url(HF_URL) == HF_URL

    monkeypatch.setenv("HF_ENDPOINT", "https://hf.example/")

    assert rewrite_huggingface_url(HF_URL) == MIRROR_URL
    assert rewrite_huggingface_url("https://huggingface.co/user/repo?download=1#frag") == (
        "https://hf.example/user/repo?download=1#frag"
    )
    monkeypatch.setenv("HF_ENDPOINT", "https://hf.example/base/")
    assert rewrite_huggingface_url(HF_URL) == "https://hf.example/base/user/repo/resolve/main/model.bin"
    monkeypatch.setenv("HF_ENDPOINT", "hf.example")
    assert rewrite_huggingface_url(HF_URL) == HF_URL
    assert rewrite_huggingface_url("https://example.com/user/repo") == "https://example.com/user/repo"
    assert rewrite_huggingface_url("https://huggingface.co.evil/user/repo") == (
        "https://huggingface.co.evil/user/repo"
    )
    assert rewrite_huggingface_url(None) is None


def test_patch_torchhub_rewrites_download_url_to_file(tmp_path, monkeypatch):
    write_file(tmp_path / "torch" / "__init__.py", "")
    write_file(
        tmp_path / "torch" / "hub.py",
        """
        calls = []

        def download_url_to_file(url, dst, *args, **kwargs):
            calls.append((url, dst, args, kwargs))
            return url
        """,
    )
    sys.path.insert(0, str(tmp_path))
    monkeypatch.setenv("HF_ENDPOINT", "https://hf.example")

    patch_torchhub()
    module = importlib.import_module("torch.hub")

    assert module.download_url_to_file(HF_URL, "/tmp/model") == MIRROR_URL
    assert module.calls[-1][0] == MIRROR_URL


def test_patch_torchvision_rewrites_urlretrieve(tmp_path, monkeypatch):
    write_file(tmp_path / "torchvision" / "__init__.py", "")
    write_file(tmp_path / "torchvision" / "datasets" / "__init__.py", "")
    write_file(
        tmp_path / "torchvision" / "datasets" / "utils.py",
        """
        calls = []

        def _urlretrieve(url, fpath, *args, **kwargs):
            calls.append((url, fpath, args, kwargs))
            return url
        """,
    )
    sys.path.insert(0, str(tmp_path))
    monkeypatch.setenv("HF_ENDPOINT", "https://hf.example")

    patch_torchvision()
    module = importlib.import_module("torchvision.datasets.utils")

    assert module._urlretrieve(HF_URL, "/tmp/model") == MIRROR_URL
    assert module.calls[-1][0] == MIRROR_URL


def test_patch_comfyui_wd14_tagger_rewrites_async_download(tmp_path, monkeypatch):
    module_path = tmp_path / "ComfyUI-WD14-Tagger.pysssss.py"
    write_file(
        module_path,
        """
        calls = []

        def download_to_file(url, dst, *args, **kwargs):
            calls.append((url, dst, args, kwargs))
            return url
        """,
    )
    monkeypatch.setenv("HF_ENDPOINT", "https://hf.example")

    patch_comfyui_wd14_tagger()
    module = load_module_from_path("ComfyUI-WD14-Tagger.pysssss", module_path)

    result = asyncio.run(module.download_to_file(HF_URL, "/tmp/model"))

    assert result == MIRROR_URL
    assert module.calls[-1][0] == MIRROR_URL


def test_apply_mirror_keeps_original_url_without_endpoint(tmp_path):
    write_file(tmp_path / "torch" / "__init__.py", "")
    write_file(
        tmp_path / "torch" / "hub.py",
        """
        calls = []

        def download_url_to_file(url, dst):
            calls.append((url, dst))
            return url
        """,
    )
    sys.path.insert(0, str(tmp_path))

    apply_mirror()
    module = importlib.import_module("torch.hub")

    assert module.download_url_to_file(HF_URL, "/tmp/model") == HF_URL
    assert module.download_url_to_file("https://example.com/model.bin", "/tmp/model") == "https://example.com/model.bin"


def test_apply_from_config_can_disable_registration(tmp_path, monkeypatch):
    write_file(tmp_path / "torch" / "__init__.py", "")
    write_file(
        tmp_path / "torch" / "hub.py",
        """
        def download_url_to_file(url, dst):
            return url
        """,
    )
    sys.path.insert(0, str(tmp_path))
    monkeypatch.setenv("HF_ENDPOINT", "https://hf.example")

    apply_from_config({"enabled": False})
    module = importlib.import_module("torch.hub")

    assert module.download_url_to_file(HF_URL, "/tmp/model") == HF_URL


def test_patch_sd_webui_load_file_from_url_replaces_download_function(tmp_path, monkeypatch):
    write_file(tmp_path / "modules" / "__init__.py", "")
    write_file(
        tmp_path / "modules" / "util.py",
        """
        def load_file_from_url(url, *, model_dir, progress=True, file_name=None, hash_prefix=None, re_download=False):
            return "original"
        """,
    )
    sys.path.insert(0, str(tmp_path))
    monkeypatch.setenv("HF_ENDPOINT", "https://hf.example")
    requests_module, requested_urls = make_fake_requests([b"abc", b"def"])
    monkeypatch.setitem(sys.modules, "requests", requests_module)
    monkeypatch.setitem(sys.modules, "tqdm", make_fake_tqdm())

    patch_sd_webui_load_file_from_url()
    module = importlib.import_module("modules.util")
    result = module.load_file_from_url(
        HF_URL,
        model_dir=str(tmp_path / "models"),
        file_name="model.bin",
        hash_prefix=hashlib.sha256(b"abcdef").hexdigest()[:8],
    )

    assert requested_urls == [MIRROR_URL]
    assert result == str(tmp_path / "models" / "model.bin")
    assert (tmp_path / "models" / "model.bin").read_bytes() == b"abcdef"


def test_sd_webui_load_file_from_url_keeps_original_url_without_endpoint(tmp_path, monkeypatch):
    write_file(tmp_path / "modules" / "__init__.py", "")
    write_file(tmp_path / "modules" / "util.py", "")
    sys.path.insert(0, str(tmp_path))
    requests_module, requested_urls = make_fake_requests([b"data"])
    monkeypatch.setitem(sys.modules, "requests", requests_module)
    monkeypatch.setitem(sys.modules, "tqdm", make_fake_tqdm())

    patch_sd_webui_load_file_from_url()
    module = importlib.import_module("modules.util")
    result = module.load_file_from_url(
        HF_URL,
        model_dir=str(tmp_path / "models"),
        file_name="model.bin",
    )

    assert requested_urls == [HF_URL]
    assert result == str(tmp_path / "models" / "model.bin")


def test_sd_webui_load_file_from_url_uses_cached_file_without_request(tmp_path, monkeypatch):
    write_file(tmp_path / "modules" / "__init__.py", "")
    write_file(tmp_path / "modules" / "util.py", "")
    model_dir = tmp_path / "models"
    model_dir.mkdir()
    (model_dir / "model.bin").write_bytes(b"cached")
    sys.path.insert(0, str(tmp_path))
    requests_module, requested_urls = make_fake_requests([b"data"])
    monkeypatch.setitem(sys.modules, "requests", requests_module)
    monkeypatch.setitem(sys.modules, "tqdm", make_fake_tqdm())

    patch_sd_webui_load_file_from_url()
    module = importlib.import_module("modules.util")
    result = module.load_file_from_url(HF_URL, model_dir=str(model_dir), file_name="model.bin")

    assert requested_urls == []
    assert result == str(model_dir / "model.bin")
    assert (model_dir / "model.bin").read_bytes() == b"cached"


def test_sd_webui_load_file_from_url_removes_temp_on_hash_mismatch(tmp_path, monkeypatch):
    write_file(tmp_path / "modules" / "__init__.py", "")
    write_file(tmp_path / "modules" / "util.py", "")
    sys.path.insert(0, str(tmp_path))
    requests_module, requested_urls = make_fake_requests([b"bad"])
    monkeypatch.setitem(sys.modules, "requests", requests_module)
    monkeypatch.setitem(sys.modules, "tqdm", make_fake_tqdm())

    patch_sd_webui_load_file_from_url()
    module = importlib.import_module("modules.util")
    with pytest.raises(ValueError):
        module.load_file_from_url(
            HF_URL,
            model_dir=str(tmp_path / "models"),
            file_name="model.bin",
            hash_prefix="0000",
        )

    assert requested_urls == [HF_URL]
    assert not (tmp_path / "models" / "model.bin").exists()
    assert not (tmp_path / "models" / "model.bin.tmp").exists()


def make_fake_requests(chunks):
    requested_urls = []

    class FakeResponse:
        headers = {"content-length": str(sum(len(chunk) for chunk in chunks))}

        def raise_for_status(self):
            return None

        def iter_content(self, chunk_size):
            yield from chunks

    def get(url, stream=True):
        requested_urls.append(url)
        return FakeResponse()

    return types.SimpleNamespace(get=get), requested_urls


def make_fake_tqdm():
    class FakeTqdm:
        def __init__(self, *args, **kwargs):
            self.total = kwargs.get("total", 0)
            self.value = 0

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            return None

        def update(self, value):
            self.value += value

    return types.SimpleNamespace(tqdm=FakeTqdm)
