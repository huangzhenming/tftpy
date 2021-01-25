import logging
import threading
import yaml
import logging.config
import os

initLock = threading.Lock()
rootLoggerInitialized = False

log_format = "%(asctime)s %(name)s [%(levelname)s] %(message)s"
level = logging.DEBUG
file_log = "pids.log"  # File name
console_log = True

def setup_logging(default_path='logging.yaml', default_level=logging.INFO):
    path = default_path
    if os.path.exists(path):
        with open(path, 'rt') as f:
            config = yaml.safe_load(f.read())
        logging.config.dictConfig(config)
    else:
        logging.basicConfig(level = default_level)

def timer_handler():
    try:
        setup_logging("logging.yaml")
    except Exception as e:
        logging.getLogger().exception(e)
    global timer
    timer = threading.Timer(5, timer_handler)
    timer.start()

def init_handler(handler):
    handler.setFormatter(Formatter(log_format))


def init_logger(logger):
    # logger.setLevel(level)
    # if file_log is not None:
    #     fileHandler = logging.FileHandler(file_log)
    #     init_handler(fileHandler)
    #     logger.addHandler(fileHandler)
    #
    # if console_log:
    #     consoleHandler = logging.StreamHandler()
    #     init_handler(consoleHandler)
    #     logger.addHandler(consoleHandler)
    setup_logging("logging.yaml")


def initialize():
    global rootLoggerInitialized
    with initLock:
        if not rootLoggerInitialized:
            timer_handler()
            init_logger(logging.getLogger())
            rootLoggerInitialized = True


def getLogger(name=None):
    initialize()
    my_logger = logging.getLogger(name)
    return my_logger


# This formatter provides a way to hook in formatTime.
class Formatter(logging.Formatter):
    DATETIME_HOOK = None

    def formatTime(self, record, datefmt=None):
        newDateTime = None

        if Formatter.DATETIME_HOOK is not None:
            newDateTime = Formatter.DATETIME_HOOK()

        if newDateTime is None:
            ret = logging.Formatter.formatTime(self, record, datefmt)
        else:
            ret = str(newDateTime)
        return ret

def main():
    log = getLogger()
    log.info("this is info test")
    log.debug("this is just debug test")
    log.error("this is error test")

if __name__ == '__main__':
    main()
