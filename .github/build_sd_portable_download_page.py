import os
import re
from collections import namedtuple
from typing import Union, Literal
from pathlib import Path
from datetime import datetime, timezone, timedelta
from modelscope.hub.api import HubApi, DEFAULT_DATASET_REVISION
from modelscope.hub.snapshot_download import fetch_repo_files


# 解析整合包文件名的正则表达式
PORTABLE_NAME_PATTERN = r'''
    ^
    (?P<software>[\w_]+?)       # 软件名 (允许下划线)
    -                           
    (?P<signature>[a-z0-9]+)    # 署名 (小写字母 + 数字)
    -                           
    (?:
        # 每日构建模式：日期 + nightly
        (?P<build_date>\d{8})   # 构建日期 (YYYYMMDD)
        -
        nightly                 
    |
        # 正式版本模式：v + 版本号
        v
        (?P<version>[\d.]+)     # 版本号 (数字和点)
    )
    \.
    (?P<extension>[a-z0-9]+(?:\.[a-z0-9]+)?)  # 扩展名 (支持多级扩展)
    $
'''


# 编译正则表达式 (忽略大小写, 详细模式)
portable_name_parse_regex = re.compile(
    PORTABLE_NAME_PATTERN,
    re.VERBOSE | re.IGNORECASE
)

# 定义文件名组件的命名元组
PortableNameComponent = namedtuple(
    'PortableNameComponent', [
        'software',     # 软件名称
        'signature',    # 署名标记
        'build_type',   # 构建类型 (nightly/stable)
        'build_date',   # 构建日期 (仅 nightly 有效)
        'version',      # 版本号 (仅 stable 有效)
        'extension'     # 文件扩展名
    ]
)


def parse_portable_filename(filename: str) -> PortableNameComponent:
    """
    解析文件名并返回结构化数据

    :param filename: 要解析的文件名
    :return: PortableNameComponent 命名元组
    :raises ValueError: 当文件名不符合模式时
    """
    match = portable_name_parse_regex.match(filename)
    if not match:
        raise ValueError(f"Invalid filename format: {filename}")

    groups = match.groupdict()

    # 确定构建类型并提取相应字段
    if groups['build_date']:
        build_type = 'nightly'
        build_date = groups['build_date']
        version = None
    else:
        build_type = 'stable'
        build_date = None
        version = groups['version']

    return PortableNameComponent(
        software=groups['software'],
        signature=groups['signature'],
        build_type=build_type,
        build_date=build_date,
        version=version,
        extension=groups['extension'].lower()
    )


def get_modelscope_repo_file(
    repo_id: str,
    repo_type: Literal["model", "dataset", "space"],
) -> list[str, str]:
    '''从 ModelScope 仓库获取文件列表

    :param repo_id`(str)`: 仓库 ID
    :param repo_type`(str)`: 仓库种类 (model/dataset/space)
    :return `list[str,str]`: 仓库文件列表 `[<路径>, <链接>]`
    '''
    api = HubApi()
    file_list = []
    file_list_url = []

    def _get_file_path(repo_files: list) -> list:
        file_list = []
        for file in repo_files:
            if file["Type"] != "tree":
                file_list.append(file["Path"])
        return file_list

    if repo_type == "model":
        try:
            print(f"获取 {repo_id} (类型: {repo_type}) 中的文件列表")
            repo_files = api.get_model_files(model_id=repo_id, recursive=True)
            file_list = _get_file_path(repo_files)
        except Exception as e:
            print(f"获取 {repo_id} (类型: {repo_type}) 仓库的文件列表出现错误: {e}")
    elif repo_type == "dataset":
        user = repo_id.split("/")[0]
        name = repo_id.split("/")[1]
        try:
            print(f"获取 {repo_id} (类型: {repo_type}) 中的文件列表")
            repo_files = fetch_repo_files(
                _api=api,
                group_or_owner=user,
                name=name,
                revision=DEFAULT_DATASET_REVISION,
                endpoint=api.endpoint
            )
            file_list = _get_file_path(repo_files)
        except Exception as e:
            print(f"获取 {repo_id} (类型: {repo_type}) 仓库的文件列表出现错误: {e}")
    elif repo_type == "space":
        # TODO: 支持创空间
        print(f"{repo_id} 仓库类型为创空间, 不支持获取文件列表")
        return file_list_url
    else:
        raise Exception(f"未知的 {repo_type} 仓库类型")

    for i in file_list:
        if repo_type == "model":
            url = f"https://modelscope.cn/models/{repo_id}/resolve/master/{i}"
        elif repo_type == "dataset":
            url = f"https://modelscope.cn/datasets/{repo_id}/resolve/master/{i}"
        elif repo_type == "space":
            url = f"https://modelscope.cn/studio/{repo_id}/resolve/master/{i}"
        else:
            raise Exception(f"错误的 HuggingFace 仓库类型: {repo_type}")

        file_list_url.append([i, url])

    return file_list_url


