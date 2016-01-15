import logging
from logging import handlers
from logging import config
from queue import Queue


__logging_queue = None # type: Queue
__listener = None # type: handlers.QueueListener

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

    console_handler = logging.StreamHandler()
    detailed_formatter = logging.Formatter('%(asctime)s %(name)-15s %(levelname)-8s %(message)s')

    console_handler.setFormatter(detailed_formatter)

    q_listener = handlers.QueueListener(q, console_handler)


    __logging_queue = q
    __listener = q_listener

    q_listener.start()

def newLogger(name, configuration=None, level="DEBUG"):
    """
    Create and return a new logger connected to the main logging queue.

    :param name: Name (preferably of the calling module) that will show in the log records
    :param configuration: a dict configuration for the logger, or None to use the basic config
    :param str level: log message level
    :return: logger object
    """

    if __listener is None:
        setupLogListener()

    if configuration is not None:
        # logging.config.dictConfig(base_config(name))
        config.dictConfig(configuration)
    # else:

    q_handler = handlers.QueueHandler(__logging_queue)
    logger = logging.getLogger(name)

    try:
        logger.setLevel(level.upper())
    except ValueError:
        pass # let it default to warning

    logger.addHandler(q_handler)

    return logger




def __lshift(self, value):
    """
    Overload the << op to allow a shortcut to debug() calls:

    logger << "Here's your problem: {}".format(thisiswrong)

    ==

    logger.debug("Here's your problem: {}".format(thisiswrong))

    :param value: the message to send
    """
    # print("thisdsfgsdgdsf")
    self.debug(value)
    return self

# holy ... it took forever, but I finally figured out you have to set the
# attribute on the class, not the instance...which I guess makes sense, in hindsight
setattr(logging.Logger , "__lshift__", __lshift)  # add << overload


def start_listener():
    __listener.start()

def stop_listener():
    __listener.stop()
