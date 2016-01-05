from skymodman import skylog
from collections import namedtuple

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


class Notifier:
    """Creates a callable object that waits to be called `count` number of times, then executes the given `callback` with the given args and kwargs"""

    def __init__(self, count, callback, *cb_args, **cb_kwargs):
        self.count = count
        self.callback = callback
        self.cbargs = cb_args
        self.cbkwargs = cb_kwargs

        self.timer = self.notify_wait(count)

    def __call__(self, who=None):
        """:param who: optional string to provide context about the caller to the user; only used for logging purposes"""
        try:
            # print("--call from {}".format(who))
            next(self.timer)
        except StopIteration:
            # print("--done--")
            self.callback(*self.cbargs, **self.cbkwargs)

    @staticmethod
    def notify_wait(count):
        calls = 1
        while calls < count:
            yield
            calls+=1


ModEntry = namedtuple("ModEntry", ['enabled', 'name', 'id', 'version', 'order'])
