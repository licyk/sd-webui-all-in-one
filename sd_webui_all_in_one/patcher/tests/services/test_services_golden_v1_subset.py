"""Hotpatcher 服务默认配置与能力目录的 v1 golden 子集测试

``golden/*_v1.json`` 是 P0 冻结的 v1 输出。之后只允许新增 key: v1 中的每个 key 和值都必须在当前输出中存在且相等,
并且 v1 key 的相对顺序保持不变 (GUI 表单按目录顺序生成)。v1 golden 文件不应重新生成。
"""

import json
from pathlib import Path
from typing import Any

import pytest

from sd_webui_all_in_one_hotpatcher import monkey_zoo
from sd_webui_all_in_one_hotpatcher.services import get_catalog, get_default_config
from sd_webui_all_in_one_hotpatcher.state import HotpatcherState

GOLDEN_DIR = Path(__file__).resolve().parent / "golden"
VOLATILE_FEATURE_KEYS = ("active", "registered")


@pytest.fixture(autouse=True)
def clean_monkey_zoo():
    monkey_zoo.clear()
    yield
    monkey_zoo.clear()


def _load(name: str) -> Any:
    return json.loads((GOLDEN_DIR / name).read_text(encoding="utf-8"))


def _assert_deep_subset(expected: Any, actual: Any, path: str = "$") -> None:
    if isinstance(expected, dict):
        assert isinstance(actual, dict), f"{path}: expected object, got {type(actual).__name__}"
        missing = [key for key in expected if key not in actual]
        assert not missing, f"{path}: keys removed {missing}"
        order = [key for key in actual if key in expected]
        assert order == list(expected), f"{path}: v1 key order changed: {order} != {list(expected)}"
        for key, value in expected.items():
            _assert_deep_subset(value, actual[key], f"{path}.{key}")
        return
    assert actual == expected, f"{path}: {actual!r} != {expected!r}"


def _static_catalog() -> dict[str, Any]:
    features = get_catalog(state=HotpatcherState())["features"]
    for feature in features.values():
        for key in VOLATILE_FEATURE_KEYS:
            feature.pop(key, None)
    return {"features": features}


def test_default_config_is_additive_over_v1_golden():
    _assert_deep_subset(_load("default_config_v1.json"), get_default_config())


def test_catalog_static_parts_are_additive_over_v1_golden():
    _assert_deep_subset(_load("catalog_static_v1.json"), _static_catalog())


def test_current_golden_is_additive_over_v1_golden():
    _assert_deep_subset(_load("default_config_v1.json"), _load("default_config.json"))
    _assert_deep_subset(_load("catalog_static_v1.json"), _load("catalog_static.json"))


def test_deep_subset_rejects_changed_and_removed_values():
    with pytest.raises(AssertionError):
        _assert_deep_subset({"a": {"b": 1}}, {"a": {"b": 2}})
    with pytest.raises(AssertionError):
        _assert_deep_subset({"a": {"b": 1, "c": 2}}, {"a": {"b": 1}})
    with pytest.raises(AssertionError):
        _assert_deep_subset({"a": 1, "b": 2}, {"b": 2, "a": 1})
    with pytest.raises(AssertionError):
        _assert_deep_subset({"a": [1, 2]}, {"a": [1, 2, 3]})
    _assert_deep_subset({"a": {"b": 1}}, {"a": {"b": 1, "new": True}, "added": {}})
