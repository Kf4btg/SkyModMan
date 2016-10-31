from itertools import count as counter, chain
from functools import partial
from collections import abc, OrderedDict, namedtuple

from skymodman.utils import singledispatch_m

# used to prepare executable "move" actions
_mover = namedtuple("_mover", "first last split exec")

class ModCollection(abc.MutableSequence):
    """A sequence that acts in some ways like a set (cannot add multiple
    items with the same key to the collection), some ways like a list
    (can access elements via their integer-index (an easily-adjustable
    ordering, not intrinsically tied to an individual item)), and in
    some ways like a dict (can also access elements via their unique
    key).

    Performance needs to be tested, but access should be O(1) (or, if
    not 1, at least constant...), insertion and deletion linear (worst
    case should be some multiple of n, like O(3n), while typical case
    is more like O(2k), where k is determined by where the insertion/
    deletion takes place). Insertion at the end of the collection is O(1).

    The trade off for speed is, off course, space. At least three
    different underlying containers are used to track the various
    aspects of the collection; to be fair, though, they're mostly
    fairly small (just containing strings and ints), so I don't expect
    the memory usage to be much of a problem, either--at least not
    for a reasonably-sized collection."""

    def __init__(self, iterable=None):
        # {mod_key:mod_entry}
        self._map = {} # type: dict [str, Any]

        # mod-ordinal (int): mod_key (str)
        self._order = OrderedDict() # type: dict [int, str]

        # mod_key (str): mod-ordinal (int)
        # (reverse of _order)
        self._index = {} # type: dict [str, int]

        # we refer to len(self) a lot, so let's just track it
        self._length = 0

        if iterable is not None:
            self.extend(iterable)

    ##=============================================
    ## Abstract methods
    ##=============================================

    def __len__(self):
        return self._length

    def __unslice(self, slice_):
        """Make sense of a provided slice object (for __getitem__,
        __setitem__, and __delitem__).

        Returns 3-tuple of ints (start, stop, step), properly
        adjusted to take negative indexing into account."""

        # try to make sense of slice objects;
        # any or all of .start, .stop, and .step may be None

        a,b,n = slice_.start, slice_.stop, slice_.step

        if n is None: n = 1
        # step NEVER defaults to negative, even if start and stop
            # would indicate that was the intention

        elif n < 0:
            # negative step -> a defaults to len(), b to <before start>

            # stop==None is the only way to indicate that
            # item#0 should be included in the result when using a
            # negative step (using -1 in slice notation is, of course,
            # intepreted as (end of sequence));
            # if b==0, the result will terminate
            # just BEFORE the first item; so we return -1 NOT to
            # indicate negative indexing, but rather to show that
            # we want to go ALL THE WAY to 0
            return (self._length-1 if a is None else self._getposindex(a),
                    -1 if b is None else self._getposindex(b),
                    n)

        # else: positive step
        return (self._getposindex(a) if a else 0, # 0 if None or 0
                self._length if b is None else self._getposindex(b),
                n)


    def __getitem__(self, index):
        """
        If `index` is an integer, get the item currently located at that
        position in the ordering.

        If `index` is a string, return the item having that unique
        key.

        If index is a slice (i.e. notation was like ``collection[3:5]``,
        ``collection[3:13:2]``, or ``collection[5:3:-1]``) return a
        regular list containing the selected items
        """

        if isinstance(index, str):
            # will raise keyerror if 'index' is not a valid key
            key = index
        elif isinstance(index, slice):
            # start, stop, step = self.__unslice(index)

            # build and return a list
            return [self._map[k] for i in range(*self.__unslice(index))
                    for k in self._keyfromindex(i)]
        else:
            # raises index error if index is out of range
            key = self._keyfromindex(index)

        # NTS: possibly return an object that includes the item's
        # current ordinal...

        return self._map[key]

    #=================================
    # setitem + helper
    #---------------------------------

    def __setitem__(self, index, value):
        """
        Accepts integers or slices as valid values for `index`.
        """
        if isinstance(index, slice):
            # if the 'index' is a slice, then "value" must be an
            # iterable of values (or an iterator or a generator or ...)
            idxs = iter(range(*self.__unslice(index)))
            vals = iter(value)

            while True:
                try:
                    self.__setitem(self._getposindex(next(idxs)), next(vals))
                except StopIteration:
                    # this stops at end of the shortest sequence;
                    # it may be useful to throw an exception if there's
                    # a mismatch in length.
                    # ...let's put that one on the 'long-term' to-do list
                    break
        else:
            self.__setitem(self._getposindex(index), value)

    def __setitem(self, index, value):
        """Internal helper for __setitem__"""
        # call w/ pre-adjusted index

        # check for unique key
        key = value.key
        if key not in self._map:
            old_key = self._keyfromindex(index)
            # get (adjusted) index and old_key
            # index, old_key = self._get_index_and_key(index)

            # clear all refs to replaced data
            del self._index[old_key]
            del self._map[old_key]
            # and insert new
            self._order[index] = key
            self._index[key] = index
            self._map[key] = value

    #=================================
    # delitem + helpers
    #---------------------------------

    def __delitem__(self, index):

        if isinstance(index, str):
            # passed a key
            self.__delitem(self._index[index])
        elif isinstance(index, slice):
            # translate the slice endpoints & call helper
            self.__delslice(*self.__unslice(index))
        else:
            # assume index is int; adjust as necessary
            self.__delitem(self._getposindex(index))


    def __delitem(self, index:int):
        """__delitem__ helper; this ONLY accepts ints--that is, keys
        for the self._order mapping. They are assumed to have already
        been adjusted for negative indexing, if needed."""

        # adjust order; this intrinsically takes care of removing the
        # item (key) from the _order and _index mappings;
        # the method returns a list of removed keys; in this instance,
        # there should just be one
        old_key = self._shift_indices_up(index, 1)[0]

        # now delete from main _map
        del self._map[old_key]

        # update length
        self._length = len(self._map)


    def __delslice(self, start, stop, step):
        """Internal helper for deleting slices"""
        if step == 1:
            # no surprises here, just delete the range of entries

            # shift indices up; hold onto the keys being removed
            k2r = self._shift_indices_up(start, stop - start)

            # delete all removed entries from map
            for k in k2r:
                del self._map[k]

            # update length attribute
            self._length = len(self._map)

        else:
            # if "step" is something other than 1 (or None), it's
            # a bit more involved; since _shift_indices_up changes
            # the order and index maps, doing a 1-by-1 loop w/ the
            # values from the slice won't work (the values would
            # be invalid after the first iteration)

            # thus, we get the keys currently at those values
            k2r = [self._order[i]
                   for i in range(start, stop, step)]

            # then, to keep things simple, delete each from self
            for k in k2r:
                self.__delitem(self._index[k])

            # the length attr will be set in the del self[k] call

    #=================================
    # Item insertion
    #---------------------------------

    def insert(self, index, value):
        """Add a new item at the ordinal `index`. Value must have
        a ``key`` attribute that is unique amongst all other values
        in the collection."""

        # NTS: consider allowing 'value' to just be hashable, rather
        # than requiring the key attribute; or maybe allow a key()
        # function; or maybe don't, since this is really just specific
        # to this application and doesn't need to be so generic...

        # data needs to have a 'key' attribute
        key = value.key

        # built-in set type does not throw an error for elements
        # that already exist; dict does, however...which to imitate?
        if key not in self._map:

            idx = self._getposindex(index)

            if 0 <= idx < self._length:
                # shift all indices below this down one.
                self._shift_indices_down(idx, 1)
            elif idx != self._length:
                # (index == length) is the only other valid scenario
                # (in that case, this is an append op, and no shifting
                # is necessary); anything else is out of range
                raise IndexError(index) # raise with original index

            # track new item's order
            self._order[idx] = key
            self._index[key] = idx

            # and finally add val to map
            self._map[key] = value

            # update length attr
            self._length = len(self._map)

    ##=============================================
    ## overrides
    ##=============================================

    def __contains__(self, value):

        # return true if value is a key that exists in our mapping
        if isinstance(value, str):
            return value in self._map

        # otherwise assume value is a ModEntry
        return value.key in self._map

    def __iter__(self):
        """Traverse the collection in the currently-defined order"""

        yield from (self._map[key] for key in self._order.values())

    def clear(self):
        # override for speed; no need to pop everything off 1by1;
        # having weakrefs to all nodes will allow gc to collect them
        # after they've been cleared from our mapping, so there
        # shouldn't be any problems w/ memory leaks here.
        self._map.clear()
        self._index.clear()
        self._order.clear()
        self._length = 0

    def extend(self, values):
        # override extend to improve performance

        m = self._map
        o = self._order
        i = self._index
        c = len(self._map)

        for v in values:
            k = v.key
            if k not in m:
                m[k] = v
                o[c] = k
                i[k] = c
                c+=1

        self._length = len(self._map)

    def index(self, value, start=0, stop=None) -> int:
        """Override to greatly increase speed when checking for the
        order of a mod (by ModEntry object or key). This ignores
        start and stop as the operation is about O(1).

        Raises ValueError if the value is not present"""

        if isinstance(value, str):
            key = value
        else:
            #assume is ModEntry
            try:
                key = value.key
            except AttributeError:
                # not modentry...call super method as last resort
                return super().index(value, start, stop)
        try:
            # check for key; ignore start and stop
            return self._index[key]
        except KeyError:
            raise ValueError(value) from None

    def __str__(self):
        # show order-number and key for each item
        s = self.__class__.__name__ + "("
        s+=", ".join("[{}: {}]".format(o,n) for o,n in self._order.items())
        return s + ")"

    ##=============================================
    ## Other
    ##=============================================

    def iter_order(self):
        """
        Iterate over the items of the collection, yielding ordered
        pairs of (int, object), where the first item is the current
        ordinal of the item in the collection, and the second item is
        the item itself.
        """
        yield from ((idx, self._map[key]) for idx, key in self._order.items())

    def verbose_str(self):
        """
        Unlike the regular str() functionality (which only prints the
        key of each item) this calls str(obj) on each item in the
        collection.
        """
        s = self.__class__.__name__ + "("
        s += ", ".join(
            "[{}: {}]".format(o, str(self._map[k])) for o, k in self._order.items())
        return s + ")"

    ##=============================================
    ## Rearrangement
    ##=============================================

    @singledispatch_m
    def move(self, from_index, to_index, count=1):
        """
        Change the order of an item or block of items.

        :param int|str from_index:
        :param int to_index:
        :param int count: number of items (including the first) to move
        """

        # adjust given indices, if needed
        self._change_order(self._getposindex(from_index),
                           self._getposindex(to_index),
                           count)

    @move.register(str)
    def _(self, key:str, dest:int, count:int=1):
        """Given the key of a an item in the list, move it to the new
        position, adjusting the index as needed for the new ordering

        :param key:
        :param dest:
        :param count:
        :return:
        """
        # get the index of the item to move based on its key
        self._change_order(self._index[key],
                           self._getposindex(dest),
                           count)

    def _change_order(self, old_position, new_position, num_to_move=1):
        """
        Move the item currently located at `old_position` to
        `new_position`, adjusting the indices of any affected items
        as needed.

        :param int old_position:
        :param int new_position:
        :param int num_to_move: Number of contiguous items to move
            (i.e. length of the slice starting at index `old_position`)
        """

        # Note -- The conventional way to visualize this is that
        # the item is being slotted in _before_ the destination index;
        # so, to move an item from position 7 to position 2, we pull
        # it out of slot 7 and slide it back in directly above the
        # item currently in slot 2, pushing that item down to slot 3,
        # the one below it to slot 4, etc, until the item that was
        # previously in slot 6 moves into the empty slot at slot 7.

        # So, moving an item UP means shifting all the items BEFORE it--
        # up to and including the item currently in the destination--
        # down by 1. Moving a contiguous section of items up just means
        # shifting the preceding items down by the number of items in
        # the section.

        # I don't know why this always makes my brain cry.

        ## don't do dumb things
        assert new_position != old_position
        assert num_to_move > 0
        assert new_position in range(self._length)
        assert old_position + num_to_move <= self._length

        new, old, count = new_position, old_position, num_to_move

        ## note:: there are some rambling talking-to-myself musings on why
        ## we move things around like this back in the git history of
        # this file. The gist of it is,
        # basically, because we're not really using lists OR modifying
        # the real data (kept safe and sound in self._map), we can
        # just get a list of the keys of the items we're moving around
        # (in their new order) and directly assign their new indexes
        # to _index and _order

        try:
            # save the keys we're moving around
            chunk = [self._order[i] for i in range(old, old+count)]

            if new < old:
                # moving up (to LOWER indices)

                # append the stuff from <the target index> to <right before
                # our original index> to the chunk (since, after "shifting"
                # these values out of the way, they will come after our
                # "moved" values in the New Order)

                first=new
                chunk += [self._order[i] for i in range(new,old)]

            elif old < new:
                #     moving down (to HIGHER indices)

                # have to shift items <immediately after the main block> to
                # <index where the END of our block will end up>.
                # This can stuck on the front of the original chunk to get
                # the New Order
                first = old
                chunk = [self._order[i] for i in range(old+count, new+count)] + chunk

            else:
                # old==new WHAT ARE YOU DOING GET OUT OF HERE
                return
        except KeyError as e:
            # if a key (an int in this case) was not found, that effectively
            # means the given index was "out of bounds"

            raise IndexError(e.args[0],
                         "Tried to move item(s) beyond end of collection") from None

        # now plug the whole chunk back in;
        # we don't need to worry about the 'last' index because the
        # length of the chunk implicitly handles that; so we just
        # start counting at first.
        for i,k in zip(counter(first), chunk):
            self._index[k] = i
            self._order[i] = k

    def prepare_move(self, start, end, count):
        """This prepares a move operation, then returns an object
        that can be used to actually execute the move.

        The returned object will have ``first`` and ``last``
        attributes, corresponding to the start and end points of the
        full range of indices affected by the move operation.

        To execute the move, call the ``exec()`` method of the returned
        object. As a convenience, to 'undo' the move and put the
        affected items back in their previous positions, simply call
        ``exec(undo=True)``

        IMPORTANT!: if the collection has been modified since
        the creation of the mover-object, the results of calling
        ``exec()`` are undefined and data may be lost!

        :param int start: current index of 1st item in block
        :param int end: target index for 1st item in block
        :param int count: number of items, including `start`, to include in
            the block that gets moved
        """

        # adjust given indices, if needed
        old = self._getposindex(start)
        new = self._getposindex(end)

        if old == new:
            # throw error?
            return None, None, None

        # return first, last, split
        return (min(old, new),
                max(old, new) + count,
                count if old<new else (old-new))

        ## Legend:
        # old > new => Up   (to lesser index)
        # old < new => Down (to greater index)


        #  first is start of affected chunk
        # last is index immediately AFTER the end of the chunk
        # first, last = min(old, new), max(old, new) + count

        # if going DOWN, split=length of chunk to be lowered;
        # elif going UP, split=length of section between the destination
        #                      and the start of the section to be raised
        # split_on = count if old<new else (old-new)


        # # precalculate the new order
        # try:
        #
        #     selected_keys = [self._order[i] for i in
        #                      range(old, old + count)]
        #
        #     if old < new:  # increasing index
        #         c_start = old
        #         # selected block goes on end
        #         reordered = [self._order[i] for i in
        #                      range(old + count,
        #                            new + count)] + selected_keys
        #
        #         # calculate the "split" point so the move can easily be
        #         # undone (swap the section [0:split] with [split:-1] to
        #         # get the original ordering back)
        #         split = len(reordered) - len(selected_keys)
        #     else:  # decreasing index (cannot be equal)
        #         c_start = new
        #         # selected block goes at beginning
        #         reordered = selected_keys + [self._order[i] for
        #                                      i in
        #                                      range(new, old)]
        #
        #         # split after 'selected_keys' section
        #         split = len(selected_keys)
        # except KeyError as e:
        #     # if a key (an int in this case) was not found, that effectively
        #     # means the given index was "out of bounds"
        #
        #     raise IndexError(e.args[0],
        #                      "Tried to move item(s) beyond end of collection") from None

        # return min(old, new), max(old, new) + count, split, tuple(reordered)

        # each 'Mover' object will contain the list of keys in the
        # new order that they should appear after the move is executed,
        # along with the index where insertion of the keys should begin.
        # Obviously, if the collection is changed between the creation
        # of this object and its execution, the collection will be
        # left in an undefined state afterwards, and data may have been
        # lost.
        # The move can easily be undone by passing undo=True to the
        # exec() method
        # return _mover(first=min(old, new),
        #               # last is the item immediately AFTER the shifted block
        #               last=max(old, new) + count,
        #               # defines the start of the block for the undo op
        #               split=split,
        #               exec=partial(self._do_move, c_start,
        #                            # convert the list to a tuple since
        #                            # we won't be modifying it further
        #                            tuple(reordered), split))



    # def _do_move(self, start_count, reordered_keys, split, undo=False):
    def exec_move(self, start_count, split, reordered_keys, undo=False):
        """Used as the exec() method on the _mover objects"""
        # if start_count and reordered_keys are set up correctly
        # (and the collection is unmodified since they were set up),
        # it shouldn't be possible to lose data w/ this operation.
        # everything will still be there, just in a different order

        if not undo:
            for i, k in zip(counter(start_count),
                            reordered_keys):
                self._index[k] = i
                self._order[i] = k
        else:
            # if we're undoing, rearrange the list using the split point
            for i, k in zip(counter(start_count),
                            reordered_keys[
                            split:] + reordered_keys[:split]
                            ):
                self._index[k] = i
                self._order[i] = k

    def _doshift(self, first, last, split):
        """Can it really be this simple? A move is just swapping the
        position of 2 sub-lists

        Doing it this way requires a bit more work on each operation
        (the sub-list is pulled from the collection on each run: O(k)),
        but greatly reduces the amount of information we have to store.

        :return: value of 'split' parameter for reversed op
        """
        # """
        # [8 9 | 10 11 12] => f=8, l=13, s=2
        #   |
        #   V
        # [10 11 12 | 8 9] => new s=3 (13-8-2)
        #
        #
        # [10 11 12 13 14 15 | 16 17 18] f=10 l=19 s=6
        #
        # [16 17 18 | 10 11 12 13 14 15] new s = (19-10)-6 = 9-6 = 3
        # """

        try:
            keys = [self._order[i] for i in range(first, last)]
        except KeyError as e:
            raise IndexError(e.args[0],
             "Tried to move item(s) beyond end of collection") from None

        # use itertools.chain to avoid list concatenation
        for j,k in zip(counter(first), chain(keys[split:],keys[:split])):
            self._index[k] = j
            self._order[j] = k

        return last - first - split

    ##=============================================
    ## Additional mechanics
    ##=============================================

    def _shift_indices_down(self, start_idx=0, count=1):
        """Starting at 'start_idx', increment each item's recorded order
        by `count`. This will effectively make an 'empty' section in the
        list `count` items in length.

        The empty section will be the `count` items before the item that
        was previously located at 'start_idx' So, for something like this:

        [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]

        if start_idx = 3 & count = 2, we'd end up with this:

        [0, 1, 2, _, _, 3, 4, 5, 6, 7, 8, 9]


        O(2k) complexity (where k=[current_max_ordinal - start_idx])"""

        # sanity check on the parameters
        if count > 0 <=start_idx:

            offset = count-1

            # start at the end so we don't overwrite data!
            # (_order[len(self._map)] is beyond the end of the list when we start)
            for i in range(self._length+offset, start_idx+offset, -1):
                key = self._order[i-count]

                # add placeholder to order map
                # (since _order is an OrderedDict, we only want to delete
                # items from the end, otherwise it will get dis-ordered!)
                self._order[i-count] = None

                # effectively add `count` to each ordinal;
                self._order[i] = key
                # record new position in index
                self._index[key] = i
        else:
            raise IndexError


    def _shift_indices_up(self, start_idx, count=1):
        """
        Decrease the ordinal by `count` for each item from `start_idx`
        to the end of the list. (Used when deleting items). This effectively
        overwrites a chunk of the list `count` items wide and shortens
        the list by the same amount

        The overwritten section starts at 'start_idx' and includes the
        `coount` items following it. So, for something like this:

        [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]

        if start_idx = 3, count = 2, we'd end up with this:

        [0, 1, 2, 5, 6, 7, 8, 9]

        :param int start_idx:
        :param int count:
        :return: list of keys that were removed from the ``order`` and
        ``index`` mappings by this operation.
        """

        # sanity check on the parameters
        if count > 0 <= start_idx:

            order = self._order
            key_index = self._index

            keys_to_remove = [order[i] for i in range(start_idx,
                                                      start_idx+count)]

            # remove key(s) about to be overwritten
            for k2r in keys_to_remove:
                del key_index[k2r]

            # current length of collection
            # coll_len = len(order)
            end_idx = self._length - count

            for i in range(start_idx, end_idx):
                key = order[i+count]
                # shift up
                order[i] = key
                # update index
                key_index[key] = i

            # remove 'tail' from order list
            for i in range(end_idx, self._length):
                del order[i]

            return keys_to_remove
        else:
            raise IndexError

    def _get_index_and_key(self, index):
        """Given a user-supplied index (which could be negative), return
        the (possibly-adjusted) index and key to which it points"""

        # handle negative indices
        index = self._getposindex(index)

        try:
            key = self._order[index]
        except KeyError:
            # make it look like we're a list
            raise IndexError(index, "Index out of range") from None

        return index, key

    def _getposindex(self, index):
        """

        :param index: If supplied w/ a negative index, will assume user
            is attempting to use reverse-indexing, and returns the
            index translated to its positive counterpart (Assuming the
            index was in range). If `index` is positive, it is returned
            as-is.

            This does not check for range constraints, so the returned
            value may still be negative/OOR-positive if the
            given value was OOR to begin with.
        """

        return index + self._length if index < 0 else index

    def _keyfromindex(self, index):
        """

        Throws IndexError if index out of range.

        :param index: A 'raw' (user-provided) index.
        :return: The key of the item located at that index, after
            accounting for possible negative-indexing.
        """

        try:
            return self._order[self._getposindex(index)]
        except KeyError:
            # since the 'key' was an int (as we sometimes pretend to
            # be a list), raise indexerror instead of keyerror
            raise IndexError(index, "Index out of range") from None




