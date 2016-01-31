from collections import deque, Mapping, Sequence


class diqt(deque):
    """It is not recommended to create a maxlen-bounded diqt from an existing dictionary unless you know for sure that the dictionary is smaller than `maxlen`. If the dict has more elements than `maxlen`, it is guaranteed that some will be dropped, but it is impossible to know which ones due to a dict's unordered nature."""

    def __init__(self, iterable_=(), values_=None, maxlen_=None, **kwargs):
        self._values = deque(maxlen=maxlen_)
        keys = deque(maxlen=maxlen_)

        if values_ is None:
            # assume iterable is either empty, a dict, or an ordered sequence of pairs
            if iterable_:
                # super().__init__(maxlen=maxlen_)

                if isinstance(iterable_, Mapping):

                    # self._values = deque(maxlen=maxlen_)
                    # keys = deque(maxlen=maxlen_)

                    for k,v in iterable_.items():
                        keys.append(k)
                        self._values.append(v)
                    # super().init(keys, maxlen_)

                # ordered pairs
                elif isinstance(iterable_[0], Sequence) \
                    and len(iterable_[0])==2:
                    # we'll just assume the rest are also pairs...
                    # self._values = deque(maxlen=maxlen_)
                    # keys = deque(maxlen=maxlen_)
                    for k,v in iterable_:
                        keys.append(k)
                        self._values.append(v)
                    # super().__init__(keys, maxlen_)

                else:
                    raise TypeError("If the 'values_' argument is not provided, the first argument to diqt() must be either a mapping or a sequence of ordered pairs.")
            #else:
                # either it's empty or we have kwargs, which will be taken care of below

        elif iterable_:
            assert len(iterable_) == len(values_), "The 'iterable' and 'values' arguments must be equal in length."
            keys = deque(iterable_, maxlen_)
            self._values = deque(values_, maxlen_)

        else:
            raise TypeError("The 'values' argument requires a corresponding 'iterable' argument.")


        for k, v in kwargs.items():
            keys.append(k)
            self._values.append(v)

        if keys:
            super().__init__(keys, maxlen_)
        else:
            super().__init__(maxlen=maxlen_)


    def __repr__(self):
        return "{}({})".format(type(self).__name__, ", ".join(str(k)+'='+str(v) for k,v in zip(self, self._values)))

    def __getitem__(self, item):
        if isinstance(item, int):
            return super().__getitem__(item)
        else:
            return self._values[self.index(item)]

    def __setitem__(self, key, value):
        try:
            i = self.index(key)
            self._values[i]=value
        except ValueError:
            super().append(key)
            self._values.append(value)

    def values(self):
        yield from self._values

    def keys(self):
        yield from self

    def items(self):
        yield from zip(self, self._values)

    def pop(self):
        super().pop()
        return self._values.pop()

    def popleft(self):
        super().popleft()
        return self._values.popleft()

    def rotate(self,n):
        super().rotate(n)
        self._values.rotate(n)

    def reverse(self):
        super().reverse()
        self._values.reverse()

    def append(self, key, value):
        super().append(key)
        self._values.append(value)

    def appendleft(self, key, value):
        super().appendleft(key)
        self._values.appendleft(value)

    def remove(self, key):
        i=self.index(key)
        del self._values[i]
        super().__delitem__(i)




def __test():
    d=diqt()

    #empty
    print(d)


    d=diqt(test=1, rest=33, lest="now", best=None)
    print(d)


    _123 = range(26)
    abc = 'abcdefghijklmnopqrstuvwxyz'

    # two seqs
    d=diqt(abc, _123)
    print(d)


    # tuples
    d=diqt([(n,a) for n,a in zip(reversed(abc), _123)])
    print(d)

    print("'a' in d:", 'a' in d)

    print("d[19]={}".format(d[19]))

    print("d['g']={}".format(d['g']))

    d = diqt(abc, _123, maxlen_=10)

    print(d)

    d.append("lalala", 84848)

    print(d)




if __name__ == '__main__':
    __test()