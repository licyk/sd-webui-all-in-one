## 整合包版本说明
- 正式版：`<整合包名>-<署名>-<正式版本号><文件格式>`
- 测试版：`<整合包名>-<署名>-<构建日期>-<每日构建标志><文件格式>`

整合包下载页使用 [build_sd_portable_download_link.py](build_sd_portable_download_link.py)、[build_sd_portable_download_page.py](build_sd_portable_download_page.py) 进行构建。

解析文件名使用以下的代码：

```python
import re
from collections import namedtuple


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
```
