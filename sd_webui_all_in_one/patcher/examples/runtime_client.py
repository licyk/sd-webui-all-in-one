"""
运行时客户端示例

先在另一个终端运行 ``python -m examples.runtime_host``。
"""

from __future__ import annotations

import os
import logging
import subprocess
import sys
import time

from sd_webui_all_in_one_hotpatcher.runtime import (
    FileOperation,
    ManagedBrowser,
    Progress,
    ProgressManager,
    RuntimeClient,
    install_log_capture,
    uninstall_log_capture,
)


def main():
    """运行 runtime client 示例"""

    host = os.getenv("SD_WEBUI_ALL_IN_ONE_HOTPATCHER_HOST", "127.0.0.1")
    port = int(os.getenv("SD_WEBUI_ALL_IN_ONE_HOTPATCHER_PORT", "8765"))

    with RuntimeClient.connect(host, port, token=os.getenv("SD_WEBUI_ALL_IN_ONE_HOTPATCHER_TOKEN", "")) as client:
        install_log_capture(
            client,
            subprocess_mode=os.getenv("SD_WEBUI_ALL_IN_ONE_HOTPATCHER_LOG_SUBPROCESS", "safe"),
            policy=os.getenv("SD_WEBUI_ALL_IN_ONE_HOTPATCHER_LOG_POLICY", "bounded"),
        )

        try:
            print("config:", client.get_config())
            logging.getLogger("runtime-client-demo").warning("logging record from runtime client example")
            sys.stderr.write("stderr text from runtime client example\n")
            subprocess.run(
                [
                    sys.executable,
                    "-c",
                    "print('child stdout'); import sys; print('child stderr', file=sys.stderr)",
                ],
                capture_output=True,
                text=True,
                check=True,
            )

            Progress.manager = ProgressManager(client)
            with Progress("demo task", 3) as progress:
                for i in range(3):
                    progress.value = i + 1
                    progress.right = f"{i + 1}/3"
                    time.sleep(0.1)

            ManagedBrowser(client).open("https://example.com")

            with FileOperation(client) as fileop:
                fileop.delete("/tmp/example-delete-me")
                fileop.perform()
        finally:
            Progress.manager = None
            uninstall_log_capture()


if __name__ == "__main__":
    main()
