from sdaio_utils.logger import get_logger
from sdaio_utils.config import LOGGER_COLOR, LOGGER_LEVEL, LOGGER_NAME

logger = get_logger(
    name=LOGGER_NAME,
    level=LOGGER_LEVEL,
    color=LOGGER_COLOR,
)
