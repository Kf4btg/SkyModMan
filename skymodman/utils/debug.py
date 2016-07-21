


class _Printer:
    """
    Because sometimes the log doesn't cut it.
    """

    def __lshift__(self, other):
        print(other, end=" ")
        return self

    def __del__(self):
        print()

Printer = _Printer()

def printattrs(obj, name=None, dunder=True, sunder=True):
    """
    For debugging. Prints the name and value of any entry in the object's dir(). Works for classes with or without a __dict__
    :param obj:
    :param name: Just used to label the object in output
    :param dunder: Include double-underscore __names__ in output
    :param sunder: Include single-underscore _names in output
    :return:
    """
    from pprint import pprint
    from collections import Mapping, Sequence
    if name:
        print(name+":")
    else:
        print("attributes:")

    for a in dir(obj):
        if not dunder and a.endswith("__"): continue
        if not sunder and a.startswith("_"): continue
        print("    ",end="")

        try:
            attr=getattr(obj,a)
        except AttributeError:
            # I have no idea how this happens...
            continue
        if isinstance(attr,(Mapping,Sequence)) and not isinstance(attr,(str,bytes)):
            print(a,end=": ")
            pprint(attr, indent=4)
        else:
            print(a, attr, sep=": ")