import operator

# __all__=['On', 'onCall', 'onContains', 'onEquals', 'switch']

class __SwitchTypeMeta(type):

    def __getattribute__(cls, key):

        # if one of the helper types is called, add it to the list of requested mixins
        if key in ('call', 'contains', 'equals'):
            currmixins = type.__getattribute__(cls, '_type_mixins')

            setattr(cls, '_type_mixins', currmixins | {key})
        return type.__getattribute__(cls, key)





class __on_(metaclass=__SwitchTypeMeta):
    call=... # type: _helper             # to avoid issues with trying to 'forward-declare' classes,
    contains=...    # type: _helper      # we'll add these attrs after the three other classes are createe
    equals=...    # type: __helper

    _type_mixins = set()


def __callOnly(value):
    return onCall(value)


def __containsOnly(value):
    return onContains(value)


def __equalsOnly(value):
    return onEquals(value)


def __call_contains(value):
    def case(match):
        try:
            return match(value)
        except TypeError:
            return value in match

    return [case]


def __contains_equals(value):
    def case(match):
        try:
            return value in match
        except TypeError:
            return value == match

    return [case]


def __call_equals(value):
    def case(match):
        try:
            return match(value)
        except TypeError:
            return value == match

    return [case]


def __call_contains_equals(value):
    def case(match):
        try:
            return match(value)
        except TypeError:
            try:
                return value in match
            except TypeError:
                return value == match

    return [case]


def __helper(value):
    c = frozenset({'call'})
    n = frozenset({'contains'})
    e = frozenset({'equals'})

    types = frozenset(__helper.Or._type_mixins)

    # reset the mixins set
    __helper.Or._type_mixins.clear()

    return {
        c: __callOnly,
        n: __containsOnly,
        e: __equalsOnly,

        c|n: __call_contains,
        c|e: __call_equals,
        n|e: __contains_equals,

        c|n|e: __call_contains_equals

    }[types](value)



# setattr(__helper, 'Or', __on_)

# and now add the attributes
# __on_.contains = __on_.equals = __helper

setattr(__on_, 'call', __helper)
setattr(__on_, 'contains', __helper)
setattr(__on_, 'equals', __helper)



def switch(value, comp=operator.eq):
    """generic version of the switch; pass any comparator function you wish"""
    return [lambda match: comp(match, value)]

def onCall(value):
    """Version that accepts a new comparator callable on each invocation"""
    return [lambda c: __comp_call(c,value)]

def onContains(value):
    """Convenience switch version that accepts containers as parameters and checks for the values membership"""
    return [lambda cont: value in cont]

def onEquals(value):
    """Convenience version of switch that checks for == equality between the value and the comparator object.

    .. note:: This is the same as calling Switch.switch(value), leaving the `comp` argument as default.
    """
    return switch(value)

On = __helper.Or = __on_
  # add the reference

__comp_call=lambda c,v: c(v)
"""Allows passing a different callable-comparator for each case"""

def __test2():
    text3='234'

    s=On.call.Or.equals.Or.contains

    for ccase in s(text3):
        if ccase(lambda v: int(v)==234):
            print ('hello')

        if ccase('234'):
            print('haha')
            break
        if ccase(['234', '123', [342]]):
            print('wellll')
    else:
        print('here we are')


if __name__ == '__main__':
    __test2()