def build_download_page_list(package_list: list[str, str, str]) -> list[str]:
    '''构建下载页面

    :param package_list`(list[str,str,str])`: 整合包列表 `[<整合包名>, <路径>, <链接>]`
    :return `list[str]`: HTML 页面内容
    '''
    html_string = []
    p_type_list = list(set([x for x, _, _ in package_list]))
    p_type_list.sort()

    html_string.append("<ul>")

    for p_type in p_type_list:
        html_string.append(f"<li>{replace_package_name(p_type)}</li>")
        for origin_p_type, p_path, url in package_list:
            if origin_p_type != p_type:
                continue

            html_string.append("<ul>")
            filename = os.path.basename(p_path)
            tmp = f"""
    <li><a href="{url}">
    {filename}
    </a></li>
            """
            html_string.append(tmp)
            html_string.append("</ul>")
    html_string.append("</ul>")

    return html_string


def write_content_to_file(content: list, path: Union[str, Path]) -> None:
    '''将列表写入文件中

    :param content`(list)`: 列表内容
    :param path`(Union[str,Path])`: 保存路径
    '''
    if len(content) == 0:
        return

    dir_path = os.path.dirname(path)
    if not os.path.exists(dir_path):
        os.makedirs(dir_path, exist_ok=True)

    print(f"写入文件到 {path}")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf8") as f:
        for item in content:
            f.write(item + "\n")


def filter_portable_file(file_list: list[str, str]) -> list[str, str]:
    '''从仓库列表中筛选出整合包列表

    :param file_list`(list[str,str])`: 仓库文件列表 `[<路径>, <链接>]`
    :return `(list[str,str])`: 整合包文件列表 `[<路径>, <链接>]`
    '''
    fitter_file_list = []
    for file, url in file_list:
        filename = os.path.basename(file)
        if file.startswith("portable/"):
            try:
                _ = parse_portable_filename(filename)
                fitter_file_list.append([file, url])
            except Exception as e:
                print(f"{file} 文件名不符合规范: {e}")

    return fitter_file_list


def classify_package(
    package_list: list[str, str]
) -> tuple[list[str, str, str], list[str, str, str]]:
    '''分类整合包列表

    :param package_list`(list[str,str])`: 整合包列表 `[<路径>, <链接>]`
    :return `tuple[list[str,str,str],list[str,str,str]]`: 整合包列表

    整合包列表为 `[<稳定版整合包名>, <路径>, <链接>], [<每日构建版整合包名>, <路径>, <链接>]`
    '''
    portable_type = set()
    stable_portable = []
    nightly_portable = []

    # 提取所有整合包的名字
    for file, _ in package_list:
        filename = os.path.basename(file)
        portable_type.add(parse_portable_filename(filename).software)

    portable_type = sorted(list(portable_type))

    # 根据整合包名字分组
    for p_type in portable_type:
        tmp = []

        # 筛选出同一个类型的整合包
        for file, url in package_list:
            filename = os.path.basename(file)
            portable = parse_portable_filename(filename)
            if portable.software == p_type:
                tmp.append([file, url])

        # 分出 stable 版
        for file, url in tmp:
            filename = os.path.basename(file)
            portable = parse_portable_filename(filename)
            if portable.build_type == "stable":
                stable_portable.append([p_type, file, url])

        # 分出 nightly 版
        for file, url in tmp:
            filename = os.path.basename(file)
            portable = parse_portable_filename(filename)
            if portable.build_type == "nightly":
                nightly_portable.append([p_type, file, url])

    return stable_portable, nightly_portable


