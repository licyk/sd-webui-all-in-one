"""基于 HF_ENDPOINT 的 Hugging Face URL 重写"""

from __future__ import annotations

import os
import re
from typing import Any
from urllib.parse import urlsplit, urlunsplit

HUGGINGFACE_URL_PATTERN = re.compile(
    r"^https://huggingface\.co(?P<path>/.*)$",
    flags=re.IGNORECASE,
)


def rewrite_huggingface_url(url: Any) -> Any:
    """
    使用 ``HF_ENDPOINT`` 重写 Hugging Face URL

    非字符串、非 Hugging Face URL、或未设置 ``HF_ENDPOINT`` 时原样返回。

    Args:
        url (Any):
            待处理的 URL

    Returns:
        Any:
            重写后的 URL, 或原始输入
    """

    if not isinstance(url, str):
        return url

    endpoint = _hf_endpoint()
    if endpoint is None:
        return url

    parsed = urlsplit(url)
    if parsed.scheme.lower() not in {"http", "https"}:
        return url
    if (parsed.hostname or "").lower() != "huggingface.co":
        return url

    endpoint_parts = urlsplit(endpoint)
    if not endpoint_parts.scheme or not endpoint_parts.netloc:
        return url

    endpoint_path = endpoint_parts.path.rstrip("/")
    path = parsed.path
    combined_path = f"{endpoint_path}{path}" if endpoint_path else path
    return urlunsplit(
        (
            endpoint_parts.scheme,
            endpoint_parts.netloc,
            combined_path,
            parsed.query,
            parsed.fragment,
        )
    )


def _hf_endpoint() -> str | None:
    endpoint = os.getenv("HF_ENDPOINT")
    if endpoint is None:
        return None
    endpoint = endpoint.strip()
    if not endpoint:
        return None
    return endpoint.rstrip("/")
