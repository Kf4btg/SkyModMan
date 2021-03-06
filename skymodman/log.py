import logging
from logging import handlers, config
from queue import Queue

import sys

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

    # rename the log levels with COLORFUL versions of themselves
    # because COLORS.
    logging.addLevelName(50, "\033[1;31mCRITICAL\033[0m")
    logging.addLevelName(40, "\033[0;31mERROR   \033[0m")
    logging.addLevelName(30, "\033[0;33mWARNING \033[0m")
    logging.addLevelName(20, "\033[0;37mINFO    \033[0m")
    logging.addLevelName(10, "\033[0;34mDEBUG   \033[0m")


    q = Queue()

    console_handler = logging.StreamHandler()
    # includes terminfo color codes for easier visual grepping
    detailed_formatter = logging.Formatter('{levelname}[{asctime}.{msecs:03.0f}] line \033[1m{lineno:4d}\033[0m in \033[1;30m{funcName:40}\033[0m: \033[0;37m{message}\033[0m', datefmt='%H:%M:%S', style='{')
    # detailed_formatter = logging.Formatter('%(asctime)s %(name)-15s %(levelname)-8s %(message)s')
    # plain_formatter = logging.Formatter('%(asctime)s %(message)s')

    console_handler.setFormatter(detailed_formatter)
    # console_handler.setFormatter(plain_formatter)

    q_listener = handlers.QueueListener(q, console_handler)


    __logging_queue = q
    __listener = q_listener

    q_listener.start()

# def newLogger(name, configuration=None, level="DEBUG"):
def newLogger(name, configuration=None, level=10):
    """
    Create and return a new logger connected to the main logging queue.

    :param name: Name (preferably of the calling module) that will show in the log records
    :param configuration: a dict configuration for the logger, or None to use the basic config
    :param level: log message level; default is 10 (DEBUG)
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
        # logger.setLevel(level.upper())
        logger.setLevel(level)
    except ValueError:
        pass # let it default to warning

    # check for handlers, or we could get one logger spitting out
    # dozens of duplicate messages everytime it's called
    if not logger.hasHandlers():
        logger.addHandler(q_handler)

    return logger


old_factory = logging.getLogRecordFactory()
def recordFactory(name, level, fn, lno, msg, args, exc_info, func=None, sinfo=None, **kwargs):
    """
    intercept log record creation to clean up output a bit, as well as to correct the information the << overload was giving us (it was reporting module name and line numbers as coming from the skylog module, rather than from where the debug call originated)
    """
    _name=name.split(".")[-1]
    if func and not func=="__lshift":
        func = _name + "." + func
        return old_factory(name, level, fn, lno, msg, args, exc_info, func, sinfo, **kwargs)

    ## get info for actual calling function
    ## (value of 5 determined by trial and error)
    f = sys._getframe(5)
    # pathname = f.f_code.co_filename
    # lineno = f.f_lineno
    funcName=_name + "." + f.f_code.co_name

    return old_factory(name, level, f.f_code.co_filename, f.f_lineno, msg, args, exc_info, funcName, sinfo, **kwargs)

logging.setLogRecordFactory(recordFactory)

def __lshift(caller, value):
    """
    Overload the << op to allow a shortcut to debug() calls:

    logger << "Here's your problem: " + str(thisiswrong)

    ==

    logger.debug("Here's your problem: {}".format(thisiswrong))

    :param value: the message to send
    """
    caller.debug(value)

    return caller

# holy ... it took forever, but I finally figured out you have to set the
# attribute on the class, not the instance...which I guess makes sense, in hindsight
setattr(logging.Logger , "__lshift__", __lshift)  # add << overload


def start_listener():
    __listener.start()

def stop_listener():
    __listener.stop()


def withlogger(cls):
    """Class decorator to add a logger to the class"""
    orig_init = cls.__init__

    def __init__(self, *args, **kwargs):
        name = '.'.join([cls.__module__, cls.__name__])

        self._logger = newLogger(name)
        orig_init(self, *args, **kwargs)

    def logger(self):
        return self._logger
    logger = property(logger)

    setattr(cls, '__init__', __init__)
    setattr(cls, 'logger', logger)
    setattr(cls, 'LOGGER', logger)

    return cls

