from pathlib import PurePath, _PosixFlavour
from functools import lru_cache
# from enum import Enum

from skymodman.exceptions import Error
from skymodman.utils import singledispatch_m
from skymodman.utils.debug import Printer as PRINT

class FSError(Error):
    """ Represents some sort of error in the ArchiveFS """
    msg = "{path}"
    def __init__(self, path, message=None):
        if message is not None:
            self.msg = message
        self.path = path
    def __str__(self):
        return self.msg.format(path=self.path)

class Error_EEXIST(FSError):
    """ File Exists Error """
    msg="File exists: {path}"
class Error_ENOTDIR(FSError):
    """ Not a Directory """
    msg="Not a directory: {path}"
class Error_EISDIR(FSError):
    """ Is a directory """
    msg="Path '{path}' is a directory"
class Error_ENOTEMPTY(FSError):
    """ Directory not Empty """
    msg="Directory not empty: {path}"
class Error_ENOENT(FSError):
    """ No such File or Directory """
    msg="No such file or directory: {path}"
class Error_EIO(FSError):
    """ Input/Output Error (inode not found) """
    msg="I/O Error: bad inode {path}" # not actually a path in this case

class _CIFlavour(_PosixFlavour):
    """
    A path-flavour that is identical to PosixFlavour, but implements case-insensitive case folding.
    """
    def casefold(self, s):
        return s.lower()

    def casefold_parts(self, parts):
        return [p.lower() for p in parts]

_ci_flavour = _CIFlavour()

class PureCIPath(PurePath):
    """
    A case-insensitive version of PurePosixPath
    """
    _flavour = _ci_flavour
    __slots__ = ()

    @property
    def str(self):
        return str(self)

class CIPath(PureCIPath):
    __slots__ = ("_accessor", "_cache")

    FS=None # type: ArchiveFS

    def __new__(cls, *args, **kwargs):
        return cls._from_parts(args)

    def _init(self): # called from __new__
        # assert type(self).FS is not None, "No Filesystem"

        self._accessor = type(self).FS # type: ArchiveFS
        self._cache = {}

    ##===============================================
    ## stats & info
    ##===============================================

    @property
    def inode(self):
        try:
            return self._cache["inode"]
        except KeyError:
            value = self._cache["inode"] = self._accessor.inodeof(self)
            return value

    @property
    def is_dir(self):
        try:
            return self._cache["isdir"]
        except KeyError:
            value = self._cache["isdir"] = self._accessor.is_dir(self)
            return value

    @property
    def is_file(self):
        try:
            return not self._cache["isdir"]
        except KeyError:
            self._cache["isdir"] = self._accessor.is_dir(self)
            return not self._cache["isdir"]

    def exists(self):
        return self._accessor.exists(self)

    def dir_length(self):
        return self._accessor.dir_length(self)

    ##===============================================
    ## Stored Data Access
    ##===============================================

    @property
    def sparent(self):
        pp = PureCIPath(self)
        return self._accessor.storedpath(pp.parent)

    ##===============================================
    ## Directory listing/iteration
    ##===============================================

    def listdir(self):
        return self._accessor.listdir(self)

    def iterdir(self):
        yield from self._accessor.listdir(self)

    def itertree(self):
        yield from self._accessor.itertree(root=self, include_root=False)

    ##===============================================
    ## creation
    ##===============================================

    def touch(self):
        self._accessor.touch(self)

    def mkdir(self, exist_ok=False):
        self._accessor.mkdir(self, exist_ok)

    ##===============================================
    ## deletion
    ##===============================================

    def rm(self):
        self._accessor.rm(self)

    def rmdir(self):
        self._accessor.rmdir(self)

    ##===============================================
    ## path/name manipulation
    ##===============================================

    def move(self, destination, overwrite=False):
        self._accessor.move(self, destination, overwrite)

    def rename(self, destination, overwrite=False):
        self._accessor.rename(self, destination, overwrite)

    def chname(self, new_name, overwrite=False):
        self._accessor.chname(self, new_name, overwrite)

    def replace(self, destination):
        self._accessor.replace(self, destination)

    ##===============================================
    ## Comparison
    ##===============================================

    def __lt__(self, other):
        flags = self._accessor.sorting

        if not flags: return True

        val = super().__lt__(other)

        reverse = bool(flags & SortFlags.Descending)


        if val is not NotImplemented:
            if flags & SortFlags.DirsFirst and \
                (self.is_dir and not other.is_dir):
                    return not reverse
            elif flags & SortFlags.FilesFirst and \
                 (other.is_dir and not self.is_dir):
                    return not reverse

            if flags & SortFlags.Inode and self.inode < other.inode:
                    return not reverse

            if flags & SortFlags.NameCS:
                # only applies for siblings
                if self.sparent == other.sparent and self.name < other.name:
                    return not reverse

            if flags & SortFlags.Name and val:
                return not reverse

            return reverse

        return val


