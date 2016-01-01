import skylog

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

    return cls



