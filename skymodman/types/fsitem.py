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
    # __slots__=("_path", "_lpath", "_name", "_parent", "_isdir", "_children", "_childnames", "_row", "_hidden", "_level", "_hasconflict")
    __slots__=("path", "lpath", "name", "parent", "isdir", "row", "index", "_children", "_childnames", "_hidden", "level", "_hasconflict")

    def __init__(self, path, name, parent=None, isdir=True, *, index=-1, **kwargs):
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
        self.index = index

        self._hidden = False

        self.level = len(self.ppath.parts)

    # @property
    # def path(self):
    #     """Relative path to this item from its containing mod-directory"""
    #     return self._path

    # @property
    # def lpath(self):
    #     """All-lowercase version of this item's relative path"""
    #     return self._lpath
    #
    # @property
    # def name(self):
    #     """Name of the file"""
    #     return self._name

    @property
    def ppath(self):
        """The relative path of this item as a pathlib.Path object"""
        return Path(self.path)

    # @property
    # def row(self):
    #     """Which row (relative to its parent) does this item appear on"""
    #     return self._row
    #
    # @row.setter
    # def row(self, value:int):
    #     self._row = value

    # @property
    # def level(self):
    #     """How deep is this item from the root"""
    #     return self._level
    #
    # @property
    # def isdir(self):
    #     """Whether this item represents a directory"""
    #     return self._isdir

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

    # @property
    # def parent(self):
    #     """Reference to the parent (containing directory) of this item,
    #     or None if this is the root item"""
    #     return self._parent

    def __getitem__(self, item):
        """
        Access children using list notation: thisitem[0] or
        thisitem["childfile.nif"] Returns none if given an invalid item
        number/name or childlist is None

        :param int|str item:
        """
        try:
            # assume `item` is an int
            return self._children[item]
        except TypeError:
            try:
                # assume `item` is the name of the file as a string
                return self._children[self._childnames.index(item)]
            except (ValueError, AttributeError):
                return None

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
        :param (str)->bool name_filter:
        :return:
        """

        # use class attribute on temporary class to statically track
        # items as they are added; each file-item (not dirs) will
        # have an 'index' attribute >=0.
        class indexer:
            i=0

        if name_filter is None:
            name_filter = lambda n: False

        root._build_children(file_tree, indexer, name_filter)

        return root

    def _build_children(self, file_tree, index, name_filter):
        """Build the fs-item tree from a tree of path names

        :param skymodman.utils.tree.AutoTree file_tree:
        :param index:
        """



        row=count()
        # recurse=False; do it manually by passing child tree to child item
        for dirs, files in file_tree.walk(recurse=False):

            for d in dirs:
                if name_filter(d):
                    continue # skip names that match filter

                # child=type(self)(path=join(self.path, d),
                #                  name=d,
                #                  parent=self,
                #                  isdir=True)

                child=type(self)(join(self.path, d), d, self, True)

                child.build_children(file_tree[d], index, name_filter)
                child.row = next(row)

                self._children.append(child)
                self._childnames.append(child.name)

            for f in files:
                if name_filter(f):
                    continue

                # child = type(self)(path=join(self.path, f),
                #                    name=f,
                #                    parent=self,
                #                    isdir=False,
                #                    index=index.i)
                child = type(self)(join(self.path, f),
                                   f,
                                   self,
                                   False,
                                   index=index.i)
                child.row=next(row)

                index.i+=1

                self._children.append(child)
                self._childnames.append(child.name)


    # #!!!!: This doc comment makes no freaking sense...absolute relative rel_root path name?? WHAT??
    # def load_children(self, rel_root, namefilter = None):
    #     """
    #     Given a root, construct an absolute path from that root and
    #     this item's (relative) path. Then scan that path for entries,
    #     creating an FSItem for each file found and adding it to this
    #     item's list of children. If the entry found is a directory, then
    #     call the load_children() method of the new FSItem with the same
    #     root given here.
    #
    #     :param str rel_root:
    #     :param (str)->bool namefilter: if given and not none, each
    #         filename found will be passed to the `namefilter` callable.
    #         If the namefiter returns True, that file will NOT be added
    #         to the list of children
    #     """
    #
    #     # :param conflicts: a collection of filepaths (all relative to a
    #     # mod's 'data' directory) that have been determined to exist in
    #     # multiple mods; if the name of a loaded file is in this
    #     # collection, it will be marked as "has_conflict"
    #
    #     rpath = Path(rel_root)
    #     path = rpath / self.path
    #
    #     nfilter = None
    #     if namefilter:
    #         nfilter = lambda p:not namefilter(p.name)
    #
    #     # sort by name
    #     entries = sorted(filter(nfilter, path.iterdir()),
    #                      key=lambda p:p.name)
    #
    #     for row,entry in enumerate(sorted(entries, key=lambda p:p.is_file())): #type: int, Path
    #         rel = str(entry.relative_to(rpath))
    #
    #         # using type(self) here to make sure we get an instance of
    #         # the subclass we're using instead of the base FSItem
    #         child = type(self)(path=rel, name=entry.name, parent=self, isdir=entry.is_dir())
    #         if entry.is_dir():
    #             child.load_children(rel_root, namefilter)
    #         child.row = row
    #         # if child.path in conflicts:
    #         #     child._hasconflict = True
    #         self._children.append(child)
    #         self._childnames.append(child.name)

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
                "level: {0.level}, " \
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
                  "  level: %d" % self.level,
                  "  kids: %d" % self.child_count,
                  "  hidden: %s" % self._hidden)

        if file is not None:
            for l in lines:
                print(l, file=file)
        else:
            for l in lines:
                print(l)

