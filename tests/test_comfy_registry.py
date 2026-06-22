import zipfile
import urllib.error
import urllib.parse

import pytest

from sd_webui_all_in_one.base_manager import comfy_registry


def _make_node_zip(path, version="1.2.3"):
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr(
            "pyproject.toml",
            "\n".join(
                [
                    "[project]",
                    'name = "demo-node"',
                    f'version = "{version}"',
                    "[project.urls]",
                    'Repository = "https://github.com/example/demo-node"',
                ]
            ),
        )
        archive.writestr("node.py", "pass\n")


def test_comfy_registry_install_writes_tracking_and_reads_local_info(monkeypatch, tmp_path):
    archive_path = tmp_path / "node.zip"
    _make_node_zip(archive_path)

    monkeypatch.setattr(
        comfy_registry,
        "fetch_comfy_registry_install_info",
        lambda node_id, version=None: comfy_registry.ComfyRegistryNodeVersion(
            node_id=node_id,
            version=version or "1.2.3",
            download_url="https://cdn.example/node.zip",
        ),
    )
    monkeypatch.setattr(comfy_registry, "download_file", lambda **_kwargs: archive_path)

    info = comfy_registry.install_comfy_registry_node(tmp_path, "demo-node", run_postinstall=False)

    install_path = tmp_path / "custom_nodes" / "demo-node"
    assert info.version == "1.2.3"
    assert (install_path / "node.py").is_file()
    assert (install_path / ".tracking").read_text(encoding="utf-8").splitlines() == ["pyproject.toml", "node.py"]

    local = comfy_registry.read_comfy_registry_info(install_path)
    assert local is not None
    assert local.registry_id == "demo-node"
    assert local.version == "1.2.3"
    assert local.repository == "https://github.com/example/demo-node"


def test_comfy_registry_switch_version_preserves_untracked_files(monkeypatch, tmp_path):
    old_archive = tmp_path / "old.zip"
    new_archive = tmp_path / "new.zip"
    _make_node_zip(old_archive, version="1.0.0")
    _make_node_zip(new_archive, version="2.0.0")
    downloads = [old_archive, new_archive]

    monkeypatch.setattr(
        comfy_registry,
        "fetch_comfy_registry_install_info",
        lambda node_id, version=None: comfy_registry.ComfyRegistryNodeVersion(
            node_id=node_id,
            version=version or "2.0.0",
            download_url="https://cdn.example/node.zip",
        ),
    )
    monkeypatch.setattr(comfy_registry, "download_file", lambda **_kwargs: downloads.pop(0))

    comfy_registry.install_comfy_registry_node(tmp_path, "demo-node", version="1.0.0", run_postinstall=False)
    install_path = tmp_path / "custom_nodes" / "demo-node"
    (install_path / "user-data.txt").write_text("keep", encoding="utf-8")

    comfy_registry.switch_comfy_registry_node_version(tmp_path, "demo-node", "2.0.0", target_path=install_path, run_postinstall=False)

    assert (install_path / "user-data.txt").read_text(encoding="utf-8") == "keep"
    assert 'version = "2.0.0"' in (install_path / "pyproject.toml").read_text(encoding="utf-8")


def test_fetch_all_comfy_registry_nodes_paginates_and_uses_cache(monkeypatch):
    comfy_registry.clear_comfy_registry_cache()
    calls = []

    def fake_fetch_json(url, timeout=20):
        del timeout
        query = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
        page = int(query["page"][0])
        limit = int(query["limit"][0])
        calls.append((page, limit))
        nodes = [
            {"id": f"node-{index}", "name": f"Node {index}"}
            for index in range((page - 1) * limit, min(page * limit, 5))
        ]
        return {"nodes": nodes, "total": 5}

    monkeypatch.setattr(comfy_registry, "_fetch_json", fake_fetch_json)

    first = comfy_registry.fetch_all_comfy_registry_nodes(page_size=2)
    second = comfy_registry.fetch_all_comfy_registry_nodes(page_size=2)

    assert [node.id for node in first] == ["node-0", "node-1", "node-2", "node-3", "node-4"]
    assert [node.id for node in second] == ["node-0", "node-1", "node-2", "node-3", "node-4"]
    assert calls == [(1, 2), (2, 2), (3, 2)]


