import typing as T
from abc import ABCMeta, abstractmethod
import collections.abc as abcco
from pprint import pprint

# control variable
CV = T.TypeVar('CV', bound=T.Hashable) # type: T.TypeVar('CV')

# any object that is comparable to the Control Variable
# must also be a hashable object (e.g. no switches on lists, dicts, etc.)
class Equator(metaclass=ABCMeta):
    @abstractmethod
    def __eq__(self, other: CV) -> bool: ...
    @abstractmethod
    def __hash__(self) -> int: ...


# cases can be either callables or anything that compares (== or !=) with the control variable
comparer = T.Callable[[CV], bool]
comparable = T.TypeVar('comparable', bound=Equator) # type: T.TypeVar('comparable')

# The overall sequence is made of single case statements or blocks of fallthrough cases
case = T.Union[comparer, comparable] # type: T.Union[comparer, comparable]
# case_fallthroughs = T.Set[case] # type: T.Set[case]

# we want to be able to iterate over the sequence of cases in the block,
# but we'd also like to keep our selector mapping as small and efficient as possible;
# this means that storing the operation value for each case in the fallthrough
# is not ideal. Preferably we'd query the mapping using the hashed value of the entire block
# (calculated at instantiation), so any case in the block will point to the same key in the mapping.
# Effectively making the selector a many-to-one mapping.

V=T.TypeVar('V')  # generic parameter
class ManyToOne(T.Iterable[V], T.Hashable):
    @abstractmethod
    def __iter__(self) -> T.Iterator[V]: ...
    @abstractmethod
    def __hash__(self) -> int: ...

case_block = T.Union[case, ManyToOne[case]] # type: T.Union[case, ManyToOne[case]]

# operation on satisfied cases
operation = T.Callable[[CV], None]

# the whole sequence
case_sequence = T.Sequence[case_block]

# when a case is satisfied
selector = T.Mapping[case_block, operation]

# and an approzimation of the entire statement
switch=T.Callable[[CV, case_sequence, selector], None] # should it return a value??

from collections import namedtuple

caseop = namedtuple('caseop', 'case operation')

