from itertools import count as counter
from collections import abc, OrderedDict

from skymodman.utils import singledispatch_m

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

    def __getitem__(self, index):
        """
        If `index` is an integer, get the item currently located at that
        position in the ordering.

        If `index` is a string, return the item having that unique
        key."""

        # TODO: support slices

        if isinstance(index, str):
            # will raise keyerror if 'index' is not a valid key
            key = index
        else:
            # raises index error if index is out of range
            key = self._keyfromindex(index)

        # NTS: possibly return an object that includes the item's
        # current ordinal...

        return self._map[key]

    def __setitem__(self, index, value):
        # TODO: support slices

        key = value.key

        # check for unique key
        if key not in self._map:
            # get (adjusted) index and old_key
            index, old_key = self._get_index_and_key(index)

            # clear all refs to replaced data
            del self._index[old_key]
            del self._map[old_key]
            # and insert new
            self._order[index] = key
            self._index[key] = index
            self._map[key] = value

    def __delitem__(self, index):

        # TODO: support slices

        if isinstance(index, str):
            # passed a key
            key = index
            idx = self._index[key]
        else:
            # assume index is int
            idx, key = self._get_index_and_key(index)

        # adjust order; this intrinsically takes care of removing the
        # item (key) from the _order and _index mappings
        self._shift_indices_up(idx, 1)

        # now delete from main _map
        del self._map[key]

        # update length
        self._length = len(self._map)

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
    ## Rearrangement
    ##=============================================

    @singledispatch_m
    def move(self, from_index, to_index, count=1):
        """
        Change the order of an item or block of items.

        :param int|str from_index:
        :param int to_index:
        :param int count:
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

        # So, moving an item UP means shifting all the items BEFORE it,
        # up to and including the item currently in the destination,
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

        # save the keys we're moving around
        chunk = [self._order[i] for i in range(old, old+count)]

        if new < old:
            # moving up

            # shift the preceding items (new->old-1) down;
            # but we have to start at the bottom (the bottom falls first!)
            for i in range(old-1, new-1, -1):
                key = self._order[i] # what's here right now?
                drop_to = i+count

                # shift down (give higher index)
                self._index[key] = drop_to

                # record new order
                self._order[drop_to] = key

            # slide chunk into place
            for key, new_home in zip(chunk, counter(new)):
                # give them an address
                self._order[new_home] = key
                # put them in the phone book
                self._index[key] = new_home


        elif old < new:
            # moving down

            # need to make sure we don't go past the end
            # new += min(0, _imax - (new+count))
            ## -- actually, this means we have bad arguments...(see below)

            # shift following items up
            # range: <index imm. after chunk> to <dest. index + count lower>
            # shift amount: -count
            for i in range(old+count, new+count):
                try:
                    key = self._order[i]
                except KeyError:
                    raise IndexError(i, "Tried to move item(s) beyond end of collection") from None
                raise_to = i-count

                self._index[key] = raise_to
                self._order[raise_to] = key

            # put chunk in place
            for key, new_home in zip(chunk, counter(new)):
                self._order[new_home] = key
                self._index[key] = new_home

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
        """

        # sanity check on the parameters
        if count > 0 <= start_idx:

            order = self._order
            key_index = self._index

            # remove key(s) about to be overwritten
            for key_to_remove in [order[i] for i in range(start_idx, start_idx+count)]:
                del key_index[key_to_remove]

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

    tcoll.insert(0, Fakeentry("1"))
    assert tcoll[0].key == "1"
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

    print('SETIDX_8', tcoll, len(tcoll))

    tcoll.move(6, 9)

    print('MVIDX_6_9', tcoll, len(tcoll))

    tcoll.move(6,3)

    print('MVIDX_6_3', tcoll, len(tcoll))

    tcoll.move('Y', 0)

    print('MVKEY_Y_0', tcoll, len(tcoll))

    tcoll.move(3, 8, 3)

    print('MVCHUNK_3-5_8', tcoll, len(tcoll))
