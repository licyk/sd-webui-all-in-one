import hashlib
from pathlib import Path


def compare_sha256(
    file_path: str | Path,
    hash_prefix: str,
) -> bool:
    """检查文件的 sha256 哈希值是否与给定的前缀匹配

    Args:
        file_path (str | Path): 文件路径
        hash_prefix (str): 哈希前缀
    Returns:
        bool: 匹配结果
    """
    hash_sha256 = hashlib.sha256()
    blksize = 1024 * 1024

    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(blksize), b""):
            hash_sha256.update(chunk)
    return hash_sha256.hexdigest().startswith(hash_prefix.strip().lower())
