from collections.abc import MutableSequence, MutableSet
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

class ModCollection(MutableSequence):
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
        self._order = {} # type: dict [int, str]

        # mod_key (str): mod-ordinal (int)
        # (reverse of _order)
        self._index = {} # type: dict [str, int]

        # initialize root/sentinel node
        self._root = _Node()
        # these pointers are hard-refs so we don't lose our sentinel
        self._root.prev = self._root.next = self._root

    ##=============================================
    ## Abstract methods
    ##=============================================

    def __getitem__(self, index):
        """
        If `index` is an integer, get the item at currently set as that
        number in the ordering.

        If `index` is a string, return the item having that unique
        key."""

        # TODO: support slices

        # (bytes, str) -- nah, don't worry about bytes...
        if isinstance(index, str):
            # will raise keyerror if 'index' is not a valid key
            key = index
        else:
            # will raise indexerror if index too high, type error
            # if it is not a number
            key = self._order[index]

        # return the actual data stored in the node at that index
        # XXX: should this return the Node object? Allowing use see which mods are previous/next? Maybe.
        # XXX: or possibly return an object that includes the item's current ordinal...

        return self._map[key].data


    def __setitem__(self, index, value):
        # TODO: support slices

        key = value.key

        # check for unique key
        if key not in self._map:

            # create new node for this item
            newnode = _Node()

            # set key and data
            newnode.key, newnode.data = key, value

            # check if we're replacing an item
            if index in range(len(self._map)):

                ## delete old item ##

                # don't have to shift anything if we're just replacing
                # a single item

                # get current key at this index
                old_key = self._order[index]

                doomed = self._map[old_key]
                _prev, _next = doomed.prev, doomed.next

                # add pointers to new node
                newnode.prev, newnode.next = _prev, _next

                # adjust pointers on adjacent nodes
                _prev.next = _next.prev = proxy(newnode)

                # clear all refs to replaced data
                self._order[index] = key

                del self._index[old_key]
                self._index[key] = index

                del self._map[old_key]

    def __len__(self):
        return len(self._map)

    def __delitem__(self, index):

        # TODO: support slices

        if isinstance(index, str):
            # passed a key
            idx = self._index[index]
            key = index
        else:
            # assume index is int
            idx = index
            key = self._order[index]


        # adjust order; this intrinsically takes care of removing the
        # item (key) from the _order and _index mappings
        self._shift_up(idx, 1)

        # adjust pointers
        doomed = self._map[key]
        _prev, _next = doomed.prev, doomed.next

        _prev.next = _next
        _next.prev = _prev

        # now delete node from main _map; weakref should allow it to be
        # garbage collected shortly
        del self._map[key]

    def insert(self, index, value):
        """Add a new item at the ordinal `index`"""

        # if the provided index is higher than the length of our map, just do an 'add'
        if index > len(self._map):
            self.add(value)
        elif value.key not in self._map:

            key = value.key

            # get current node at that index
            current = self._map[self._order[index]]
            # and it's predecessor
            prev = current.prev

            # shift everything below this index down one
            # FIXME: my brain not work so good right now...but I have feeling that math not work out right in shift_down() funkshun; mite stop going before get to 'index'. Check later when brane on.
            #-- don't allow negative indices here
            self._shift_down(max(index, 0), 1)

            # new node
            node = _Node()

            # assign data and pointers to new node
            node.prev, node.next, node.key, node.data = prev, current, key, value

            # store pointers to new node as weak references
            prev.next = current.prev = proxy(node)

            # track new item's order
            self._order[index] = key
            self._index[key] = index

            # and finally add to map
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

    def add(self, data):
        """Add `data` to the end of the collection. Key must be a unique
        value that can be used to identify this data"""

        # data needs to have a 'key' attribute
        key = data.key # type: str

        if key not in self._map:
            node = _Node()

            root = self._root
            last = root.prev

            # assign data and pointers to new node
            node.prev, node.next, node.key, node.data = last, root, key, data

            # store pointers to new node as weak references
            last.next = root.prev = proxy(node)

            # track new item's order (easy to calculate since it is the
            # last item in the list)
            idx = len(self._map)
            self._order[idx] = key
            self._index[key] = idx

            # and finally add to map
            self._map[key] = node

            # built-in ``set`` type does not throw an error for elements
            # that already exist; dict does, however...



    ##=============================================
    ## Additional mechanics
    ##=============================================

    def _shift_down(self, start_idx=0, count=1):
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
                self._order[i-count] = None

                # effectively add `count` to each ordinal;
                self._order[i] = key
                # record new position in index
                self._index[key] = i


    def _shift_up(self, start_idx, count=1):
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

            end_idx = len(self._map)-count

            for i in range(start_idx, end_idx):
                # grab the 'new' key for this index (use pop to make
                # sure we clear the 'tail' at the end of the 'list')
                key = self._order.pop(i+count)
                old_key = self._order[i]
                # set popped key in its new location (overwrites the
                # old key that was there)
                self._order[i] = key

                # remove overwritten entry from index...
                self._index.pop(old_key)

                # ...and record new position of moved key
                self._index[key] = i
