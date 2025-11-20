"""配置管理"""

import os
import logging

LOGGER_NAME = os.getenv("SD_WEBUI_ALL_IN_ONE_LOGGER_NAME", "SD WebUI All In One")
"""日志器名字"""

LOGGER_LEVEL = int(os.getenv("SD_WEBUI_ALL_IN_ONE_LOGGER_LEVEL", str(logging.INFO)))
"""日志等级"""

LOGGER_COLOR = os.getenv("SD_WEBUI_ALL_IN_ONE_LOGGER_COLOR") not in ["0", "False", "false", "None", "none", "null"]
"""日志颜色"""
