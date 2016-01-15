from skymodman import skylog
from .notifier import Notifier

def withlogger(cls):
    """Class decorator to add a logger to the class"""
    orig_init = cls.__init__

    def __init__(self, *args, **kwargs):
        name = '.'.join([cls.__module__, cls.__name__])

        self._logger = skylog.newLogger(name)
        orig_init(self, *args, **kwargs)

    def logger(self):
        return self._logger
    logger = property(logger)

    setattr(cls, '__init__', __init__)
    setattr(cls, 'logger', logger)
    setattr(cls, 'LOGGER', logger)

    return cls

def counter():
    count=0
    def inc():
        nonlocal count
        count+=1
        return count
    return inc


from os.path import exists, expanduser
def checkPath(path, exp_user=False):
    """
    Verifies that path is not None or an empty string, then returns whether
    the path exists on the filesystem.

    :param str path:
    :param exp_user: expand ~ in path string
    :return:
    """
    if exp_user:
        return path and exists(expanduser(path))
    return path and exists(path)
