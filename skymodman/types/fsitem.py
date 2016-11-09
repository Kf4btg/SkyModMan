from pathlib import Path
from os.path import join
from itertools import count
from functools import total_ordering

# @humanizer.humanize
@total_ordering
class FSItem:
    """
    Used to hold information about a real file on the filesystem,
    including references to its containing directory and (if it is
    itself a directory) any files and folders contained within it.
    """

    #Since we may be creating LOTS of these things (some mods have gajiblions of files), we'll define
    # __slots__ to keep the memory footprint as low as possible
    __slots__=("path", "lpath", "name", "parent", "isdir", "row", "_children", "_childnames", "_hidden", "_hasconflict")

    def __init__(self, path, name, parent=None, isdir=True, **kwargs):
        """

        :param str path: a relative path from an arbitray root to this file
        :param str name: the name that will displayed for this file; usually just the basename
        :param parent: this Item's parent, if any. will be None for top-level items
        :param bool isdir: Is this a directory? If not, it will be marked as never being able to hold children
        """
        # noinspection PyArgumentList
        super().__init__(**kwargs)
        self.path = path
        self.lpath = path.lower() # used to case-insensitively compare two FSItems
        self.name = name
        self.parent = parent

        self.isdir = isdir
        if self.isdir:
            self._children = []
            self._childnames = []
        else:
            self._children = None #type: list [FSItem]
            self._childnames = None

        self.row=0

        # as opposed to row, this is relative to the *entire* hierarchy
        # of files this fsitem belongs to; basically, this is the index
        # of this item in a flattened list of all files in the mod
        # self.index = index

        self._hidden = False

    @property
    def ppath(self):
        """The relative path of this item as a pathlib.Path object"""
        return Path(self.path)

    @property
    def hidden(self):
        """Return whether this item is marked as hidden"""
        return self._hidden

    @hidden.setter
    def hidden(self, value:bool):
        self._hidden = value

    @property
    def child_count(self):
        """Number of **direct** children"""
        return len(self._children) if self.isdir else 0

    def __getitem__(self, item):
        """
        Access children using list notation: ``thisitem[0]`` or
        ``thisitem["childfile.nif"]``. Returns ``None`` if given an invalid item
        number/name or childlist is ``None``.

        As a special case, if indexed w/ ``None``, returns itself.

        >>> this_item[None]
        this_item

        :param int|str|None item: if an ``int``, return the item at that
            row in this directory. if ``str``, return the child with
            that name in this directory. If ``None``, return self.
        """
        try:
            # assume `item` is an int
            return self._children[item]
        except TypeError:
            # bit of a hack: return self if indexed w/ ``None``
            if item is None:
                return self
            try:
                # assume `item` is the name of the file as a string
                return self._children[self._childnames.index(item)]
            except (ValueError, AttributeError):
                return None

    @property
    def row_path(self):
        """This is the 'how to get here from the root' path, using
        row-indices from the top-level on down:
            e.g. root[0][3][3][1][12]

            or, the 13th item in the 2nd directory of the 4th directory
            of the 4th directory of the 1st directory of the root item.
            """
        if self.parent.parent:
            return self.parent.row_path + [self.row]
        else:
            return [self.row]

    @property
    def children(self):
        """Returns a list of this item's direct children"""
        return self._children

    def iterchildren(self, recursive = False):
        """
        Obtain an iterator over this FSItem's children

        :param recursive: If False or omitted, yield only this item's
            direct children. If true, yield each child followed by that
            child's children, if any

        :rtype: __generator[FSItem|QFSItem, Any, None]
        """
        if recursive:
            for child in self._children:
                yield child
                if child.isdir:
                    yield from child.iterchildren(True)
        else:
            yield from self._children

    @staticmethod
    def build_filetree(root, file_tree, name_filter=None):
        """

        :param FSItem root: Root container item of the tree
        :param skymodman.utils.tree.AutoTree file_tree:
        :param (str)->bool name_filter: if given and not ``None``, each
            filename found will be passed to the `namefilter` callable.
            If the namefiter returns True, that file will NOT be added
            to the list of children
        :return: `root`
        """

        if name_filter is None:
            name_filter = lambda n: False

        root._build_tree(file_tree, name_filter)

        return root

    def _build_tree(self, file_tree, name_filter):
        row = count()
        # recurse=False; do it manually by passing child tree to child item
        for dirs, files in file_tree.walk(recurse=False):

            for d in dirs:
                if name_filter(d):
                    continue  # skip names that match filter

                # child=type(self)(path=join(self.path, d),
                #                  name=d,
                #                  parent=self,
                #                  isdir=True)

                child = type(self)(join(self.path, d), d, self, True)

                child._build_tree(file_tree[d], name_filter)
                child.row = next(row)

                self._children.append(child)
                self._childnames.append(child.name)

            for f in files:
                if name_filter(f):
                    continue

                child = type(self)(join(self.path, f),
                                   f,
                                   self,
                                   False)
                child.row = next(row)

                self._children.append(child)
                self._childnames.append(child.name)


    def __eq__(self, other):
        """Return true when these 2 items refer to the same relative path.
        Case insensitive. Used to determine file conflicts.

        :param FSItem other:
        """
        try:
            return self.lpath == other.lpath
        except AttributeError:
            # value was not a FSItem...maybe it's a string
            try:
                return self.lpath == other.lower()
            except AttributeError:
                # nope, not a string
                return NotImplemented

    def __lt__(self, value):
        """Compare this item's path to the path of the other item,
        case insensitively. Also works if `value` is a string."""
        try:
            return self.lpath < value.lpath
        except AttributeError:
            # value was not a FSItem...maybe it's a string
            try:
                return self.lpath < value.lower()
            except AttributeError:
                # nope, not a string
                return NotImplemented


    def __str__(self):
        return  "{0.__class__.__name__}(name: '{0.name}', " \
                "path: '{0.path}'," \
                "row: {0.row}, " \
                "isdir: {0.isdir}, " \
                "kids: {0.child_count}, " \
                "hidden: {0._hidden}" \
                ")".format(self)

    def __hash__(self):
        """Use the hash of this item's filepath as its hash value"""

        return hash(self.lpath)

    def print(self, file=None):
        """print a str repr of the fsitem

        use `file` to print to somewhere/something besides sys.stdout
        """

        lines= ("Name: %s " % self.name,
                  "  Path: %s" % self.path,
                  "  row: %d" % self.row,
                  "  kids: %d" % self.child_count,
                  "  hidden: %s" % self._hidden)

        if file is not None:
            for l in lines:
                print(l, file=file)
        else:
            for l in lines:
                print(l)