class SortFlags:
    NoSort      = 0x00
    Ascending   = 0x01
    Descending  = 0x02
    Name        = 0x04
    Inode       = 0x08
    DirsFirst   = 0x10
    FilesFirst  = 0x20
    CaseSensitive = 0x40

    # FilesFirst  = DirsFirst|Descending
    NameCS      = Name|CaseSensitive
    Default     = Name|DirsFirst|Ascending


def get_associated_pathtype(arcfs):

    class assoc_cipath(CIPath):
        FS = arcfs

    return assoc_cipath


class InodeRecord:

    # not supported?!
    __slots__ = ("parent", "name", "__inode")

    def __init__(self, name, inode, parent_inode, *args, **kwargs):
        """

        :param str name:
        :param int inode:
        :param int parent_inode:
        """
        # super().__init__(inode, *args, **kwargs)
        self.__inode = inode    # immutable
        self.name = name          # mutable
        self.parent = parent_inode  # mutable


    @property
    def inode(self):
        return self.__inode

    def __int__(self):
        return self.__inode
    def __index__(self):
        return self.__inode





class ArchiveFS:

    ROOT_INODE=0

    ## note: most operations will convert a 'path' argument (whether it's a string or some type of path object) into a PureCIPath before doing any operations. The Pure version of the CIPath is much lighter-weight and doesn't have a need for an associated filesystem, yet still compares equal with CIPaths that have the same "value" (path-string), and thus can be used for dict-lookups even when the actual key is technically a different type.  Only when a path is about to be entered into the class's storage tables is it converted to a concrete CIPath

    # noinspection PyUnresolvedReferences
    def __init__(self):
        # create a 'custom' subclass of CIPath that associates all its instances
        # with this particular ArchiveFS instance; allows having multiple active
        # arcfs' without complex systems to keep paths associated with the right one.
        self.CIPath = get_associated_pathtype(self)

        # list of paths, where an item's index in the list corresponds to its inode number.
        # self.i2p_table = [] # type: list[CIPath]
        # inode -> path
        self.inode_table = [] # type: list[InodeRecord]

        # mapping of filepaths to inodes
        ## FIXME: so...one of the fundamental building blocks of this class at the moment...is fundamentally broken. This abstraction was meant to prevent having to apply recursive or cascading changes to parent and child items in the tree on every change. However, because I store (absolute) path objects in the inode table and reference them everywhere, when, for example, a directory is moved to a new sub-directory, it's path gets updated to reflect the change...but all of its children's paths still show the old hierarchy. To fix that and still maintain this model, I'd have to do--cascading changes. Which defeats the entire point.
        ## XXX: I suppose the "best" thing to do in this situation is just to store file-names in the inode table rather than path objects; when a path is requested, the Path object will have to be generated dynamically by piecing together the calculated hierarchy. This method can probably be improved by using a cache of some sort; I'll just have to be careful to make sure the cache (or part of it) is marked invalid when a change occurs.
        # self.p2i_table = dict() # type: # dict[CIPath, int]
        # path -> inode

        # mapping of directory-inodes to set of inodes they contain
        self.directories = dict() # type: dict[int, set[int]]
        # inode -> {inode, ...}

        # create root of filesystem
        # self._root=self.CIPath("/")

        # only root should have its parent be the same as itself
        self._root=InodeRecord("/", 0, 0)
        self.inode_table.append(self._root)

        # self.i2p_table.append(self._root) # inode 0
        # self.p2i_table[self._root]=0
        self.directories[0]=set() # create empty set

        self.sorting=SortFlags.Default

    @property
    def root(self):
        return self._root

    ##=====================================================
    ## File Access/stats
    ##-----------------------------------------------------
    ## Below, we will often use a version of singledispatch
    ## that dispatches on the second argument (rather than
    ## the first, as the original function does) to allow
    ## it to work with instance methods.
    ##=====================================================

    # @singledispatch_m

    @lru_cache(256)
    def inodeof(self, path):

        parts = PureCIPath(path).parts

        assert parts[0]=="/", "Path must be absolute: {}".format(path)

        if len(parts)==1:
            return self.ROOT_INODE

        ir=self.root
        for p in parts[1:]:

            try:
                # `ir` is the parent of the current path part
                for i in self.dir_inodes(ir):
                    if self._inode_name_lower(i) == p.lower():
                        ir = self.inode_table[i]
                        break
                else:
                    raise Error_ENOENT(
                        PureCIPath(*parts[:parts.index(p) + 1])) from None
            except Error_EIO:
                raise Error_ENOENT(
                    PureCIPath(*parts[:parts.index(p) + 1])) from None

        return ir.inode

    @lru_cache(1024)
    def _inode_name(self, int_inode:int):
        try:
            return self.inode_table[int_inode].name
        except IndexError:
            raise Error_EIO(int_inode)

    @lru_cache(1024)
    def _inode_name_lower(self, inode:int):
        return self._inode_name(inode).lower()


    @lru_cache(256)
    def pathfor(self, inode:int):

        try:
            ir = self.inode_table[inode]
        except IndexError:
            raise Error_EIO(inode)

        path_parts = []

        while ir > 0:
            path_parts.append(ir.name)
            ir = self.inode_table[ir.parent]

        path_parts.append(self.root.name)

        return self.CIPath(*path_parts[::-1])

    def storedpath(self, path):
        """
        Return the version of `path` that is built from the inode-table
        """
        return self.pathfor(self.inodeof(path))

    @singledispatch_m
    def dir_inodes(self, directory):
        try:
            return self._dii(self.inodeof(directory))
        # could be raised from the exception handler in _dii
        except Error_EIO:
            # I'd consider this a more specific (or maybe less specific...
            # but certainly easier to understand) version of EIO
            raise Error_ENOENT(directory) from None

    @dir_inodes.register(int)
    def _dii(self, directory):
        try:
            return self.directories[directory]
        except KeyError:
            raise Error_ENOTDIR(self.pathfor(directory)) from None


    def dir_length(self, directory):
        """
        Returns the number of items contained by `directory`

        :param directory: Can be a string, a path, or the directory's inode number (int)
        :return: number of items contained by `directory`
        """
        # let the singledispatch mechanics take care of the type for directory
        return len(self.dir_inodes(directory))

    def listdir(self, directory):
        """
        List of names all items in `directory`
        :param directory:
        :return:
        """
        return [self._inode_name(i) for i in self.dir_inodes(directory)]

        # return [self.i2p_table[i] for i in self.dir_inodes(directory)]

    def iterdir(self, directory):
        """
        An unsorted iteration
        :param directory:
        :return:
        """
        yield from (self._inode_name(i) for i in self.dir_inodes(directory))

        # yield from (self.i2p_table[i] for i in self.dir_inodes(directory))

    def itertree(self, root="/", include_root=True):
        """
        Return a generator that recursively yields all paths under the specified directory 'root'. The only requirements for `root` are that it be an existing directory within the filesystem, though the method will not fail if a file-path is passed instead. If `include_root` is True, the rootpath itself will be the first item yielded by the generator; if False, the root will be not be included in the output and iteration will begin with the root's children.

        Directory entries are visited in a depth-first manner: the path of each entry is returned as soon as it is encountered; then, if the entry is a directory, the contents of the entry will be yielded (recursively), with iteration of the remaining children in the current directory resuming only once the full subtree for the entry has been returned.

        :param str|Path root:
        :param bool include_root:
        :return:
        """
        rootpath = PureCIPath(root)

        # if root was actually a file, just yield that file
        if not self.is_dir(rootpath):
            if include_root: yield self.storedpath(rootpath)
        else:

            def _iter(base):
                for c in self.iterdir(base):
                    yield c
                    if self.is_dir(c):
                        yield from _iter(c)

            if include_root: yield self.storedpath(rootpath)

            yield from _iter(rootpath)

    def itertree2(self, root="/", include_root=True):
        """
        Almost identical to itertree, but yields tuples with signature (int, PureCIPath, str). The first item is the depth (from root) of the yielded path, the second is the path object, and the third is a single character indicating the type of file the path refers to. For now, the only type-codes are:

            * d - Directory
            * f - File

        :param root:
        :param include_root:
        :return:
        """
        rootpath = PureCIPath(root)
        # if root was actually a file, just yield that file
        if not self.is_dir(rootpath):
            if include_root: yield (0, rootpath, "f")
        else:

            depth=0
            def _iter(base):
                nonlocal depth
                depth+=1
                for c in self.dir_inodes(base):
                    if self.is_dir(c):
                        yield (depth, self._inode_name(c), "d")
                        yield from _iter(c)
                    else:
                        yield (depth, self._inode_name(c), "f")
                depth-=1

            if include_root: yield (0, rootpath, "d")

            yield from _iter(self.inodeof(rootpath))

    @singledispatch_m
    def is_dir(self, path):
        """
        :param path:
        :return: True if `path` is a directory, False if `path` is a regular file
        """
        return self._idi(self.inodeof(path))

    @is_dir.register(int) # directly given inode
    def _idi(self, inode):
        """

        :param inode:
        :return: True if `inode` is the inode of a directory
        """
        return inode in self.directories

    @singledispatch_m
    def exists(self, path): # should catch str and other path-types
        try:
            # if it finds it...it's because it was findable
            self.inodeof(path)
            return True
        except Error_ENOENT:
            return False

    @exists.register(int) # for checking inodes
    def _ei(self, inode):
        return inode < len(self.inode_table) and self.inode_table[inode] is not None

        # return inode < len(self.i2p_table) and self.i2p_table[inode] is not None


    ##===============================================
    ## File Creation
    ##===============================================

    def touch(self, path, name=None):
        """
        Create a file.
        By default, any parents of `path` that do not exist will be created.

        :param name: if given, path is assumed to be the path to the directory that will contain the file named 'name'. If absent or None, `path` itself is considered to be the full path to the new file.
        """
        if name:
            fullpath = PureCIPath(path, name)
        else:
            fullpath = PureCIPath(path)

        try:
            self._create(fullpath)
        except Error_EEXIST:
            # touch doesn't fail on existing paths
            pass

    def mkdir(self, path, exist_ok=False):
        """
        By default, any parents of `path` that do not exist will be created.

        :param exist_ok: if True, an error will not be raised when the directory already exists
        """
        path = PureCIPath(path)

        try:
            inode = self._create(path)
            self.directories[inode] = set()
        except Error_EEXIST:
            if not exist_ok:
                raise

    def _create(self, path):
        """
        By default, any parents of `path` that do not exist will be created.
        :param path:
        :return:
        """

        if self.exists(path):
            # if path in self.p2i_table:
            raise Error_EEXIST(path.str)

        # new inode numbers are always == 1+current maximum inode.
        # since they start at 0, this is == the len of the table
        # new_inode = len(self.i2p_table)
        new_inode = len(self.inode_table)

        # append placeholder in case parent dirs have to be created
        # in getparentinode(),
        # so that they don't invalidate the above new_inode
        self.inode_table.append(None)
        par_inode = self._getparentinode(path)

        # insert into position saved earlier
        self.inode_table[new_inode] = InodeRecord(path.name, new_inode, par_inode)

        self._addtodir(new_inode, par_inode)

        return new_inode

    def _getparentinode(self, path):
        parent = path.parent
        try:
            return self.inodeof(parent)
        except Error_ENOENT:
            self.mkdir(parent) # recursive call
            return self.inodeof(parent)

    def _addtodir(self, inode:int, parent_inode:int):
        self.directories[parent_inode].add(inode)

    ##===============================================
    ## File Deletion
    ##===============================================

    def rm(self, path):
        """
        Delete a file path and null-out its inode-reference
        Use rmdir for directories.

        :param str|PurePath path:
        :return:
        """
        path = PureCIPath(path)

        if self.is_dir(path):
            raise Error_EISDIR(path)

        self._unlink(self.inodeof(path))

    def rmdir(self, dirpath):
        """
        Remove an empty directory. Raises Errors if `directory` is not empty or is not actually a directory
        :param str|PurePath dirpath:
        """

        dirpath = PureCIPath(dirpath)
        dirinode = self.inodeof(dirpath)

        assert dirpath != self.root, "No."

        if not self.is_dir(dirinode):
            raise Error_ENOTDIR(dirpath)

        if len(self.directories[dirinode]):
            raise Error_ENOTEMPTY(dirpath)

        self._del_dir(dirinode)

    def rmtree(self, directory:int):
        """
        Recursively remove a non-empty directory tree.
        :param str|PurePath directory:
        """
        directory = PureCIPath(directory)

        assert directory != self.root, "No. Stop that."

        dirinode = self.inodeof(directory)
        self._del_dir_tree(dirinode)

        # have to do a final removal of the dir from its parent-list
        # (since we skip that step in _del_dir_tree)
        self.dir_inodes(self.inode_table[dirinode].parent).remove(dirinode)

    def _del_dir(self, dirinode:int):
        """
        No checks, just does the job.
        :param int dirinode:
        """
        # remove it from directory table
        del self.directories[dirinode]

        # now delete it like any other file
        self._unlink(dirinode)

    def _del_dir_tree(self, dirinode:int):

        # will raise ENOTDIR if directory is not...a directory.
        for childnode in self.dir_inodes(dirinode):
            if not self.is_dir(childnode):
                # don't need to bother removing it from the directory's
                # node list since we're deleting the directory in just
                # a second anyway.
                self.inode_table[childnode] = None
            else:
                self._del_dir_tree(childnode)

        # remove the empty dir when it's all done
        del self.directories[dirinode]
        self.inode_table[dirinode]=None


    def _unlink(self, inode:int):
        """
        Instead of deleting the inode from the inode table,
        (thus changing the length of the list and messing up all our inodes),
        this replaces the index in the table with ``None``. Also removes
        the inode from its parent's list of child-inodes
        :param inode:
        :return:
        """
        inorec = self.inode_table[inode]
        # remove this node from its parent-directory's nodelist
        self.dir_inodes(inorec.parent).remove(inode)
        # and null out its entry in the inode table
        self.inode_table[inode] = None

    ##===============================================
    ## Name/Path Manipulation
    ##===============================================

    def move(self, path, destination, overwrite=False):
        """...
        Move the file or directory pointed to by `path` to `destination`.

        :param path:
        :param destination:
            If `destination` is an existing directory, `path` will become a child of `destination`. Otherwise, the filesystem path of the file-object `path` will be changed to `destination`.
        :param overwrite:
            If `destination` is an already-existing file and `overwrite` is False, a File-Exists error will be raised; if overwrite is True, `destination` will be deleted and replaced with `path`
        :return: True if all went well
        """

        PRINT() << "move(" << path << ", " << destination << ")"

        src = PureCIPath(path)
        dst = PureCIPath(destination)

        # if someone attempted to move an item to itself, just return
        if src == dst: return True

        # if the destination is an existing directory, move the source inside of it.
        if self.is_dir(dst):
            return self._move_to_dir(src, dst)

        # now we know dst is either a file or a non-existing path
        # so if it's a file, either delete it or raise an error
        self._check_collision(dst, overwrite)

        # and now we can be sure it doesn't exist! Muahahahaha...ha....oh

        # if destination path is in the same folder as the source,
        # this is just a name change
        if dst.parent == src.parent:
            return self._change_name(src, dst.name)

        # and if we made it here, we can finally just move src to dst
        return self._move_to_path(src, dst)

    def rename(self, path, destination, overwrite=False):
        """...
        Functions much like ``move``; the main difference is that, if the destination is a directory, instead of moving path inside that directory, an attempt will be made to overwrite it; if the destination directory is empty, this attempt will always succeed. If it is a file or non-empty directory, success depends on the value of `overwrite`.

        :param path: path being renamed
        :param destination: target path
        :param overwrite: If True, then an existing target will be unconditionally replaced--this means that, if the target is a non-empty directory, all contents of that directory tree will be removed.
        :return:
        """

        PRINT() << "rename(" << path << ", " << destination << ")"

        src = PureCIPath(path)
        dest = PureCIPath(destination)

        if src == dest:
            return True

        if self.is_dir(dest):
            try:  # if the directory is empty, this will succeed and
                # we can just rename the src
                self.rmdir(dest)
            except Error_ENOTEMPTY:
                if overwrite:
                    self.rmtree(dest)
                else:
                    raise

        else:  # file
            self._check_collision(dest, overwrite)

            if dest.parent == src.parent:
                return self._change_name(src, dest.name)

        return self._move_to_path(src, dest)

    def chname(self, path, new_name, overwrite=False):
        """...
        A simplified rename that just changes the file name (final path component) of `path` to `new_name`

        :param path:
        :param new_name:
        :return:
        """

        PRINT() << "chname(" << path << ", " << new_name << ")"

        src = PureCIPath(path)

        if new_name == src.name:
            return True

        dest = src.with_name(new_name)

        if self.exists(dest) and dest != src:
            if self.is_dir(dest):
                # only directories can replace other directories
                if self.is_dir(src):
                    # cannot use this method to overwrite non-empty directories
                    self.rmdir(dest)  # just let the error propagate
                else:
                    e = Error_ENOTDIR(src)
                    e.msg = "Will not overwrite directory '{dest}' with non-directory '{path}'".format(
                        dest=dest)
                    raise e
            # dest is file:
            else:
                self._check_collision(dest, overwrite)

        # at this point, we should be able to guarantee that either
        #   a) dest does not exist (or has been removed), or
        #   b) dest technically exists, but only because its filename matches
        #       that of src when compared case-insensitively; we ensured above
        #       that new_name != src.name (a case-sensitive comparison), so the
        #       user simply wants to change the displayed case of the filename
        #
        #   In either case (hah!), it should be safe to just do:
        self._change_name(src, new_name)

    def replace(self, path, destination):
        """

        :param path:
        :param destination: If exists, will be unconditionally replaced; if it is a directory all its contents will be removed
        :return:
        """
        self.rename(path, destination, True)

    def _change_inode_path(self, inode, new_path):
        PRINT() << "_change_inode_path(" << inode << ", " << new_path << ")"

        inorec = self.inode_table[inode]

        # remove from old dir
        self.directories[inorec.parent].remove(inorec)

        # change name and parent
        inorec.name = new_path.name
        inorec.parent = self.inodeof(new_path.parent)

        # add to new dir
        self.directories[inorec.parent].add(inorec)


    def _move_to_dir(self, path, dest_dir):
        """
        Move file or dir `path` inside directory `dest_dir`
        """

        PRINT() << "_move_to_dir(" << path << ", " << dest_dir << ")"

        dest_path = self.storedpath(dest_dir) / path.name # keep same name

        # if someone attempted to move an item inside its own parent, just return
        if dest_path == path: return True

        return self._move(path, dest_path)

    def _move_to_path(self, src, dest):
        """
        inode.path -> new_path
        """
        # use storedpath() instead of just dest to preserve existing case
        PRINT() << "_move_to_path(" << src << ", " << dest << ")"

        return self._move(src, self.storedpath(dest.parent) / dest.name)

    def _move(self, from_path, to_path):
        """
        Perform the final move of `from_path` to destination `to_path`
        """

        PRINT() << "_move(" << from_path << ", " << to_path << ")"

        inode = self.inodeof(from_path)           # get inode from current path value
        self._change_inode_path(inode, to_path)   # update the inode table
        return True

    def _change_name(self, path, new_name):
        """
        Just change the name of the file or directory pointed to by path
        (Slightly simpler version of _change_inode_path())

        :param path:
        :param str new_name:
        """
        self.inode_table[self.inodeof(path)].name = new_name
        return True

    def _check_collision(self, target, overwrite):
        """...
        If the file `target` exists and overwrite is True, `target` will be deleted. If `target` exists and `overwrite` is False, raise Error_EEXIST. If `target` does not exist, do nothing.

        :param target: must not be a directory
        :param overwrite:
        :return:
        """
        if self.exists(target):

            if overwrite: self.rm(target)

            else: raise Error_EEXIST(target.str)

    # todo: copy and copytree (maybe...since our 'files' are really just names and contain no data, a 'copy' operation may be unnecessary)

    ##===============================================
    ## Misc
    ##===============================================

    def mksubfs(self, from_path):
        """
        Initialize a new ArchiveFS from a sub-directory in this one.
        :param from_path: The path in this fs that will become the root of the new fs.
        """
        subfs = type(self)()
        from_path = PureCIPath(from_path)

        for p in self.itertree(from_path, False):
            rel_path = p.relative_to(from_path)
            if self.is_dir(p):
                # re-root
                subfs.mkdir("/" / rel_path)
            else:
                subfs.touch("/" / rel_path)

        return subfs

    def mkdupefs(self):
        """
        Create and return an exact duplicate of this filesystem
        """
        import copy
        dupefs = type(self)()

        dupefs.inode_table = copy.deepcopy(self.inode_table)

        # directories just contains ints
        dupefs.directories = copy.deepcopy(self.directories)

        del copy
        return dupefs

        # have to make sure the paths in the inode-table are of the correct type
        # dupefs.i2p_table = [dupefs.CIPath(p) if p is not None else p for p in self.i2p_table]
            # copy.deepcopy(self.i2p_table)
        # for i,p in enumerate(dupefs.i2p_table):
        #     if p is not None:
        #         dupefs.p2i_table[p]=i


        # for p in self.itertree("/", False):
        #     if self.is_dir(p):
        #         dupefs.mkdir(p)
        #     else:
        #         dupefs.touch(p)



    def fsck(self, root="/"):
        return fsck_modfs(self, root)

    def fsck_quick(self, root="/"):
        return fsck_modfs_quick(self, root)


