from functools import wraps

from sd_webui_all_in_one_hotpatcher import install_import_hook, monkey_zoo

install_import_hook()

with monkey_zoo("examples.target_module") as monkey:

    def patch_greet(func, module):
        """
        构造 greet 函数补丁

        Args:
            func (Callable[..., Any]):
                原始 greet 函数
            module (ModuleType):
                目标模块对象

        Returns:
            Callable[..., Any]:
                替换后的 greet 函数
        """

        @wraps(func)
        def wrapper(name):
            return func(name).upper()

        return wrapper

    monkey.patch_function("greet", patch_greet)

from examples import target_module

print(target_module.greet("world"))