def test_fetch_comfy_registry_extension_index_marks_missing_versions(monkeypatch):
    def fake_fetch_all_nodes(
        search=None,
        page_size=500,
        max_items=None,
        timeout=20,
        cache_ttl_seconds=comfy_registry.COMFY_REGISTRY_CACHE_TTL_SECONDS,
        force_refresh=False,
        progress_callback=None,
    ):
        del search, page_size, max_items, timeout, cache_ttl_seconds, force_refresh, progress_callback
        return [
            comfy_registry.ComfyRegistryNode(
                id="installable-node",
                name="Installable Node",
                author="Install Author",
                latest_version=comfy_registry.ComfyRegistryNodeVersion(
                    node_id="installable-node",
                    version="1.0.0",
                    download_url="https://cdn.example/installable.zip",
                ),
            ),
            comfy_registry.ComfyRegistryNode(
                id="metadata-only-node",
                name="Metadata Only Node",
                author="Metadata Author",
                repository="https://github.com/example/metadata-only-node",
            ),
        ]

    monkeypatch.setattr(
        comfy_registry,
        "fetch_all_comfy_registry_nodes",
        fake_fetch_all_nodes,
    )

    items = comfy_registry.fetch_comfy_registry_extension_index()

    assert [(item.registry_id, item.installable, item.install_status) for item in items] == [
        ("installable-node", True, "可安装"),
        ("metadata-only-node", False, comfy_registry.COMFY_REGISTRY_UNAVAILABLE_STATUS),
    ]
    assert [item.author for item in items] == ["Install Author", "Metadata Author"]
    assert items[1].url == "https://github.com/example/metadata-only-node"


def test_fetch_comfy_registry_install_info_404_raises_unavailable(monkeypatch):
    def fail_fetch(url, timeout=20):
        raise urllib.error.HTTPError(url, 404, "Not Found", {}, None)

    monkeypatch.setattr(comfy_registry, "_fetch_json", fail_fetch)

    with pytest.raises(comfy_registry.ComfyRegistryInstallUnavailableError) as exc:
        comfy_registry.fetch_comfy_registry_install_info("ComfyUI_CosyVoice")

    assert exc.value.node_id == "ComfyUI_CosyVoice"
    assert exc.value.version is None
    assert exc.value.http_status == 404
    assert "ComfyUI_CosyVoice@latest" in str(exc.value)
    assert "HTTP 404" in str(exc.value)
    assert "没有可安装 CNR 版本" in str(exc.value)


def test_comfy_registry_install_rejects_install_info_without_download_url(monkeypatch, tmp_path):
    monkeypatch.setattr(
        comfy_registry,
        "fetch_comfy_registry_install_info",
        lambda node_id, version=None: comfy_registry.ComfyRegistryNodeVersion(
            node_id=node_id,
            version=version or "1.0.0",
            download_url="",
        ),
    )

    with pytest.raises(comfy_registry.ComfyRegistryInstallUnavailableError) as exc:
        comfy_registry.install_comfy_registry_node(tmp_path, "metadata-only-node", run_postinstall=False)

    assert exc.value.node_id == "metadata-only-node"
    assert "downloadUrl" in str(exc.value)


def test_parse_comfy_registry_node_author_priority():
    explicit = comfy_registry._parse_node(
        {
            "id": "explicit-node",
            "name": "Explicit Node",
            "author": "node-author",
            "publisher": {"name": "Publisher Name"},
            "repository": "https://github.com/repo-owner/explicit-node",
        }
    )
    publisher = comfy_registry._parse_node(
        {
            "id": "publisher-node",
            "name": "Publisher Node",
            "author": "",
            "publisher": {"name": "Publisher Name"},
            "repository": "https://github.com/repo-owner/publisher-node",
        }
    )
    repository = comfy_registry._parse_node(
        {
            "id": "repository-node",
            "name": "Repository Node",
            "author": "",
            "publisher": {"name": "Unclaimed"},
            "repository": "https://github.com/repo-owner/repository-node",
        }
    )

    assert explicit is not None
    assert publisher is not None
    assert repository is not None
    assert explicit.author == "node-author"
    assert publisher.author == "Publisher Name"
    assert repository.author == "repo-owner"
