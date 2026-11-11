"""Hotpatcher 服务默认配置与能力目录的 golden snapshot 测试

冻结 ``get_default_config()`` 和 ``get_catalog()`` 静态部分 (含 key 顺序), 防止控制面重构改变 GUI 表单与宿主默认值。

重新生成 golden 文件 (仅在有意修改默认配置或 schema 时):

    SD_WEBUI_ALL_IN_ONE_HOTPATCHER_REGEN_GOLDEN=1 python -m pytest sd_webui_all_in_one/patcher/tests/services/test_services_golden_snapshot.py
"""

import json
import os
from pathlib import Path
from typing import Any

import pytest

from sd_webui_all_in_one_hotpatcher import monkey_zoo
from sd_webui_all_in_one_hotpatcher.services import get_catalog, get_default_config
from sd_webui_all_in_one_hotpatcher.state import HotpatcherState

GOLDEN_DIR = Path(__file__).resolve().parent / "golden"
REGEN_ENV = "SD_WEBUI_ALL_IN_ONE_HOTPATCHER_REGEN_GOLDEN"

# 依赖进程状态的 feature 级字段, 不进入 golden
VOLATILE_FEATURE_KEYS = ("active", "registered")


@pytest.fixture(autouse=True)
def clean_monkey_zoo():
    monkey_zoo.clear()
    yield
    monkey_zoo.clear()


def _dump(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2) + "\n"


def _static_catalog() -> dict[str, Any]:
    catalog = get_catalog(state=HotpatcherState())
    assert list(catalog) == ["features", "registered_patches"]
    assert sorted(catalog["registered_patches"]) == ["aliases", "modules"]
    features = catalog["features"]
    for feature in features.values():
        for key in VOLATILE_FEATURE_KEYS:
            feature.pop(key, None)
    return {"features": features}


def _assert_matches_golden(name: str, actual: Any) -> None:
    path = GOLDEN_DIR / name
    text = _dump(actual)
    if os.environ.get(REGEN_ENV) == "1":
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    expected_text = path.read_text(encoding="utf-8")
    # 先比较对象, 失败时 diff 更易读; 再比较序列化文本, 锁定 key 顺序
    assert actual == json.loads(expected_text)
    assert text == expected_text


def test_default_config_matches_golden_snapshot():
    _assert_matches_golden("default_config.json", get_default_config())


def test_catalog_static_parts_match_golden_snapshot():
    _assert_matches_golden("catalog_static.json", _static_catalog())


def test_catalog_volatile_feature_fields_are_booleans():
    features = get_catalog(state=HotpatcherState())["features"]

    for name, feature in features.items():
        assert isinstance(feature["active"], bool), name
    assert [name for name, feature in features.items() if "registered" in feature] == ["runtime.browser"]
    assert isinstance(features["runtime.browser"]["registered"], bool)
