"""清理过期整合包

环境变量参数:
- HF_TOKEN: HuggingFace Token
- MODELSCOPE_API_TOKEN: ModelScope Token
- HF_REPO_ID: HuggingFace 仓库 ID
- HF_REPO_TYPE: HuggingFace 仓库类型
- MS_REPO_ID: ModelScope 仓库 ID
- MS_REPO_TYPE: ModelScope 仓库类型
- DAY_THRESHOLD: 整合包过期时间 (天)
"""
import os
import re
import datetime
from typing import Literal
from collections import namedtuple
from huggingface_hub import HfApi, CommitOperationDelete
from modelscope import HubApi


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
        raise ValueError(f"无效文件名格式: {filename}")

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


# HuggingFace 仓库类型
HFRepoType = Literal["model", "dataset", "space"]

# ModelScope 仓库类型
MSRepoType = Literal["model", "dataset", "space"]


def get_repo_file(
    api: HfApi | HubApi,
    repo_id: str,
    repo_type: HFRepoType = "model",
) -> list[str]:
    """获取 HuggingFace / ModelScope 仓库文件列表

    :param api`(HfApi|HubApi)`: HuggingFace / ModelScope Api 实例
    :param repo_id`(str)`: HuggingFace / ModelScope 仓库 ID
    :param repo_type`(str)`: HuggingFace / ModelScope 仓库类型
    :return `list[str]`: 仓库文件列表
    """
    if isinstance(api, HfApi):
        print(f"获取 HuggingFace 仓库 {repo_id} (类型: {repo_type}) 的文件列表")
        return get_hf_repo_files(api, repo_id, repo_type)
    if isinstance(api, HubApi):
        print(f"获取 ModelScope 仓库 {repo_id} (类型: {repo_type}) 的文件列表")
        return get_ms_repo_files(api, repo_id, repo_type)

    print(f"未知 Api 类型: {api}")
    return []


def get_hf_repo_files(
    api: HfApi,
    repo_id: str,
    repo_type: HFRepoType,
) -> list[str]:
    """获取 HuggingFace 仓库文件列表

    :param api`(HfApi)`: HuggingFace Api 实例
    :param repo_id`(str)`: HuggingFace 仓库 ID
    :param repo_type`(str)`: HuggingFace 仓库类型
    :return `list[str]`: 仓库文件列表
    """
    try:
        return api.list_repo_files(
            repo_id=repo_id,
            repo_type=repo_type,
        )
    except (ValueError, ConnectionError, TypeError) as e:
        print(f"获取 {repo_id} (类型: {repo_type}) 仓库的文件列表出现错误: {e}")
        return []


def get_ms_repo_files(
    api: HubApi,
    repo_id: str,
    repo_type: MSRepoType = "model",
) -> list[str]:
    """ 获取 ModelScope 仓库文件列表

    :param api`(HfApi)`: ModelScope Api 实例
    :param repo_id`(str)`: ModelScope 仓库 ID
    :param repo_type`(str)`: ModelScope 仓库类型
    :return `list[str]`: 仓库文件列表
    """
    file_list = []

    def _get_file_path(repo_files: list) -> list[str]:
        """获取 ModelScope Api 返回的仓库列表中的模型路径"""
        return [
            file["Path"]
            for file in repo_files
            if file['Type'] != 'tree'
        ]

    if repo_type == "model":
        try:
            repo_files = api.get_model_files(
                model_id=repo_id,
                recursive=True
            )
            file_list = _get_file_path(repo_files)
        except (ValueError, ConnectionError, TypeError) as e:
            print(f"获取 {repo_id} (类型: {repo_type}) 仓库的文件列表出现错误: {e}")
    elif repo_type == "dataset":
        try:
            repo_files = api.get_dataset_files(
                repo_id=repo_id,
                recursive=True
            )
            file_list = _get_file_path(repo_files)
        except (ValueError, ConnectionError, TypeError) as e:
            print(f"获取 {repo_id} (类型: {repo_type}) 仓库的文件列表出现错误: {e}")
    elif repo_type == "space":
        # TODO: 支持创空间
        print(f"{repo_id} 仓库类型为创空间, 不支持获取文件列表")
    else:
        print(f"未知的 {repo_type} 仓库类型")

    return file_list


def fitter_portable_list(repo_files: list[str]) -> tuple[list[str], list[str]]:
    """从仓库文件中过滤出整合包文件列表

    :param repo_files`(list[str])`: 仓库文件列表
    :return `tuple[(list[str]),list[str]]`: Stable, Nightly 整合包文件列表
    """
    stable = []
    nightly = []
    for file in repo_files:
        if file.startswith("portable/"):
            try:
                portable = parse_portable_filename(os.path.basename(file))
                if portable.build_type == "stable":
                    stable.append(file)
                if portable.build_type == "nightly":
                    nightly.append(file)
            except ValueError as e:
                print(f"{file} 不符合整合包文件名规范: {e}")
    return stable, nightly


def is_outdated_portable(name: str, day_threshold: int) -> bool:
    """判断整合包是否过期

    :param name`(str)`: 整合包名称
    :param day_threshold`(int)`: 整合包发布天数限制
    :return `bool`: 当整合包发布时间超过限制时为过期整合包
    """
    portable = parse_portable_filename(name)
    date = datetime.datetime.strptime(portable.build_date, r"%Y%m%d")
    date_threshold = datetime.datetime.today() - datetime.timedelta(days=day_threshold)
    return date < date_threshold