def replace_package_name(name: str) -> str:
    '''替换原有整合包名

    :param name`(str)`: 整合包名
    :return `str`: 替换后的整合包名
    '''
    if name == "sd_webui":
        return "Stable Diffusion WebUI"

    if name == "sd_webui_forge":
        return "Stable Diffusion WebUI Forge"

    if name == "sd_webui_reforge":
        return "Stable Diffusion WebUI reForge"

    if name == "sd_webui_forge_classic":
        return "Stable Diffusion WebUI Forge Classic"

    if name == "sd_next":
        return "SD Next"

    if name == "comfyui":
        return "ComfyUI"

    if name == "fooocus":
        return "Fooocus"

    if name == "invokeai":
        return "InvokeAI"

    if name == "sd_trainer":
        return "SD Trainer"

    if name == "kohya_gui":
        return "Kohya GUI"

    if name == "sd_scripts":
        return "SD Scripts"

    if name == "musubi_tuner":
        return "Musubi Tuner"

    return name


def main() -> None:
    '''主函数'''
    root_path = os.environ.get("ROOT_PATH")
    repo_id = os.environ.get("REPO_ID")
    repo_type = os.environ.get("REPO_TYPE")
    ms_file = get_modelscope_repo_file(repo_id=repo_id, repo_type=repo_type)
    ms_file = filter_portable_file(ms_file)
    stable, nightly = classify_package(ms_file)
    html_string_stable = build_download_page_list(stable)
    html_string_nightly = build_download_page_list(nightly)

    current_time = (
        datetime.now(timezone.utc) + timedelta(hours=8)
    ).strftime(r"%Y-%m-%d %H:%M:%S")

    content_s = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link rel="shortcut icon" href="../favicon.ico" type="image/x-icon">
    <style>
        body {
            line-height: 1.5;
        }
    </style>
    <title>AI 绘画 / 训练整合包列表</title>
</head>
<body>
    <h1>AI 绘画 / 训练整合包列表</h1>
    基于 <a href="https://github.com/licyk/sd-webui-all-in-one?tab=readme-ov-file#installer">sd-webui-all-in-one/Installer</a> 全自动构建整合包
    <br>
    项目地址：<a href="https://github.com/licyk/sd-webui-all-in-one">https://github.com/licyk/sd-webui-all-in-one</a>
    <br>
    原仓库：<a href="https://huggingface.co/licyk/sdnote/tree/main/portable">HuggingFace</a> / <a href="https://modelscope.cn/models/licyks/sdnote/files">ModelScope</a>
    <br>
    <br>
    Stable 列表为稳定版本, Nightly 为测试版本, 根据需求自行下载
    <br>
    若整合包无法解压，请下载并安装 <a href="https://7-zip.org/">7-Zip</a> 后再尝试解压
    <br>
    整合包说明可阅读：<a href="https://github.com/licyk/sd-webui-all-in-one/discussions/1">AI 绘画 / 训练整合包 · licyk/sd-webui-all-in-one · Discussion #1</a>
    <br>
    <br>
    """ + f"""
    列表更新时间：{current_time}
    <br>
    ===================================================
    <h2>下载列表</h2>
    """

    content_e = """
</body>
</html>
    """

    package_list_html = (
        content_s.strip().split("\n")
        + ["<h3>Stable</h3>"]
        + html_string_stable
        + ["<h3>Nightly</h3>"]
        + html_string_nightly
        + content_e.strip().split("\n")
    )

    write_content_to_file(
        package_list_html, os.path.join(root_path, "index.html"))


if __name__ == "__main__":
    main()
