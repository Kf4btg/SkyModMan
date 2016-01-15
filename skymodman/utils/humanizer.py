"""
http://code.activestate.com/recipes/578619-humanize-decorator/

Created by tomer filiba on Wed, 31 Jul 2013 (MIT)

When you need to inspect Python objects in a human-readable way, you're usually required to implement a custom __str__ or __repr__ which are just boilerplate (e.g., return "Foo(%r, %r, %r)" % (self.bar, self.spam, self.eggs). You may implement __str__ and __repr__ by a base-class, but it's hard to call it inheritance and moreover, you may wish to remove it when you're done debugging.

This simple (yet complete) recipe is a class decorator that injects __str__ and __repr__ into the class being printed. It handles nesting and even cycle detection, allowing you to just plug it into existing classes to get them pretty-printed and perhaps remove it later.

Example:
    ```
        @humanize
        class Foo(object):
            def __init__(self, **kw):
                self.__dict__.update(kw)

        x = Foo(bar = 5, zar = "hello", mar = Foo())
        x.gar = [Foo(a = 17, b = 18), Foo(c = 19), Foo(e = 20, f = 21)]
        x.lap = {
            "zizi" : "tripo",
            "mimi" : Foo(g = 22, h = 23, q = {}, p = []),
            "x" : x,
        }
        print x
    ```
Which results in:

    ```
    Foo:
       bar = 5
       mar = Foo()
       zar = 'hello'
       gar = [
          Foo:
             a = 17
             b = 18,
          Foo:
             c = 19,
          Foo:
             e = 20
             f = 21,
       ]
       lap = {
          'zizi': 'tripo',
          'mimi': Foo:
             q = {}
             p = []
             g = 22
             h = 23,
          'x': <...>,     # <<< prevent going into a cycle
       }
    ```

"""


import threading
from contextlib import contextmanager

_tls = threading.local()

@contextmanager
def _nested():
    _tls.level = getattr(_tls, "level", 0) + 1
    try:
        yield "   " * _tls.level
    finally:
        _tls.level -= 1

@contextmanager
def _recursion_lock(obj):
    if not hasattr(_tls, "history"):
        _tls.history = []  # can't use set(), not all objects are hashable
    if obj in _tls.history:
        yield True
        return
    _tls.history.append(obj)
    try:
        yield False
    finally:
        _tls.history.pop(-1)

def humanize(cls):
    def __repr__(self):
        if getattr(_tls, "level", 0) > 0:
            return str(self)
        else:
            try:
                attrs = ", ".join("%s = %r" % (k, v) for k, v in self.__dict__.items())
            except AttributeError:
                attrs = ", ".join("{} = {}".format(k,getattr(self,k)) for k in self.__slots__)
            return "%s(%s)" % (self.__class__.__name__, attrs)

    def __str__(self):
        with _recursion_lock(self) as locked:
            if locked:
                return "<...>"
            with _nested() as indent:
                attrs = []
                try:
                    info = self.__dict__
                except AttributeError:
                    info = {k:getattr(self, k) for k in self.__slots__}
                # for k, v in self.__dict__.items():
                for k, v in info.items():
                    # if k.startswith("_"):
                    #     continue
                    if isinstance(v, (list, tuple)) and v:
                        attrs.append("%s%s = [" % (indent, k))
                        with _nested() as indent2:
                            for item in v:
                                attrs.append("%s%r," % (indent2, item))
                        attrs.append("%s]" % (indent,))
                    elif isinstance(v, dict) and v:
                        attrs.append("%s%s = {" % (indent, k))
                        with _nested() as indent2:
                            for k2, v2 in v.items():
                                attrs.append("%s%r: %r," % (indent2, k2, v2))
                        attrs.append("%s}" % (indent,))
                    else:
                        attrs.append("%s%s = %r" % (indent, k, v))
                if not attrs:
                    return "%s()" % (self.__class__.__name__,)
                else:
                    return "%s:\n%s" % (self.__class__.__name__, "\n".join(attrs))

    cls.__repr__ = __repr__
    cls.__str__ = __str__
    return cls