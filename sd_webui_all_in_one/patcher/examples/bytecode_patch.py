from sd_webui_all_in_one_hotpatcher import install_import_hook, monkey_zoo

install_import_hook()

with monkey_zoo("examples.target_module") as monkey:

    def replace_constant(code):
        """
        替换示例模块中的字节码常量

        Args:
            code (CodeWrapper):
                目标模块 code object 的可变代理
        """

        code.co_consts.replace_primitive("old bytecode", "patched bytecode")

    monkey.patch_bytecode(replace_constant)

from examples import target_module

print(target_module.BYTECODE_MESSAGE)
