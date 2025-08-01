import os
import re
from collections import namedtuple
from typing import Union, Literal
from pathlib import Path
from modelscope.hub.api import HubApi


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
        try:
            print(f"获取 {repo_id} (类型: {repo_type}) 中的文件列表")
            repo_files = api.get_dataset_files(
                repo_id=repo_id,
                recursive=True
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


def build_download_page(filename: str, url: str) -> str:
    html_string = f"""
<!DOCTYPE html>
<html>

<head>
	<link rel="shortcut icon" href="../../favicon.ico" type="image/x-icon">
	<script language="javascript"> location.replace("{url}") </script>
	<meta name="viewport"
		content="width=device-width,initial-scale=1.0,maximum-scale=1.0,minimum-scale=1.0,user-scalable=no">
	<meta charset="utf-8">
</head>

<title>正在跳转到 {filename} 下载链接中...</title>

<body>
	<p style="font-family:arial;color:black;font-size:30px;"></p>若未自动跳转到下载链接请点击
	<a href="{url}">{filename} 手动下载</a></p>
</body>

</html>
""".strip()

    return html_string


def write_content_to_file(content: list, path: Union[str, Path]) -> None:
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


def split_release_list(file_list: list[str, str]) -> Union[list[str, str], list[str, str]]:
    '''从整合包列表按发行类型 (stable/nightly) 进行分类

    :param file_list`(list[str,str])`: 仓库文件列表 `[<路径>, <链接>]`
    :return `list[str,str],list[str,str]`: stale 类型文件列表和 nightly 类型文件列表
    '''
    stable_list = []
    nightly_list = []
    for file, url in file_list:
        filename = os.path.basename(file)
        portable = parse_portable_filename(filename)
        if portable.build_type == "stable":
            stable_list.append([file, url])

        if portable.build_type == "nightly":
            nightly_list.append([file, url])

    return stable_list, nightly_list


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


def find_latest_package(
    package_list: list[str, str]
) -> tuple[list[str, str, str], list[str, str, str]]:
    '''查找最新版本的整合包

    :param package_list`(list[str,str])`: 整合包列表 `[<路径>, <链接>]`
    :return `tuple[list[str,str,str],list[str,str,str]]`: 最新的整合包列表

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

    # 根据整合包名字分组查找最新的版本
    for p_type in portable_type:
        tmp = []

        # 筛选出同一个类型的整合包
        for file, url in package_list:
            filename = os.path.basename(file)
            portable = parse_portable_filename(filename)
            if portable.software == p_type:
                tmp.append([file, url])

        # 找出版本最高的整合包 (stable)
        max_version = "0.0"
        latest_stable_portable = [p_type, "", ""]
        for file, url in tmp:
            filename = os.path.basename(file)
            portable = parse_portable_filename(filename)
            if portable.version is None:
                continue
            if compare_versions(portable.version, max_version) > 0:
                latest_stable_portable = [p_type, file, url]

        stable_portable.append(latest_stable_portable)

        # 找出版本最高的整合包 (nightly)
        max_version = "00000000"
        latest_nightly_portable = [p_type, "", ""]
        for file, url in tmp:
            filename = os.path.basename(file)
            portable = parse_portable_filename(filename)
            if portable.build_date is None:
                continue
            if compare_versions(portable.build_date, max_version) > 0:
                latest_nightly_portable = [p_type, file, url]

        nightly_portable.append(latest_nightly_portable)

    return stable_portable, nightly_portable


def main() -> None:
    '''主函数'''
    root_path = os.environ.get("ROOT_PATH")
    repo_id = os.environ.get("REPO_ID")
    repo_type = os.environ.get("REPO_TYPE")
    ms_file = get_modelscope_repo_file(
        repo_id=repo_id,
        repo_type=repo_type
    )
    ms_file = filter_portable_file(ms_file)
    stable, nightly = find_latest_package(ms_file)

    for portable_type, file_path, url in stable:
        filename = os.path.basename(file_path)
        html_string = [build_download_page(filename, url)]
        write_content_to_file(html_string, os.path.join(
            root_path, "stable", portable_type, "index.html"))

    for portable_type, file_path, url in nightly:
        filename = os.path.basename(file_path)
        html_string = [build_download_page(filename, url)]
        write_content_to_file(html_string, os.path.join(
            root_path, "nightly", portable_type, "index.html"))


if __name__ == "__main__":
    main()
