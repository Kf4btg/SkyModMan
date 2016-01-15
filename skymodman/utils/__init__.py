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


from os.path import exists as _exists, expanduser as _expand
def checkPath(path, exp_user=False):
    """
    Verifies that path is not None or an empty string, then returns whether
    the path exists on the filesystem.

    :param str path:
    :param exp_user: expand ~ in path string
    :return:
    """
    if exp_user:
        return path and _exists(_expand(path))
    return path and _exists(path)

from itertools import chain as _chain, combinations as _combos
def allcombos(iterable):
    """Returns iterator that yields tuples of all possible non-empty combinations of the elements of the iterable, disregarding order

    >>> allcombos([a,b,c]) = (a,) (b,) (c,) (a,b) (a,c) (b,c) (a,b,c)
    """
    yield from _chain.from_iterable(_combos(iterable, r) for r in range(1,len(iterable)+1))

from functools import reduce as _reduce
def reduceall(binfunc, list_of_lists):
    """ Read 'list of lists' as 'an iterable containing an arbitrary number of other iterables'.
    Returns an iterator that yields, for each list in the listoflists, the result of applying the given binary operation cumulatively to each element of that list. It does this by repeatedly using functools.reduce()

    Example:
        ``reduceall(operator.mul, [(1,2), (2,3,4), (3,4,5,6)]) ==> [2, 24, 360]``

    :param list_of_lists:
    :return:
    """
    yield from map(lambda r: _reduce(binfunc, r), list_of_lists)