class Switch:
    # def __init__(self, cases, operations, default=None):
    def __init__(self, cases, operations, default=None):

        """

        :param cases: An ordered sequence of checks to be performed against the passed value.  Each check should be a callable that returns a bool, a value that is directly comparable to the variable to be passed, or a sequence of the previous two types. Each sequence of cases will simulate a "fallthrough" section, with the operation of the first matched case being followed by the operations of all the remaining cases in that block.

        :param operations:
            This is another ordered sequence, but this time defines the operations that should be executed when a case statement evaluates to true.  Each operation should directly correspond with a single case in the `cases` argument (with regards to position in their respective sequences), and any fallthrough sequences should have a matching sub-sequence of operations. An 'empty case' operation may be simulated by passing something like ``lambda v: None`` as the operation.
            An 'operation' should be a callable that accepts as a parameter the control variable passed to the switch statement. The called method can then perform whatever operations it wishes, but any value it returns will be ignored.  The ``switch()`` call itself never returns anything, and will end immediately after the execution of the matched operation.

        :param default: An optional operation that will be executed in the event that none of the cases are satisfied. Without the default case, an unmatched switch call will have no effect.

        .. note:: There is currently no support for falling through to the default operation

        """


        self._case_count = len(cases)
        # Validate arguments
        assert self._case_count == len(operations), "There must be one operation for each case or case-block."

        # make sure all the operations are callable
        for o in operations:
            if _isiterable(o):
                for fo in o: assert _iscallable(fo), "Each operation must be callable"
            else: assert _iscallable(o), "Each operation must be callable"

        # make sure the default is callable
        if default is not None:
            assert _iscallable(default), "The default operation must be callable"

        ###########################
        # now create data structures

        # >0 means fallthrough-block; use this value in same way as self._case_count
        self.fallthrough = [len(c) if isinstance(c, list) else 0 for c in cases]

        c_o_list = doubleZipList(cases, operations)

        self._cases = [ [caseop._make(ft) for ft in t] if isinstance(t, list) else caseop._make(t) for t in c_o_list]

        # self._cases = [ [caseop._make(f) for f in zip(*t)] if _isiterable(t[0]) else caseop._make(t) for t in zip(cases, operations)]

        # pprint(self._cases)

        # convert entire case sequence and any contained case-blocks into tuples
        # self._cases = tuple(tuple(cases[i]) if self.fallthrough[i] else cases[i] for i in range(self._case_count))

        # find out whether each case (including the ones in the fallthrough blocks) is a value to be compared
        # to the control variable or a callable to be passed the variable. This gets us a mixed array of values
        # and arrays of values, eg:  [True, False, [True, True, False], True, [False, False]]
        self._case_func = [[_iscallable(f) for f in c] if isinstance(c, list) else _iscallable(c) for c in cases]

        # our selector will just be the corresponding index in the cases tuple
        # self._operations = tuple(operations)
        # self._operations = \
        #     tuple(tuple(operations[i]) if self.fallthrough[i] else operations[i] for i in range(self._case_count))

        self._default = default


    def __call__(self, control, override_default=None):
        """Execute the defined switch statement using `control` as the variable to compare against the cases.

        :param control: Note that `control` also needs to be a hashable type, meaning that that lists, dicts, and other mutable containers cannot be passed as variables to a switch.
        :param override_default: Whether or not a default operation was defined when this Switch was instantiated, providing a callable for `override_default` will cause that to be used as the default (non-matching) case for this invocation of the switch.
        """

        match = False
        submatch = False

        default = override_default if override_default is not None else self._default



        c=0
        f=0
        while c<self._case_count and not match:

            if self.fallthrough[c]: # we've find a fallthrough section

                f=0
                while f < self.fallthrough[c] and not submatch:

                    if self._case_func[c][f]: # callable comparator
                        match = submatch = self._cases[c][f].case(control)

                    else:
                        match = submatch = self._cases[c][f].case==control

                    f+=1

            else:
                if self._case_func[c]:
                    match = self._cases[c].case(control)
                else:
                    match = self._cases[c].case == control
            c+=1

        # print(match, submatch, c, f)

        # if we found a match, our indices will be 1 too high
        if submatch:
            # print(self._cases[c - 1])
            # print(self._cases[c-1][f-1])
            return (c.operation(control) for c in self._cases[c-1][f-1:])

        elif match:
            # print(self._cases[c - 1])
            return self._cases[c-1].operation(control)

        elif default:
            return default(control)



def _iscallable(obj):
    return hasattr(obj, "__call__")

def _isiterable(obj):
    return hasattr(obj, "__iter__")

def first_true(iterable, default=False, pred=None):
    """Returns the first true value in the iterable.

    If no true value is found, returns *default*

    If *pred* is not None, returns the first item
    for which pred(item) is true.

    """
    # first_true([a,b,c], x) --> a or b or c or x
    # first_true([a,b], x, f) --> a if f(a) else b if f(b) else x
    return next(filter(pred, iterable), default)

#
#
#
# d = {
#     Setting.MODDIR.value: {
#         "set": ["paths", "dir_mods"],
#         "to": (lambda v: Path(v)),
#     },
#
#     Setting.VFSMOUNT.value: {
#         "set": ["paths", "dir_vfs"],
#         "to": (lambda v: Path(v)),
#     },
#
#     Setting.LASTPROFILE.value: {
#         "set": ["_lastprofile"],
#         "to": (lambda v: v),
#     },
# }
# """:type: typing.MutableMapping[str, typing.MutableMapping[str,list[str]|(str)->Any]] """
#
# if p.exists() and p.is_dir():
#     cases = list(d.keys())
#     arg = setting
#
#     case = d[setting]
#
#     subject = self
#     for a in case["set"][:-1]:
#         subject = getattr(subject, a)
#     setattr(subject, case["set"][-1], d[setting]["to"](value))

def doubleZipList(list1, list2):
    c = []
    for k, v in zip(list1, list2):
        if isinstance(k, list):
            f = [t for t in zip(k, v)]
            c.append(f)
        else:
            c.append((k, v))
    return c


from collections import OrderedDict
import itertools as it
import operator as op
import functools as fun

def flatten(listOfLists):
    """Flatten one level of nesting"""
    return it.chain.from_iterable(listOfLists)

