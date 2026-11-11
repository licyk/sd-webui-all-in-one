"""Hotpatcher services 导入不变量测试

``import sd_webui_all_in_one_hotpatcher.services`` 不得加载任何 ``sd_webui_all_in_one_hotpatcher_ext`` 模块。
扩展必须在 ``apply_config`` 安装栈隐藏器之后才首次导入, 并且核心包需要能脱离扩展包单独使用。
"""

import json
import subprocess
import sys
from pathlib import Path

PATCHER_ROOT = Path(__file__).resolve().parents[2]

CHILD_SCRIPT = """
import json
import sys

sys.path.insert(0, sys.argv[1])
import sd_webui_all_in_one_hotpatcher.services  # noqa: F401

print(json.dumps(sorted(sys.modules)))
"""


def test_importing_services_loads_no_extension_modules():
    completed = subprocess.run(
        [sys.executable, "-I", "-B", "-c", CHILD_SCRIPT, str(PATCHER_ROOT)],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    modules = json.loads(completed.stdout.strip().splitlines()[-1])
    assert "sd_webui_all_in_one_hotpatcher.services" in modules
    assert [name for name in modules if name.startswith("sd_webui_all_in_one_hotpatcher_ext")] == []
