import os
import re
import json
from functools import cmp_to_key
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


# 整合包别名
PROTABLE_ALIAS = {
    "sd_webui": "Stable Diffusion WebUI",
    "sd_webui_forge": "Stable Diffusion WebUI Forge",
    "sd_webui_reforge": "Stable Diffusion WebUI reForge",
    "sd_webui_forge_classic": "Stable Diffusion WebUI Forge Classic",
    "sd_next": "SD Next",
    "comfyui": "ComfyUI",
    "fooocus": "Fooocus",
    "invokeai": "InvokeAI",
    "sd_trainer": "SD Trainer",
    "kohya_gui": "Kohya GUI",
    "sd_scripts": "SD Scripts",
    "musubi_tuner": "Musubi Tuner",
}


def replace_package_name(name: str) -> str:
    '''替换原有整合包名

    :param name`(str)`: 整合包名
    :return `str`: 替换后的整合包名
    '''
    return PROTABLE_ALIAS.get(name, name)


def save_list_to_json(save_path: Path | str, origin_list: list) -> bool:
    """保存列表到 Json 文件中

    :param save_path`(Path,str)`: 保存 Json 文件的路径
    :param origin_list`(list)`: 要保存的列表
    :return `bool`: 当文件保存成功时返回`True`
    """
    dir_path = os.path.dirname(save_path)

    if not os.path.exists(dir_path):
        os.makedirs(dir_path, exist_ok=True)

    try:
        with open(save_path, 'w', encoding='utf-8') as f:
            json.dump(
                origin_list,
                f,
                ensure_ascii=False,
                indent=4,
                separators=(',', ': ')
            )
        print(f"保存 Json 文件到 {save_path}")
        return True
    except Exception as e:
        print(f"保存列表到 {save_path} 时发生错误: {e}")
        return False


def compare_versions(version1: str, version2: str) -> int:
    '''对比两个版本号大小

    :param version1(str): 第一个版本号
    :param version2(str): 第二个版本号
    :return int: 版本对比结果, 1 为第一个版本号大, -1 为第二个版本号大, 0 为两个版本号一样
    '''
    # 将版本号拆分成数字列表
    try:
        nums1 = (
            re.sub(r'[a-zA-Z]+', '', version1)
            .replace('-', '.')
            .replace('_', '.')
            .replace('+', '.')
            .split('.')
        )
        nums2 = (
            re.sub(r'[a-zA-Z]+', '', version2)
            .replace('-', '.')
            .replace('_', '.')
            .replace('+', '.')
            .split('.')
        )
    except Exception as _:
        return 0

    for i in range(max(len(nums1), len(nums2))):
        num1 = int(nums1[i]) if i < len(nums1) else 0  # 如果版本号 1 的位数不够, 则补 0
        num2 = int(nums2[i]) if i < len(nums2) else 0  # 如果版本号 2 的位数不够, 则补 0

        if num1 == num2:
            continue
        elif num1 > num2:
            return 1  # 版本号 1 更大
        else:
            return -1  # 版本号 2 更大

    return 0  # 版本号相同


def sort_portable_impl(item1: list[str, str], item2: list[str, str]) -> int:
    '''整合包列表排序

    :param item1`(list[str,str])`: 第一个整合包列表 `[<文件名>, <下载链接>]`
    :param item2`(list[str,str])`: 第二个整合包列表 `[<文件名>, <下载链接>]`
    :param `int`: 对比结果, 1 为第一个版本号大, -1 为第二个版本号大, 0 为两个版本号一样
    '''
    p1 = parse_portable_filename(item1[0])
    p2 = parse_portable_filename(item2[0])

    if p1.version is not None and p2.version is not None:
        return compare_versions(p1.version, p2.version)

    if p1.build_date is not None and p2.build_date is not None:
        return compare_versions(p1.build_date, p2.build_date)

    return 0


def build_portable_dict(
    stable_list: list[str, str, str],
    nightly_list: list[str, str, str],
) -> dict:
    '''将整合包列表保存为 Json 文件

    :param stable_list`(list[str,str,str])`: 正式版整合包列表 `[<稳定版整合包名>, <文件名>, <链接>]`
    :param nightly_list`(list[str,str,str])`: 每日构建版整合包列表 `[<每日构建版整合包名>, <文件名>, <链接>]`
    :param `dict`: 整合包列表字典
    '''
    stable_p_type = list(set([p_type for p_type, _, _ in stable_list]))
    nightly_p_type = list(set([p_type for p_type, _, _ in nightly_list]))
    stable_p_type.sort()
    nightly_p_type.sort()
    portable_dict = {}
    stable_dict = {}
    nightly_dict = {}

    for p_type in stable_p_type:
        portable_type_list = [
            [os.path.basename(file), url]
            for name, file, url in stable_list
            if name == p_type
        ]
        stable_dict[replace_package_name(p_type)] = sorted(
            portable_type_list, key=cmp_to_key(sort_portable_impl), reverse=True
        )

    portable_dict["stable"] = stable_dict

    for p_type in nightly_p_type:
        portable_type_list = [
            [os.path.basename(file), url]
            for name, file, url in nightly_list
            if name == p_type
        ]
        nightly_dict[replace_package_name(p_type)] = sorted(
            portable_type_list, key=cmp_to_key(sort_portable_impl), reverse=True
        )

    portable_dict["nightly"] = nightly_dict

    current_time = (
        datetime.now(timezone.utc)
        +
        timedelta(hours=8)
    ).strftime(r"%Y-%m-%d %H:%M:%S")
    portable_dict["update_time"] = current_time

    return portable_dict


def main() -> None:
    '''主函数'''
    root_path = os.environ.get("ROOT_PATH")
    repo_id = os.environ.get("REPO_ID")
    repo_type = os.environ.get("REPO_TYPE")
    ms_file = get_modelscope_repo_file(repo_id=repo_id, repo_type=repo_type)
    ms_file = filter_portable_file(ms_file)
    stable, nightly = classify_package(ms_file)
    portable_dict = build_portable_dict(stable, nightly)
    save_list_to_json(os.path.join(
        root_path, "portable_list.json"), portable_dict)


if __name__ == "__main__":
    main()
