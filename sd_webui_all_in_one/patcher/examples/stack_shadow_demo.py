"""栈隐藏 traceback 文件名演示"""

from __future__ import annotations

import importlib
import sys
import tempfile
import traceback
from pathlib import Path

from sd_webui_all_in_one_hotpatcher import install_stack_shadower, uninstall_stack_shadower


def main():
    """运行栈隐藏演示"""

    with tempfile.TemporaryDirectory() as temp_dir:
        module_dir = Path(temp_dir)
        (module_dir / "demo_hidden_module.py").write_text(
            "def boom():\n    raise RuntimeError('hidden path demo')\n",
            encoding="utf-8",
        )
        sys.path.insert(0, str(module_dir))
        try:
            install_stack_shadower("demo_hidden_module", "<hidden {name}>")
            module = importlib.import_module("demo_hidden_module")
            try:
                module.boom()
            except Exception:
                print(traceback.format_exc())
        finally:
            uninstall_stack_shadower()
            sys.path.remove(str(module_dir))
            sys.modules.pop("demo_hidden_module", None)


if __name__ == "__main__":
    main()
