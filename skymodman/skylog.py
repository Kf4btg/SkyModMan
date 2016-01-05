import logging.config
import logging.handlers
import logging as Logging
from queue import Queue


__logging_queue = None # type: Queue
__listener = None # type: logging.handlers.QueueListener

# __detailed_format = logging.Formatter('%(asctime)s %(name)-15s %(levelname)-8s %(processName)-10s %(message)s')

def base_config(name) -> dict:
    return {
        "version": 1,
        "formatters": {
            "detailed": {
                "class": "logging.Formatter",
                "format": '%(asctime)s %(name)-15s %(levelname)-8s %(processName)-10s %(message)s'
            }
        },
        name: {
            'level': 'DEBUG',
        }
    }

def setupLogListener():
    global __logging_queue
    global __listener

    q = Queue()

    console_handler = Logging.StreamHandler()
    detailed_formatter = Logging.Formatter('%(asctime)s %(name)-15s %(levelname)-8s %(message)s')

    console_handler.setFormatter(detailed_formatter)

    q_listener = logging.handlers.QueueListener(q, console_handler)


    __logging_queue = q
    __listener = q_listener

    q_listener.start()

def newLogger(name, config=None, level:str = "DEBUG"):
    """
    Create and return a new logger connected to the main logging queue.
    :param level: log message level
    :param name: Name (preferably of the calling module) that will show in the log records
    :param config: a dict configuration for the logger, or None to use the basic config
    :return: logger object
    """

    if __listener is None:
        setupLogListener()

    if config is not None:
        # logging.config.dictConfig(base_config(name))
        logging.config.dictConfig(config)
    # else:

    q_handler = logging.handlers.QueueHandler(__logging_queue)
    logger = Logging.getLogger(name)

    try:
        logger.setLevel(level.upper())
    except ValueError:
        pass # let it default to warning

    logger.addHandler(q_handler)

    return logger

def start_listener():
    __listener.start()

def stop_listener():
    __listener.stop()