def fsck_modfs(modfs, root="/"):
    """
    Check if the pseudo-filesystem represented by `modfs` contains recognized game-data on its top level.
    :param arcfs.ArchiveFS modfs:
    :return: 3-tuple:
        (number_of_recognized_valid_toplevel_items,
         dict_of_that_data_and_other_stuff,
         directory_which_contains_the_game_data),

         where the last item may not be the same as the original root of `modfs`. (It will only be different if the only item in root was a directory that held all the actual data, i.e. should have just been the root directory in the first place.)
    """
    from skymodman.constants import TopLevelDirs_Bain, \
        TopLevelSuffixes
    import re

    mod_data = {
        "folders":   [],
        "files":     [],
        "docs":      [],
        # some mods have a fomod dir that just contains information
        # about the mod, with no config script
        "fomod_dir": None
    }
    doc_match = re.compile(r'(read.?me|doc(s|umentation)|info)',
                           re.IGNORECASE)

    for topitem in modfs.iterdir(root):
        if modfs.is_dir(
                topitem) and topitem.name.lower() in TopLevelDirs_Bain:
            mod_data["folders"].append(topitem)

        elif topitem.suffix.lower().lstrip(".") in TopLevelSuffixes:
            mod_data["files"].append(topitem)

        elif doc_match.search(topitem):
            mod_data["docs"].append(topitem)

    # one last check if the previous searches turned up nothing:
    # if there is only one item on the top level
    # of the mod and that item is a directory, then check inside that
    # directory for the necessary files.
    if not (mod_data["folders"] and mod_data["files"]):
        _list = modfs.listdir(root)
        if len(_list) == 1 and modfs.is_dir(_list[0]):
            return fsck_modfs(modfs, _list[0])

    return len(mod_data["folders"]) + len(
        mod_data["files"]), mod_data, root

def fsck_modfs_quick(modfs, root="/"):
    """
    This simply returns True upon finding the first viable game-data item on the root level (or False if none is found)
    :param root:
    """
    from skymodman.constants import TopLevelDirs_Bain, \
        TopLevelSuffixes

    for topitem in modfs.iterdir(root):
        if (modfs.is_dir(topitem)
            and topitem.name.lower() in TopLevelDirs_Bain) or \
                (topitem.suffix.lower().lstrip(
                    ".") in TopLevelSuffixes):
            return True

    return False


def __test1():
    cip = PureCIPath("test", "rest")
    CIP = PureCIPath("TEST", "REST")
    Cip = PureCIPath("Test", "Rest")

    print(cip, CIP, Cip, sep="\n")

    print(cip == CIP)
    print(Cip == CIP)
    print(Cip == cip)

    pathlist = [cip, PureCIPath("not", "the", "same")]
    print(CIP in pathlist)

    pathdict = {Cip: "hello"}

    print (pathdict[cip])



if __name__ == '__main__':
    # from skymodman.managers.archive_7z import ArchiveHandler
    __test1()