def printerate(iterable):
    for p in iterable:
        print(p)

def splitterate(iterator):
    return list(i if not isinstance(i, abcco.Iterator) else splitterate(i) for i in iterator )

def partition(pred, iterable):
    'Use a predicate to partition entries into false entries and true entries'
    # partition(is_odd, range(10)) --> 0 2 4 6 8   and  1 3 5 7 9
    t1, t2 = it.tee(iterable)
    return it.filterfalse(pred, t1), filter(pred, t2)

class ValueSwitch:
 def __init__(self,v):self.m,self.v=0,v
 def __iter__(self):yield self.__
 def __(self,*o): #list of options to match against
  if self.m or not o:return True # always returns 1 after first match (allows fallthrough)
  elif self.v in o:self.m=True
  return True

class DSwitch:
    def __init__(self, v):
        self.m, self.v = 0, v

    def __iter__(self):
        yield self.__

    def __(self, *o):  # list of options to match against
        if self.m or not o:
            return True  # always returns 1 after first match (allows fallthrough)
        elif self.v in o:
            self.m = True
        return True

def _varicomp(c, v):
    return c(v)


def _in_or_is(c, v, eq=op.eq, con=op.contains):
    try:
        return con(c,v)
    except TypeError:
        return eq(c,v)

def _call_or_in_or_is(c,v):
    try:
        return c(v)
    except TypeError:
        try:
            return op.contains(c, v)
        except TypeError:
            return op.eq(c, v)


def sswitch(value, comp=_in_or_is):
    return [lambda match: comp(match, value)]

if __name__ == '__main__':
    j=2
    cas = ["a", "11", "5", [25, "4", "5", "g"], "3", "&"]
    ops = [ord, int, int, [lambda v: j+v**2, lambda v: ord(str(v)[:1]), lambda v: None, type], int, ord]

    hashes = []

    # pprint([p for p in itertools.product(cas, ops)])
    [print(p) for p in it.takewhile(lambda x: not isinstance(x, list), ops)]
    # [print(type(p)) for p in ops]

    # printerate(flatten(cas))
    # print(splitterate(cas))
    print(splitterate(partition(lambda x: isinstance(x, list), cas)))

    # printerate(partition(lambda x: isinstance(x, list), cas))

    v="a"
    # print(first_true(cas, pred=fun.partial(op.eq, v)))
    #
    # for case in ValueSwitch(v):
    #     if case("a"):
    #         print("v is a")
    #
    #     if case(False):
    #         print ("fallthrough")
    #         break
    #
    #     if case ("25", 56, "5", "g"):
    #         print("second case")
    #         break
    #     if case():
    #         print("v not found")

    g=3
    # for case in sswitch(g):
    #     if case("3"):
    #         print("numba1")
    #         break
    #     if case("a"):
    #         print("numba2")
    #         break
    # else:
    #     print("default")
    #
    #
    # g=5
    # for case in sswitch(g):
    #     if case(3):
    #         print(0)
    #         break
    #     if case(["4", 5, 90]):
    #         print(1)
    #         break
    #     if case([99, 23]):
    #         print(2)
    #         break
    # else:
    #     print("default")

    g=12
    # for case in sswitch(g, _varicomp):
    #     if case(lambda gv: gv**2==25):
    #         print("squared")
    #         break
    #     if case(lambda gv: gv * 2 == 24):
    #         print ("doubled")
    #         break

    g="4"
    def thing(val):
        for case in sswitch(val, _call_or_in_or_is):
            if case(3):
                print(0)
                break
            if case(["4", 5, 90]):
                print("listed")
                break
            if case(lambda gv: gv * 2 == 24):
                print("doubled")
                break
        else:
            print("nada")

    thing("4")
    thing("3")
    thing(3)
    thing(12)



    # cc = doubleZipList(cas, ops)
    # c = []
    # t=(cas, ops)
    # for k,v in zip(cas, ops):
    #     if isinstance(k, list):
    #         f=[t for t in zip(k,v)]
    #         c.append(f)
    #     else:
    #         c.append((k,v))

    # pprint(cc)
    # s = Switch(cas, ops)

    # s("g")
    # s("11")
    # s("&")
    # [print(vv) for vv in s("4")]
    # print(s(5555))