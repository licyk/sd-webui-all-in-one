import zipfile

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
