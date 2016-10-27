from itertools import count as counter
from collections import abc, OrderedDict
from weakref import proxy

# Node object for linked list of items in ModCollection
class _Node:
    __slots__ = 'prev', 'next', 'key', 'data', '__weakref__'

    def __init__(self, prev=None, next_=None, key=None, data=None):
        """

        :param _Node prev:
        :param _Node next_:
        :param str key:
        :param data:
        """
        self.prev, self.next, self.key, self.data = prev, next_, key, data

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
        # {mod_key:_Node}
        self._map = {} # type: dict [str, _Node]

        # mod-ordinal (int): mod_key (str)
        self._order = OrderedDict() # type: dict [int, str]

        # mod_key (str): mod-ordinal (int)
        # (reverse of _order)
        self._index = {} # type: dict [str, int]

        # initialize root/sentinel node
        self._root = _Node()
        # these pointers are hard-refs so we don't lose our sentinel
        self._root.prev = self._root.next = self._root

        if iterable is not None:
            self.extend(iterable)

    ##=============================================
    ## Abstract methods
    ##=============================================

    def __len__(self):
        return len(self._map)

    def __getitem__(self, index):
        """
        If `index` is an integer, get the item currently located at that
        position in the ordering.

        If `index` is a string, return the item having that unique
        key."""

        # TODO: support slices

        # (bytes, str) -- nah, don't worry about bytes...
        if isinstance(index, str):
            # will raise keyerror if 'index' is not a valid key
            key = index
        else:
            # will raise indexerror if index out of range, type error
            # if it is not a number
            index = self._get_real_index(index)

            key = self._order[index]

        # return the actual data stored in the node at that index
        # NTS: should this return the Node object? Allowing us to see
        # which mods are previous/next? Maybe.
        # NTS: or possibly return an object that includes the item's
        # current ordinal...

        return self._map[key].data

    def __setitem__(self, index, value):
        # TODO: support slices

        key = value.key

        # check for unique key
        if key not in self._map:
            index = self._get_real_index(index)

            # create new node for this item
            newnode = _Node()

            # set key and data
            newnode.key, newnode.data = key, value

            # check if we're replacing an item
            # if index in range(len(self._map)):

            ## delete old item ##

            # don't have to shift anything if we're just replacing
            # a single item

            # get current key at this index
            old_key = self._order[index]

            # its nanoseconds are numbered
            doomed = self._map[old_key]
            _prev, _next = doomed.prev, doomed.next

            # add pointers to new node
            newnode.prev, newnode.next = _prev, _next

            # adjust pointers on adjacent nodes
            _prev.next = _next.prev = proxy(newnode)

            # clear all refs to replaced data
            del self._index[old_key]
            del self._map[old_key]
            # and insert new
            self._order[index] = key
            self._index[key] = index
            self._map[key] = newnode

    def __delitem__(self, index):

        # TODO: support slices

        if isinstance(index, str):
            # passed a key
            idx = self._index[index]
            key = index
        else:
            # assume index is int
            idx = self._get_real_index(index)
            key = self._order[index]


        # adjust order; this intrinsically takes care of removing the
        # item (key) from the _order and _index mappings
        self._shift_indices_up(idx, 1)

        # adjust pointers
        doomed = self._map[key]
        _prev, _next = doomed.prev, doomed.next

        _prev.next, _next.prev = _next, _prev

        # now delete node from main _map; weakref should allow it to be
        # garbage collected shortly
        del self._map[key]

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


            if index == len(self._map):
                # an 'append' operation:
                # the 'next' node will be the sentinel
                _next = self._root
            else:
                # do this here since we want to allow the 'append'
                # operation above, and this would throw IndexError
                # on index==len(self); don't bother trying to allow
                # '-len(self)' as a valid index because that's silly.
                index = self._get_real_index(index)

                # get current node at that index
                _next = self._map[self._order[index]]

                # shift all indices below this down one.
                self._shift_indices_down(index, 1)

            _prev = _next.prev

            # assign data and pointers to new node
            node = _Node(_prev, _next, key, value)

            # store pointers to new node as weak references
            _prev.next = _next.prev = proxy(node)

            # track new item's order
            self._order[index] = key
            self._index[key] = index

            # and finally add node to map (as strong reference, so we
            # don't lose the node altogether on next gc collect; to
            # release node we only have to remove from map)
            self._map[key] = node


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


        # XXX: I don't think this really fits with our 'keep order external' thing...we may just need to ditch the linked list; we can implement this using the _order and _index mappings

        root = self._root
        curr = root.next

        while curr is not root:
            yield curr.data
            curr = curr.next

    def clear(self):
        # override for speed; no need to pop everything off 1by1;
        # having weakrefs to all nodes will allow gc to collect them
        # after they've been cleared from our mapping, so there
        # shouldn't be any problems w/ memory leaks here.
        self._map.clear()
        self._index.clear()
        self._order.clear()

    def extend(self, values):
        # override extend to improve performance

        m = self._map
        o = self._order
        i = self._index
        r = self._root
        c = len(self._map)

        for v in values:
            k = v.key
            if k not in m:
                p = r.prev
                n = _Node(p, r, k, v)
                r.prev = p.next = proxy(n)
                m[k] = n
                o[c] = k
                i[k] = c
                c+=1

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
            raise ValueError from None

    def __str__(self):
        s = self.__class__.__name__ + "("
        s+=", ".join("[{}: {}]".format(o,n) for o,n in self._order.items())
        return s + ")"

    ##=============================================
    ## Rearrangement
    ##=============================================

    def change_order(self, old_position, new_position, num_to_move=1):
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

        # TODO: get rid of linked list, it's unnecessary.

        # can't go past this!
        _imax = len(self._map)

        ## don't do dumb things
        assert new_position != old_position
        assert num_to_move > 0
        assert new_position in range(_imax)
        assert old_position + num_to_move <= _imax

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

            # shift following items up
            # range: <index imm. after chunk> to <dest. index + count lower>
            # shift amount: -count
            for i in range(old+count, new+count):
                key = self._order[i]
                raise_to = i-count

                self._index[key] = raise_to
                self._order[raise_to] = key

            # put chunk in place
            for key, new_home in zip(chunk, counter(new)):
                self._order[new_home] = key
                self._index[key] = new_home



    def change_item_order(self, key, new_position):
        """Given the key of a an item in the list, move it to the new
        position, adjusting the index as needed for the new ordering"""

        # current index
        self.change_order(self._index[key], new_position)

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
            for i in range(len(self._map)+offset, start_idx+offset, -1):
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
            coll_len = len(order)
            end_idx = coll_len - count

            for i in range(start_idx, end_idx):
                key = order[i+count]
                # shift up
                order[i] = key
                # update index
                key_index[key] = i

            # remove 'tail' from order list
            for i in range(end_idx, coll_len):
                del order[i]


    def _get_real_index(self, index):
        """Translate an index (which could be out of range or negative)
        into a usable index, or throw IndexError as needed"""

        try:
            if abs(index) >= len(self._map):
                # out of range
                raise IndexError
        except TypeError:
            # abs() check failed
            raise TypeError("not a number") from None

        if index < 0:
            # indexing from end
            return index + len(self._map)

        # index is fine as is
        return index



if __name__ == '__main__':
    class Fakeentry:
        def __init__(self, key):
            self.key = key
        def __str__(self):
            return "FakeEntry({})".format(self.key)


    tcoll = ModCollection([Fakeentry(w) for w in "ABCDEF"])

    print("START:", tcoll)

    tcoll.extend([Fakeentry(w) for w in "GHIJKL"])

    print("EXTEND:", tcoll)

    tcoll.append(Fakeentry("Z"))

    print("APPEND:", tcoll)

    tcoll.insert(5, Fakeentry("Y"))

    print("INSERT_5", tcoll)

    tcoll.insert(0, Fakeentry("1"))

    print("INSERT_0", tcoll)

    print("GETINT_8", tcoll[8])

    print("GETKEY_G", tcoll["G"])

    del tcoll[8]

    print("DELINT_8", tcoll)

    del tcoll["H"]

    print("DELKEY_H", tcoll)

    del tcoll["Z"]

    print("DELKEY_Z", tcoll)

    del tcoll[0]

    print("DELINT_0", tcoll)




