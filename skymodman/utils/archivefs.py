from pathlib import PurePath, _PosixFlavour
# from enum import Enum

from skymodman.exceptions import Error
from skymodman.utils import singledispatch_m

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

        if cls.FS is None:
            # if no fs, return PureCIPath
            return PureCIPath._from_parts(args, init=False)

        return cls._from_parts(args)
        # self._init()
        # return self

    def _init(self): # called from __new__
        self._accessor = self.FS # type: ArchiveFS
        self._cache = {}

    # @classmethod
    # def _from_parsed_parts(cls, drv, root, parts, init=True):
    #     self = super()._from_parsed_parts(drv, root, parts, init=False)
    #     if init:
    #         self._init(self._accessor)
    #     return self


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
                # results.append(self.is_dir and not other.is_dir)
            elif flags & SortFlags.FilesFirst and \
                 (other.is_dir and not self.is_dir):
                    return not reverse

            if flags & SortFlags.Inode and self.inode < other.inode:
                    return not reverse

            if flags & SortFlags.NameCS:
                # only applies for siblings
                if self.parent == other.parent and self.name < other.name:
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


class ArchiveFS:

    ROOT_INODE=0

    # noinspection PyUnresolvedReferences
    def __init__(self):
        # Associate CIPath objects with this filesystem (...i hope this works)
        CIPath.FS = self
        # list of paths, where an item's index in the list corresponds to its inode number.
        self.i2p_table = [] # type: list[CIPath]
        # self.inodePathTable = []
        # inode -> path

        # mapping of filepaths to inodes
        self.p2i_table = dict() # type: dict[CIPath, int]
        # self.pathInodeTable = dict()
        # path -> inode

        # mapping of directory-inodes to set of inodes they contain
        self.directories = dict() # type: dict[int, set[int]]
        # inode -> {inode, ...}

        # mapping of inodes to a CIFile instance describing the current state of a file representing that inode
        # self.file_table = {} # inode -> CIFile

        # create root of filesystem
        self._root=CIPath("/")
        self.i2p_table.append(self._root) # inode 0
        self.p2i_table[self._root]=0
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

    @singledispatch_m
    def inodeof(self, path):
        return self._ino(PureCIPath(path))

    @inodeof.register(PureCIPath)
    def _ino(self, path):
        try:
            return self.p2i_table[path]
        except KeyError:
            raise Error_ENOENT(path.str) from None

    def pathfor(self, inode):
        try:
            return self.i2p_table[inode]
        except IndexError:
            raise Error_EIO(inode)

    def storedpath(self, path):
        """
        Return the version of `path` that is stored in the inode-table
        """
        return self.i2p_table[self.p2i_table[path]]

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
        List of all items in a directory, sorted according to self.sorting
        :param directory:
        :return:
        """
        return [self.i2p_table[i] for i in self.dir_inodes(directory)]
        # return self._sort([self.i2p_table[i] for i in self.dir_inodes(directory)])

    def iterdir(self, directory):
        """
        An unsorted iteration
        :param directory:
        :return:
        """
        #            inode -> path
        yield from (self.i2p_table[i] for i in self.dir_inodes(directory))

    def itertree(self, root="/", include_root=True):
        """
        Return a generator that recursively yields all paths under the specified directory 'root'. The only requirements for `root` are that it be an existing directory within the filesystem, though the method will not fail if a file-path is passed instead. If `include_root` is True, the rootpath itself will be the first item yielded by the generator; if False, the root will be not be included in the output and iteration will begin with the root's children.

        Directory entries are visited in a depth-first manner: the path of each entry is returned as soon as it is encountered; then, if the entry is a directory, the contents of the entry will be yielded (recursively), with iteration of the remaining children in the current directory resuming only once the full subtree for the entry has been returned.

        :param str|Path root:
        :param bool include_root:
        :return:
        """
        rootpath = PureCIPath(root)
        # if isinstance(root, PureCIPath):
        #     rootpath = root
        # else:
        #     rootpath = PureCIPath(root)

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
                for c in self.iterdir(base):
                    if self.is_dir(c):
                        yield (depth, c, "d")
                        yield from _iter(c)
                    else:
                        yield (depth, c, "f")
                depth-=1

            if include_root: yield (0, rootpath, "d")

            yield from _iter(rootpath)

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
        return self._ep(PureCIPath(path))

    @exists.register(PureCIPath)
    def _ep(self, path):
        return path in self.p2i_table

    @exists.register(int) # for checking inodes
    def _ei(self, inode):
        return inode < len(self.i2p_table) and self.i2p_table[inode] is not None


    # def _sort_key(self, filelist, flags=None):
    #     """
    #
    #     :param list filelist: a list of paths corresponding to files in a common directory
    #     :param flags: If None, use current FS.sorting
    #     :return:
    #     """
    #     if flags is None:
    #         flags = self.sorting
    #     if not flags:
    #         return filelist
    #
    #     # lt_checks=[]
    #     sort_key = lambda: ""
    #     key_parts=[]
    #
    #     if flags & SortFlags.DirsFirst:
    #         # want this to return 0 if true
    #         key_parts.append(lambda p: int(not self.is_dir(p)))
    #         # lt_checks.append(lambda x,y: self.is_dir(x) and not self.is_dir(y))
    #     elif flags & SortFlags.FilesFirst:
    #         key_parts.append(lambda p: int(self.is_dir(p)))
    #         # lt_checks.append(lambda x, y: self.is_dir(y) and not self.is_dir(x))
    #
    #     if flags & SortFlags.Inode:
    #         key_parts.append(lambda p: self.inodeof(p))
    #
    #         # lt_checks.append(lambda x, y: self.inodeof(x) < self.inodeof(y))
    #     elif flags & SortFlags.Name:
    #         key_parts.append(lambda p: p.name.lower())
    #
    #         # lt_checks.append(PureCIPath.__lt__)
    #     elif flags & SortFlags.NameCS:
    #         key_parts.append(lambda p: p.name)
    #
    #         # lt_checks.append(lambda x, y: x.name < y.name)
    #
    #
    #
    #
    #
    #     old_lt = PureCIPath.__lt__
    #
    #     PureCIPath.__lt__ = lambda x,y: any(lt(x,y) for lt in lt_checks)
    #     rev = flags & SortFlags.Descending
    #
    #     filelist.sort(reverse=rev)
    #
    #     PureCIPath.__lt__ = old_lt
    #     return filelist
    #
    #     # filelist[:] = sorted(filelist, key=lambda x: sum([-1 if lt(x) else 1 for lt in lt_checks]))






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
            fullpath = CIPath(path, name)
        elif not isinstance(path, CIPath):
            fullpath = CIPath(path)
        else:
            fullpath = path

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
        if not isinstance(path, CIPath):
            path = CIPath(path)

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

        if path in self.p2i_table:
            raise Error_EEXIST(path.str) from None

        new_inode = len(self.i2p_table)
        self.i2p_table.append(path)
        self.p2i_table[path] = new_inode

        self._add_to_parent_dir(path)

        return new_inode

    def _add_to_parent_dir(self, path):
        inode=self.inodeof(path)
        try:
            self.dir_inodes(path.parent).add(inode)
        except Error_ENOENT:
            self.mkdir(path.parent) # starts recursion to create lowest-nonexisting parent and propagate back up
            self.dir_inodes(path.parent).add(inode)

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
        if not isinstance(path, PureCIPath):
            path = PureCIPath(path)

        if self.is_dir(path):
            raise Error_EISDIR(path.str)

        self._delfile(path)

    def rmdir(self, dirpath):
        """
        Remove an empty directory. Raises Errors if `directory` is not empty or is not actually a directory
        :param str|PurePath dirpath:
        """

        if not isinstance(dirpath, PureCIPath):
            dirpath = PureCIPath(dirpath)

        assert dirpath != self.root, "No."

        if not self.is_dir(dirpath):
            raise Error_ENOTDIR(dirpath.str)

        if len(self.dir_inodes(dirpath)):
            raise Error_ENOTEMPTY(dirpath.str)

        # remove it from directory table
        del self.directories[self.inodeof(dirpath)]

        # now delete it like any other file
        self._delfile(dirpath)

    def rmtree(self, directory):
        """
        Recursively remove a non-empty directory tree.
        :param str|PurePath directory:
        """
        if not isinstance(directory, PureCIPath):
            directory = PureCIPath(directory)

        assert directory != self.root, "No. Stop that."

        # iterdir will raise ENOTDIR if directory is not...a directory.
        for child in self.iterdir(directory):
            try:
                # remove if file
                self.rm(child)
            except Error_EISDIR:
                # or remove the child tree if dir
                self.rmtree(child)

        # remove the empty dir when it's all done
        self.rmdir(directory)

    def _unlink(self, inode):
        """
        This does not delete the inode from the inode table,
        (thus changing the length of the list and messing up all our inodes),
        it replaces the path with ``None``.
        :param inode:
        :return:
        """
        self.i2p_table[inode] = None

    def _delfile(self, path):
        inode = self.p2i_table.pop(path)
        self.dir_inodes(path.parent).remove(inode)
        self._unlink(inode)

    ##===============================================
    ## Name/Path Manipulation
    ##===============================================

    def move(self, path, destination, overwrite=False):
        """
        Move the file or directory pointed to by `path` to `destination`.

        :param path:
        :param destination:
            If `destination` is an existing directory, `path` will become a child of `destination`. Otherwise, the filesystem path of the file-object `path` will be changed to `destination`.
        :param overwrite:
            If `destination` is an already-existing file and `overwrite` is False, a File-Exists error will be raised; if overwrite is True, `destination` will be deleted and replaced with `path`
        :return: True if all went well
        """
        src = CIPath(path) if not isinstance(path, CIPath) else path
        dst = CIPath(path) if not isinstance(destination, CIPath) else destination

        # if someone attempted to move an item to itself, just return
        if src == dst: return True

        # if the destination is an existing directory, move the source inside of it.
        if self.is_dir(dst):
            return self._move_to_dir(src, dst)

        # now we know dst is either a file or a non-existing path
        # so if it's a file, either delete it or raise an error
        self._check_collision(dst, overwrite)

        # and now we can be sure it doesn't exist! Muahahahaha...ha....oh

        # if destination path is in the same folder as the source, this is just a name change
        if dst.parent == src.parent:
            return self._change_name(src, dst.name)

        # and if we made it here, we can finally just move src to dst
        return self._move_to_path(src, dst)

    def rename(self, path, destination, overwrite=False):
        """
        Functions much like ``move``; the main difference is that, if the destination is a directory, instead of moving path inside that directory, an attempt will be made to overwrite it; if the destination directory is empty, this attempt will always succeed. If it is a file or non-empty directory, success depends on the value of `overwrite`.

        :param path: path being renamed
        :param destination: target path
        :param overwrite: If True, then an existing target will be unconditionally replaced--this means that, if the target is a non-empty directory, all contents of that directory tree will be removed.
        :return:
        """
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
        """
        A simplified rename that just changes the file name (final path component) of `path` to `new_name`

        :param path:
        :param new_name:
        :return:
        """

        src = path
        if not isinstance(path, CIPath):
            src = CIPath(path)

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
        self._chname(src, dest)

    def replace(self, path, destination):
        """

        :param path:
        :param destination: If exists, will be unconditionally replaced; if it is a directory all its contents will be removed
        :return:
        """
        self.rename(path, destination, True)

    def _change_inode_path(self, inode, new_path):
        old_path = self.i2p_table[inode]

        assert new_path != old_path

        self.i2p_table[inode] = new_path
        self.p2i_table[new_path] = inode
        del self.p2i_table[old_path]

    def _swap_inode_dir(self, inode, dir1, dir2):
        """
        "Swap" the given inode number from the directory-inode set of `dir1` to that of `dir2`

        :param int inode:
        :param PureCIPath dir1:
        :param PureCIPath dir2:
        """
        self.dir_inodes(dir1).remove(inode)
        self.dir_inodes(dir2).add(inode)

    def _move_to_dir(self, path, dest_dir):
        """
        Move file or dir `path` inside directory `dest_dir`
        """

        # use inodeof() to preserve existing case
        dest_path = self.storedpath(dest_dir) / path.name # keep same name

        # if someone attempted to move an item inside its own parent, just return
        if dest_path == path: return True

        return self._move(path, dest_path)

    def _move_to_path(self, src, dest):
        """
        inode.path -> new_path
        """
        # use storedpath() instead of just dest to preserve existing case
        return self._move(src, self.storedpath(dest.parent) / dest.name)

    def _move(self, from_path, to_path):
        """
        Perform the final move of `from_path` to destination `to_path`
        """
        inode = self.inodeof(from_path)                     # get inode from current path value
        self._swap_inode_dir(inode, from_path.parent,       # remove inode from old directory, add to new
                             to_path.parent)
        self._change_inode_path(inode, to_path)             # update the path and inode tables
        return True

    def _change_name(self, path, new_name):
        """
        Just change the name of the file or directory pointed to by path
        (Slightly simpler version of _change_inode_path())

        :param path:
        :param str new_name:
        :return:
        """
        # if dest.parent == src.parent:
        #     # just moving to a new name in the same directory;
        #     # only need to change the file name. Use dest.name
        #     # instead of just putting dest in src's place so that
        #     # the case of the names of any parents remains consistent.
        #     self._change_name(src, dest.name)
        #     return True

        return self._chname(path, path.with_name(new_name))

    def _chname(self, orig_path, renamed_path):
        """
        Assumes `orig_path` and `renamed_path` are in the same folder,
        so skips the directory-inode rearrangement.
        """
        inode = self.inodeof(orig_path)         # get inode
        self.i2p_table[inode] = renamed_path    # update inode->path table

        del self.p2i_table[orig_path]           # del old path from path->inode table
        self.p2i_table[renamed_path] = inode    # add new path to path->inode table
        return True

    def _check_collision(self, target, overwrite):
        """
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

        dupefs.i2p_table = copy.deepcopy(self.i2p_table)
        for i,p in enumerate(dupefs.i2p_table):
            if p is not None:
                dupefs.p2i_table[p]=i
        dupefs.directories = copy.deepcopy(self.directories)

        del copy

        # for p in self.itertree("/", False):
        #     if self.is_dir(p):
        #         dupefs.mkdir(p)
        #     else:
        #         dupefs.touch(p)

        return dupefs

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


# fileinfo = namedtuple("fileinfo", "inode is_dir is_file path name")

# class CIFile:
#     __slots__= "inode", "parent_inode", "is_dir", "is_file", "name"
#
#     def __init__(self, inode, parent_inode, is_dir, name):
#         self.name=name
#         self.inode=inode
#         self.parent_inode = parent_inode
#
#         # for now, this is a binary relationship
#         self.is_dir=is_dir
#         self.is_file= not is_dir




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