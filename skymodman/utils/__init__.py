from functools import (singledispatch as _singledispatch,
                       wraps as _wraps)
                       # reduce as _reduce)
# from itertools import (chain as _chain,
#                        combinations as _combos)


from skymodman import skylog as _skylog

from .notifier import Notifier
from .diqt import diqt
from .safewrite import open_for_safe_write


def withlogger(cls):
    """Class decorator to add a logger to the class"""
    orig_init = cls.__init__

    def __init__(self, *args, **kwargs):
        name = '.'.join([cls.__module__, cls.__name__])

        self._logger = _skylog.newLogger(name)
        orig_init(self, *args, **kwargs)

    def logger(self):
        return self._logger
    logger = property(logger)

    setattr(cls, '__init__', __init__)
    setattr(cls, 'logger', logger)
    setattr(cls, 'LOGGER', logger)

    return cls



# FROM:
# http://stackoverflow.com/questions/24601722/how-can-i-use-functools-singledispatch-with-instance-methods
def singledispatch_m(func):
    dispatcher = _singledispatch(func)

    @_wraps(dispatcher)
    def wrapper(*args, **kw):
        return dispatcher.dispatch(
            args[1].__class__)(*args, **kw)
    return wrapper

# class classprop:
#     """
#     Decorator that allows the creation of readonly calculated properties for classes, accessible via ''Class.propname'', just like an instance property. However, only getters are supported, not setters or deleters.
#     """
#
#     def __init__(self, getter=None):
#         self.fget = getter
#
#     # instance will (usually) always be None
#     def __get__(self, instance, cls):
#         return self.fget(cls)


#
# def allcombos(iterable):
#     """Returns iterator that yields tuples of all possible non-empty combinations of the elements of the iterable, disregarding order
#
#     >>> allcombos([a,b,c]) = (a,) (b,) (c,) (a,b) (a,c) (b,c) (a,b,c)
#     """
#     yield from _chain.from_iterable(_combos(iterable, r) for r in range(1,len(iterable)+1))
#
# def reduceall(binfunc, list_of_lists):
#     """ Read 'list of lists' as 'an iterable containing an arbitrary number of other iterables'.
#     Returns an iterator that yields, for each list in the listoflists, the result of applying the given binary operation cumulatively to each element of that list. It does this by repeatedly using functools.reduce()
#
#     Example:
#         ``reduceall(operator.mul, [(1,2), (2,3,4), (3,4,5,6)]) ==> [2, 24, 360]``
#
#     :param list_of_lists:
#     :return:
#     """
#     yield from map(lambda r: _reduce(binfunc, r), list_of_lists)


#
# # variation that allows specifying an arbitrary arg-index
#
# def dispatch_on(argnum=1):
#     def _sdispatch(func):
#         dispatcher = _singledispatch(func)
#         @_wraps(dispatcher)
#         def wrapper(*args, **kw):
#             return dispatcher.dispatch(args[argnum].__class__)(*args, **kw)
#         return wrapper
#     return _sdispatch