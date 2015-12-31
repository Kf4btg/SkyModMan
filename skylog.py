import logging.config
import logging.handlers
import logging as Logging
from queue import Queue
import threading


# class logHandler:
#     """
#     Handler for delegating logging events in the listener.
#
#     https://gist.github.com/vsajip/2331314
#     """
#     def handle(self, record):
#         logger = logging.getLogger(record.name)
#         logger.handle(record)

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
    # q_handler = logging.handlers.QueueHandler(q)

    console_handler = Logging.StreamHandler()
    detailed_formatter = Logging.Formatter('%(asctime)s %(name)-15s %(levelname)-8s %(message)s')

    console_handler.setFormatter(detailed_formatter)

    q_listener = logging.handlers.QueueListener(q, console_handler)

    # logging.config.dictConfig(d)
    # root = logging.getLogger()
    # root.setLevel('DEBUG')
    # root.addHandler(q_handler)


    # return root, q_listener

    __logging_queue = q
    __listener = q_listener

    q_listener.start()
    # return q_listener

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







# d = {
    #     "version": 1,
    #     "formatters": {
    #         "detailed": {
    #             "class": "logging.Formatter",
    #             "format": '%(asctime)s %(name)-15s %(levelname)-8s %(processName)-10s %(message)s'
    #         }
    #     },
    #     'handlers': {
    #         'console': {
    #             'class': 'logging.StreamHandler',
    #             'level': 'DEBUG',
    #             'formatter': "detailed"
    #         }
    #     },
    #     'root': {
    #         'level': 'DEBUG',
    #         'handlers': ['console']
    #     }
    # }

