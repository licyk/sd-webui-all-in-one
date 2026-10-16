"""Fooocus 启动参数检查测试"""

import importlib

check_fooocus_args = importlib.import_module("sd_webui_all_in_one.env_check.check_fooocus_args")


def test_check_fooocus_hf_mirror_arg_detects_supported_parser(tmp_path):
    modules = tmp_path / "ldm_patched" / "modules"
    modules.mkdir(parents=True)
    (tmp_path / "ldm_patched" / "__init__.py").write_text("", encoding="utf-8")
    (modules / "__init__.py").write_text("", encoding="utf-8")
    (modules / "args_parser.py").write_text(
        "import argparse\nparser = argparse.ArgumentParser()\nparser.add_argument('--hf-mirror')\n",
        encoding="utf-8",
    )

    assert check_fooocus_args.check_fooocus_hf_mirror_arg(tmp_path, timeout=5) is True


def test_check_fooocus_hf_mirror_arg_rejects_missing_or_unsupported_parser(tmp_path):
    missing = tmp_path / "missing"
    missing.mkdir()
    assert check_fooocus_args.check_fooocus_hf_mirror_arg(missing, timeout=5) is False

    modules = tmp_path / "unsupported" / "ldm_patched" / "modules"
    modules.mkdir(parents=True)
    (tmp_path / "unsupported" / "ldm_patched" / "__init__.py").write_text("", encoding="utf-8")
    (modules / "__init__.py").write_text("", encoding="utf-8")
    (modules / "args_parser.py").write_text(
        "import argparse\nparser = argparse.ArgumentParser()\nparser.add_argument('--listen')\n",
        encoding="utf-8",
    )

    assert check_fooocus_args.check_fooocus_hf_mirror_arg(tmp_path / "unsupported", timeout=5) is False
