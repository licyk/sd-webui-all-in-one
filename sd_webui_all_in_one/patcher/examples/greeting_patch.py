"""运行时加载示例使用的补丁模块

由 ``examples.runtime_patch_load`` 通过文件路径加载, 加载后位于私有模块名
``sd_webui_all_in_one_hotpatcher_dynamic.<set_id>`` 下。所有修改都经由 ``ctx`` 记录, 卸载时按 LIFO 撤销。
"""

import os

TARGET = "examples.target_module"


def setup(ctx):
    """
    应用补丁: 包装 greet、修改 LABEL 常量并设置一个环境变量

    Args:
        ctx (PatchContext):
            补丁集上下文, ``ctx.config`` 为加载时传入的配置
    """

    def factory(original):
        def greet(name):
            # 每次调用时读取 ctx.config, 原地 update() 修改配置后立即生效
            return f"{original(name)}{ctx.config.get('suffix', '!')}"

        return greet

    ctx.wrap(f"{TARGET}:greet", factory, trampoline=True)
    ctx.set_attr(f"{TARGET}:LABEL", "patched at runtime")
    ctx.set_env("EXAMPLE_GREETING_PATCH", "1")


def update(ctx, config):
    """
    原地修改补丁配置

    Args:
        ctx (PatchContext):
            补丁集上下文
        config (dict):
            新配置

    Returns:
        bool:
            返回 True 表示已原地生效, 加载器随后把新配置写入 ``ctx.config``
    """

    return isinstance(config.get("suffix"), str)


def teardown(ctx):
    """
    卸载前回调, 在撤销日志之前执行

    Args:
        ctx (PatchContext):
            补丁集上下文
    """

    print(f"teardown: EXAMPLE_GREETING_PATCH={os.environ.get('EXAMPLE_GREETING_PATCH')}")