if __name__ == '__main__':
    class Fakeentry:
        def __init__(self, key):
            self.key = key
        def __str__(self):
            return "FakeEntry({})".format(self.key)


    tcoll = ModCollection([Fakeentry(w) for w in "ABCDEF"])
    for ix, ky in enumerate("ABCDEF"):
        assert tcoll[ix].key == ky
    print("START:", tcoll, len(tcoll))

    tcoll.extend([Fakeentry(w) for w in "GHIJKL"])
    for ix, ky in enumerate("GHIJKL", start=6):
        assert tcoll[ix].key == ky
    print("EXTEND:", tcoll, len(tcoll))

    tcoll.append(Fakeentry("Z"))
    assert tcoll[-1].key == "Z"
    print("APPEND:", tcoll, len(tcoll))

    tcoll.insert(5, Fakeentry("Y"))
    assert tcoll[5].key == "Y"
    print("INSERT_5", tcoll, len(tcoll))

    tcoll.insert(0, Fakeentry("a"))
    assert tcoll[0].key == "a"
    print("INSERT_0", tcoll, len(tcoll))

    print("GETINT_8", tcoll[8], len(tcoll))

    print("GETINT_-1", tcoll[-1])

    print("GETKEY_G", tcoll["G"], len(tcoll))

    x=tcoll[8]
    assert x in tcoll
    assert x.key in tcoll

    del tcoll[8]
    assert x not in tcoll
    assert x.key not in tcoll
    print("DELINT_8", tcoll, len(tcoll))

    del tcoll["H"]
    assert "H" not in tcoll
    print("DELKEY_H", tcoll, len(tcoll))

    del tcoll["Z"]

    print("DELKEY_Z", tcoll, len(tcoll))

    del tcoll[0]

    print("DELINT_0", tcoll, len(tcoll))

    tcoll[8]=Fakeentry('X')

    print('SETIDX_8', tcoll, len(tcoll), '\n')

    tcoll.move(6, 9)

    print('MVIDX_6_9', tcoll, len(tcoll), '\n')

    tcoll.move(6,3)

    print('MVIDX_6_3', tcoll, len(tcoll), '\n')

    tcoll.move('Y', 0)

    print('MVKEY_Y_0', tcoll, len(tcoll), '\n')

    tcoll.move(3, 8, 3)

    print('MVCHUNK_3-5_8', tcoll, len(tcoll), '\n')

    print('SLICE_4:8', [e.key for e in tcoll[4:8]], '\n')

    tcoll[2:5] = [Fakeentry('0'), Fakeentry('1'), Fakeentry('2')]
    print('SETSLC_2:5', tcoll, len(tcoll), '\n')

    tcoll[2:5] = (Fakeentry(k) for k in "543")
    print('SETSGEN', tcoll, '\n')
    tcoll[2:5] = map(Fakeentry, "678")
    print('SETSMAP', tcoll, '\n')

    del tcoll[2:5]
    print('DELSLC_2:5', tcoll, len(tcoll))

    print("tcoll[1:]")
    print([e.key for e in tcoll[1:]])
    print("tcoll[:-1]")
    print([e.key for e in tcoll[:-1]])
    print("tcoll[:2]")
    print([e.key for e in tcoll[:2]])
    print("tcoll[:4:2]")
    print([e.key for e in tcoll[:4:2]])
    print("tcoll[1::2]")
    print([e.key for e in tcoll[1::2]])
    print("tcoll[::2]")
    print([e.key for e in tcoll[::2]])
    print("tcoll[::]")
    print([e.key for e in tcoll[::]])
    print("tcoll[::-1]")
    print([e.key for e in tcoll[::-1]])


    del tcoll[:8:2]
    print('DELSLC_0:8:2', tcoll, len(tcoll))

    # import json
    # print(json.dumps(tcoll, indent=1, default=lambda o: list(i.__dict__ for i in o)))

