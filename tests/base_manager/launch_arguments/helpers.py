"""启动参数测试辅助工具"""

from __future__ import annotations

HELP_LF = """usage: demo [-h] [--listen [IP]] [--port PORT]
            [--mode {auto,fast}] [--tag TAG [TAG ...]] (--cpu | --cuda)

Network options:
  -h, --help            show this help message and exit
  --listen [IP]         bind address
  --port PORT           server port
  --mode {auto,fast}    preview mode
  --tag TAG [TAG ...]   tags; may be specified multiple times
  --cpu                 use CPU
  --cuda                use CUDA
"""
