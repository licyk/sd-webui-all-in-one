"""已安装软件包的依赖分类与元数据依赖检查测试"""

import pytest

from sd_webui_all_in_one.package_analyzer import checker
from sd_webui_all_in_one.package_analyzer import dependency_categorizer


def test_dependency_categorizer_formats_and_groups_markers(monkeypatch):
    monkeypatch.setattr(
        dependency_categorizer,
        "requires",
        lambda _name: [
            "core>=1.0",
            "With_Extras[a,b]<2,>=1 ; python_version >= '3'",
            "direct @ https://example.test/direct-1.0.tar.gz",
            "gpu-extra>=2.0 ; extra == 'GPU_Tools' and python_version >= '3'",
            "gpu-skip>=3.0 ; extra == 'gpu-tools' and python_version < '3'",
            "both>=1 ; extra == 'gpu-tools' or extra == 'ui'",
            "skip-me>=1.0 ; python_version < '0'",
            "bad requirement !!!",
        ],
    )

    deps = dependency_categorizer.get_categorized_dependencies("demo")

    assert deps == {
        "mandatory": ["core>=1.0", "With_Extras[a,b]<2,>=1", "direct @ https://example.test/direct-1.0.tar.gz"],
        "optional": {"gpu-tools": ["gpu-extra>=2.0", "both>=1"], "ui": ["both>=1"]},
    }


def test_dependency_categorizer_handles_package_without_requirements(monkeypatch):
    monkeypatch.setattr(dependency_categorizer, "requires", lambda _name: None)

    assert dependency_categorizer.get_categorized_dependencies("demo") == {"mandatory": [], "optional": {}}


def test_metadata_dependency_validation_selects_mandatory_and_optional(monkeypatch):
    deps = {
        "mandatory": ["ok>=1.0", "missing>=2.0"],
        "optional": {
            "gpu": ["gpu-ok", "gpu-missing[accel]>=1.0"],
            "ui": ["ui-ok"],
        },
    }
    checked = []

    monkeypatch.setattr(checker, "get_categorized_dependencies", lambda name: deps if name == "demo" else {"mandatory": [], "optional": {}})

    def fake_is_package_installed(package):
        checked.append(package)
        return package in {"ok>=1.0", "gpu-ok", "ui-ok"}

    monkeypatch.setattr(checker, "is_package_installed", fake_is_package_installed)

    assert checker.get_missing_package_metadata_dependencies("demo") == ["missing>=2.0"]
    assert checked == ["ok>=1.0", "missing>=2.0"]

    checked.clear()
    # extra 名按规范化后的名称匹配
    assert checker.get_missing_package_metadata_dependencies("demo[GPU,ui]") == ["missing>=2.0", "gpu-missing[accel]>=1.0"]
    assert checked == ["ok>=1.0", "missing>=2.0", "gpu-ok", "gpu-missing[accel]>=1.0", "ui-ok"]

    monkeypatch.setattr(checker, "is_package_installed", lambda _package: True)
    assert checker.validate_package_metadata_dependencies("demo[gpu]") is True


def test_metadata_dependency_validation_rejects_unknown_extra_and_invalid_name(monkeypatch):
    monkeypatch.setattr(
        checker,
        "get_categorized_dependencies",
        lambda _name: {"mandatory": [], "optional": {"gpu": ["gpu-ok"]}},
    )

    with pytest.raises(ValueError, match="unknown"):
        checker.get_missing_package_metadata_dependencies("demo[unknown]")
    with pytest.raises(ValueError):
        checker.get_missing_package_metadata_dependencies("  ")
