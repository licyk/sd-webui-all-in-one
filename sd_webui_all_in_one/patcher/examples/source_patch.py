from sd_webui_all_in_one_hotpatcher import install_import_hook, monkey_zoo

install_import_hook()

with monkey_zoo("examples.target_module") as monkey:

    def replace_label(source, filename):
        """
        替换示例模块源码中的标签常量

        Args:
            source (str):
                原始源码
            filename (str):
                原始文件名

        Returns:
            str:
                替换后的源码
        """

        return source.replace('"original source"', '"patched source"')

    monkey.patch_sources(replace_label)

from examples import target_module

print(target_module.LABEL)
