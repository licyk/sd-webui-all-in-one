"""运行时加载、修改与卸载补丁模块

运行::

    PYTHONPATH=src python -m examples.runtime_patch_load
"""

import os
from pathlib import Path

from sd_webui_all_in_one_hotpatcher import hotpatch

from examples import target_module

# 在包装之前复制出去的引用指向原函数对象, 不会跟随蹦床; 需要时在 ctx.wrap 中传入 rebind_references=True
from examples.target_module import greet

PATCH_FILE = Path(__file__).resolve().with_name("greeting_patch.py")


def show_target(title):
    """
    打印目标模块的当前行为

    Args:
        title (str):
            标题
    """

    print(f"[{title}]")
    print(f"  target_module.greet('world') = {target_module.greet('world')!r}")
    print(f"  copied greet('world')        = {greet('world')!r}")
    print(f"  target_module.LABEL          = {target_module.LABEL!r}")
    print(f"  EXAMPLE_GREETING_PATCH       = {os.environ.get('EXAMPLE_GREETING_PATCH')!r}")


show_target("before load")

report = hotpatch.load_patch(str(PATCH_FILE), name="greeting", config={"suffix": "!"})
print(f"load: status={report['status']} set_id={report['set_id']} module={report['module']}")
show_target("after load")

listing = hotpatch.patches.list(owner=report["set_id"])
print(f"hotpatch.patches.list: count={listing['count']} truncated={listing['truncated']}")
for item in listing["patches"]:
    print(f"  {item['id']:<10} {item['kind']:<10} {item['status']:<10} {item['target']}")

update = hotpatch.update_patch("greeting", {"suffix": "?"})
print(f"update: status={update['status']} mode={update['mode']}")
show_target("after update")

unload = hotpatch.unload_patch("greeting")
print(f"unload: status={unload['status']} teardown={unload['teardown']}")
for item in unload["handles"]:
    print(f"  {item['id']:<10} {item['kind']:<10} {item['status']}")
show_target("after unload")
