"""文件哈希值验证工具"""

import hashlib
from pathlib import Path


HASH_ALGORITHM_NAMES = {
    "sha1": "sha1",
    "sha-1": "sha1",
    "sha256": "sha256",
    "sha-256": "sha256",
    "sha512": "sha512",
    "sha-512": "sha512",
}


def normalize_hash_algorithm(algorithm: str) -> str:
    try:
        return HASH_ALGORITHM_NAMES[algorithm.strip().lower()]
    except KeyError as e:
        raise ValueError(f"不支持的哈希算法: {algorithm}") from e


def compare_hash(
    file_path: str | Path,
    expected_hash: str,
    algorithm: str,
) -> bool:
    """检查文件哈希是否匹配给定的十六进制前缀或完整值"""
    normalized_algorithm = normalize_hash_algorithm(algorithm)
    hasher = hashlib.new(normalized_algorithm)
    with open(file_path, "rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest().startswith(expected_hash.strip().lower())


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
    return compare_hash(file_path, hash_prefix, "sha256")