def get_outdated_portable(file_list: list[str], day_threshold: int = 60) -> list[str]:
    """获取已经过期的整合包列表

    :param file_list`(list[str])`: 整合包列表
    :param `list[str]`: 过期的整合包列表
    """
    outdated_list = []
    print(f"整合包数量: {len(file_list)}")
    for file in file_list:
        name = os.path.basename(file)
        if is_outdated_portable(name, day_threshold):
            outdated_list.append(file)

    print(f"已过期的整合包数量: {len(outdated_list)}")
    return outdated_list


def remove_files_from_hf_repo(
    api: HfApi,
    repo_id: str,
    repo_type: HFRepoType,
    file_list: list[str],
) -> None:
    """从 HuggingFace 仓库中移除文件

    :param api`(HfApi)`: HuggingFace Api 实例
    :param repo_id`(str)`: HuggingFace 仓库 ID
    :param repo_type`(HFRepoType)`: HuggingFace 仓库类型
    :param file_list`(list[str])`: 要从 HuggingFace 仓库移除的文件列表
    """
    if len(file_list) == 0:
        print("要删除的文件列表为空")
        return
    op = [
        CommitOperationDelete(file)
        for file in file_list
    ]
    try:
        api.create_commit(
            repo_id=repo_id,
            repo_type=repo_type,
            operations=op,
            commit_message="Clean outdated sd portable",
        )
        print(
            f"从 HuggingFace 仓库 {repo_id} (类型: {repo_type}) 清理 {len(file_list)} 个过期整合包")
    except (ValueError, ConnectionError, TypeError) as e:
        print(
            f"从 HuggingFace 仓库 {repo_id} (类型: {repo_type}) 清理过期整合包时发送了错误: {e}")


def remove_files_from_ms_repo(
    api: HubApi,
    repo_id: str,
    repo_type: MSRepoType,
    file_list: list[str],
) -> None:
    """从 ModelScope 仓库中移除文件

    :param api`(HfApi)`: ModelScope Api 实例
    :param repo_id`(str)`: ModelScope 仓库 ID
    :param repo_type`(MSRepoType)`: ModelScope 仓库类型
    :param file_list`(list[str])`: 要从 ModelScope 仓库移除的文件列表
    """
    if len(file_list) == 0:
        print("要删除的文件列表为空")
        return
    try:
        api.delete_files(
            repo_id=repo_id,
            repo_type=repo_type,
            delete_patterns=file_list,
        )
        print(
            f"从 ModelScope 仓库 {repo_id} (类型: {repo_type}) 清理 {len(file_list)} 个过期整合包")
    except (ValueError, ConnectionError, TypeError) as e:
        print(
            f"从 ModelScope 仓库 {repo_id} (类型: {repo_type}) 清理过期整合包时发送了错误: {e}")


def main() -> None:
    """主函数"""
    hf_token = os.getenv("HF_TOKEN")
    ms_token = os.getenv("MODELSCOPE_API_TOKEN")
    hf_repo_id = os.getenv("HF_REPO_ID")
    hf_repo_type = os.getenv("HF_REPO_TYPE", "model")
    ms_repo_id = os.getenv("MS_REPO_ID")
    ms_repo_type = os.getenv("MS_REPO_TYPE", "model")
    day_threshold = int(os.getenv("DAY_THRESHOLD", "60"))

    if hf_token and hf_repo_id:
        print(f"清理 HuggingFace 仓库 {hf_repo_id} 中的过期整合包")
        hf_api = HfApi(token=hf_token)
        hf_repo_files = get_repo_file(hf_api, hf_repo_id, hf_repo_type)
        _, hf_nightly_portable = fitter_portable_list(hf_repo_files)
        hf_outdated_portable = get_outdated_portable(
            file_list=hf_nightly_portable,
            day_threshold=day_threshold
        )
        if len(hf_outdated_portable) != 0:
            print(f"HuggingFace 仓库 {hf_repo_id} 中的过期整合包")
            for i in hf_outdated_portable:
                print(f"- {i}")
            remove_files_from_hf_repo(
                api=hf_api,
                repo_id=hf_repo_id,
                repo_type=hf_repo_type,
                file_list=hf_outdated_portable
            )

    if ms_token and ms_repo_id:
        print(f"清理 ModelScope 仓库 {ms_repo_id} 中的过期整合包")
        ms_api = HubApi()
        ms_api.login(access_token=ms_token)
        ms_repo_files = get_repo_file(ms_api, ms_repo_id, ms_repo_type)
        _, ms_nightly_portable = fitter_portable_list(ms_repo_files)
        ms_outdated_portable = get_outdated_portable(
            file_list=ms_nightly_portable,
            day_threshold=day_threshold
        )
        if len(ms_outdated_portable) != 0:
            print(f"ModelScope 仓库 {ms_repo_id} 中的过期整合包")
            for i in ms_outdated_portable:
                print(f"- {i}")
            remove_files_from_ms_repo(
                api=ms_api,
                repo_id=ms_repo_id,
                repo_type=ms_repo_type,
                file_list=ms_outdated_portable
            )

    print("清理过期整合包完成")


if __name__ == "__main__":
    main()
