import logging

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO,
                    datefmt='%Y-%m-%d %H:%M:%S',
                    format='[%(asctime)s] %(module)s:%(lineno)d %(levelname)s - %(message)s',
                    handlers=[logging.StreamHandler()])
logging.getLogger("tinkoff.invest").setLevel(logging.WARNING)


def get_logger():
    return logging.getLogger(__name__)
