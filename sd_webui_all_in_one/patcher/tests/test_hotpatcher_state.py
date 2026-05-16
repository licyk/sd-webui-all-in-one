import ast
from pathlib import Path


HOTPATCHER_PACKAGE = Path(__file__).resolve().parents[1] / "sd_webui_all_in_one_hotpatcher"


def test_hotpatcher_core_has_no_global_statements():
    offenders = []
    for path in sorted(HOTPATCHER_PACKAGE.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Global):
                offenders.append(f"{path.relative_to(HOTPATCHER_PACKAGE)}:{node.lineno}:{','.join(node.names)}")

    assert offenders == []
