from pathlib import PurePath, _PosixFlavour
from collections import namedtuple
# from functools import lru_cache
# from enum import Enum

from skymodman.exceptions import Error
from skymodman.utils import singledispatch_m
from skymodman.utils.debug import Printer as PRINT
from skymodman.constants import TopLevelDirs_Bain, \
    TopLevelSuffixes, OverwriteMode

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

cistat = namedtuple("cistat", "st_type st_ino st_name")
# noinspection PyUnresolvedReferences
cistat.__doc__ = "A simplified version of os.stat_result, this contains the fields `st_type` for file type, `st_ino` for inode number, and `st_name` for current file name."

class CIPath(PureCIPath):
    __slots__ = ("_accessor", "_isdir")

    FS=None # type: ArchiveFS

    def __new__(cls, *args, **kwargs):
        return cls._from_parts(args)

    def _init(self): # called from __new__

        self._accessor = type(self).FS # type: ArchiveFS

    ##===============================================
    ## stats & info
    ##===============================================

    @property
    def inode(self):
        """
        :return: the inode number of this item
        """
        # values are cached in fs now, so may not need individual cache
        return self._accessor.inodeof(self)

    @property
    def is_dir(self):
        """
        :return: True if this path resolves to a directory
        """
        # don't look this up until needed, then cache the result
        try:
            return self._isdir
        except AttributeError:
            self._isdir = self._accessor.is_dir(self)
            return self._isdir

    @property
    def is_file(self):
        """
        :return: True if this path resolves to a file
        """
        try:
            return not self._isdir
        except AttributeError:
            self._isdir = self._accessor.is_dir(self)
            return not self._isdir

    def exists(self):
        """
        :return: True if this path exists in the filesystem
        """
        return self._accessor.exists(self)

    def dir_length(self):
        """
        :return: number of items in the directory specified by this path
        """
        return self._accessor.dir_length(self)

    def __len__(self):
        """
        :return: number of items in the directory specified by this path
        """
        return self._accessor.dir_length(self)

    @property
    def has_children(self):
        """
        :return: True if this path resolves to a non-empty directory
        """
        if self.is_dir:
            return self._accessor.dir_length(self) > 0
        return False

    @property
    def is_empty(self):
        """
        :return: True if this path resolves to an empty directory
        """
        #FIXME: this will return true for all files as well as empty directories;
        # should maybe throw an exception if this is not a directory
        return not self.has_children

    ##===============================================
    ## Stored Data Access
    ##===============================================

    @property
    def sparent(self):
        """
        :return: the path to this item's parent as it appears in the inode table (with regards to case and associated filesystem)
        """
        pp = PureCIPath(self)
        return self._accessor.get_path(pp.parent)

    def __contains__(self, file):
        """
        Assuming that this CIPath object is a directory, return True if `file` is contained within.  If this is not a directory--or `file` isn't a Path object, string, or inode number--an appropriate exception will be raised.

        :param str|CIPath|int file: Must be the inode number of an existing file, or the absolute path (either in string form or object form) to a file.
        """
        try:
            # assuming `file` is another CIPath obj
            return file.inode in self._accessor.dir_inodes(self)
        except AttributeError:
            # "file has no attr 'inode'"
            try:
                # assume `file` is actually an inode number (but int() it to be sure)
                return int(file) in self._accessor.dir_inodes(self)
            except (ValueError, TypeError):
                # file wasn't a number, either; could be different type of Path, or a string?
                return self._accessor.inodeof(file) in self._accessor.dir_inodes(self)

        # and if all of that still failed, then we definitely just need
        # to let the exception raise.


    ##===============================================
    ## Directory listing/iteration
    ##===============================================

    def ls(self, verbose=False, conv=None):
        """
        Return an unordered list of the names of files contained by this directory.

        :param verbose: If `verbose` is True, instead return an unordered list of ``cistat`` objects for files within this directory

        :param conv: If given, `conv` must be a callable that takes a single string (in this case, the filename of a directory entry), performs some conversion, and returns the modified string. The converted filenames will be returned in place of the originals.

        """
        return self._accessor.ls(self, verbose, conv)

    def listdir(self):
        """
        Return an unordered list of CIPath objects for the files within this directory
        """
        return self._accessor.listdir(self)

    def iterls(self, verbose=False):
        """
        Iterate over the names of files (in no particular order) contained by this directory.

        :param verbose: If `verbose` is True, instead iterate over ``cistat`` objects for files within this directory
        :yield: str | cistat
        """
        # uses 'ls' instead of 'iterls' to take advantage of caching.
        yield from self._accessor.ls(self, verbose)

    def iterdir(self):
        """
        Iterate over this directory's contents as CIPath objects
        """
        yield from self._accessor.iterdir(self)

    def lstree(self, verbose=False):
        """
        Generator; like a recursive ls(); `verbose` returns cistat objects instead of just names
        """
        yield from self._accessor.lstree(root=self,
                                           include_root=False,
                                           verbose=verbose)

    def itertree(self, verbose=False):
        """
        Recursively yield full paths for all items under this directory
        :param verbose:
        :return:
        """
        yield from self._accessor.itertree(str(self),
                                                include_root=False,
                                                verbose=verbose)

    ##===============================================
    ## creation
    ##===============================================

    def touch(self):
        """
        If this path does not exist, create it as a file. Any leading parent directories will also be created as needed.

        If the path does exist, this method does nothing.
        """
        self._accessor.touch(self)

    def mkdir(self, exist_ok=False):
        """
        If this path does not exist, create it as a directory, including any required parent directories.

        :param exist_ok: If True, do not throw an error if the directory already exists. Default False.
        """
        self._accessor.mkdir(self, exist_ok)

    ##===============================================
    ## deletion
    ##===============================================

    def rm(self):
        """
        If this is a file, delete it from the filesystem.
        :return:
        """
        self._accessor.rm(self)

    def rmdir(self):
        """
        If this is an EMPTY directory, remove it from the filesystem. An exception will be raised if it is not empty.
        """
        self._accessor.rmdir(self)

    ##===============================================
    ## path/name manipulation
    ##===============================================

    def move(self, destination, overwrite=OverwriteMode.PROMPT):
        """
        Move this item from its current path to a new location

        :param destination: New path or containing directory for the file
        :param overwrite: How to react if the destination already exists
        """
        self._accessor.move(self, destination, overwrite)

    def rename(self, destination, overwrite=OverwriteMode.PROMPT):
        """
        Change the path of this item; unlike ``move``, passing an existing directory as `destination` will attempt to remove/overwrite that directory rather than adding the item as a child.

        :param destination: New path for the item.
        :param overwrite: How to react if the destination already exists
        """
        self._accessor.rename(self, destination, overwrite)

    def chname(self, new_name, overwrite=OverwriteMode.PROMPT):
        """
        Like rename, but only change the basename (final path component) of this item.

        :param new_name: new base name for the item.
        :param overwrite: How to react if the destination already exists
        """
        self._accessor.chname(self, new_name, overwrite)

    def replace(self, destination):
        """
        Unconditionally move this item to a new location, removing the destination (and all of its contents) if it already exists.

        :param destination: New path for the item.
        """
        self._accessor.replace(self, destination)

    ##===============================================
    ## Comparison
    ##===============================================

    def __lt__(self, other):
        flags = self._accessor.sorting

        if not flags: return True

        # can't use super() here because it fails when self isn't the
        # same flavor of CIPath that the referenced __lt__ belongs to
        # (this came up in _FakeCIPath in archivefs_treemodel)
        val = PureCIPath.__lt__(self, other)

        reverse = bool(flags & SortFlags.Descending)


        if val is not NotImplemented:
            if flags & SortFlags.DirsFirst and \
                (self.is_dir and not other.is_dir):
                    return not reverse
            elif flags & SortFlags.FilesFirst and \
                 (other.is_dir and not self.is_dir):
                    return not reverse

            # if flags & SortFlags.Inode and self.inode < other.inode:
            #         return not reverse

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

    __slots__ = ("parent", "name", "__inode")

    def __init__(self, name, inode, parent_inode):
        """

        :param str name:
        :param int inode:
        :param int parent_inode:
        """
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
    def __lt__(self, other):
        # Despite having a 'name' attribute, these should always be ordered
        # by the value of their main inode
        if not hasattr(other, "__int__"):
            return NotImplemented
        return self.__inode < int(other)


class ArchiveFS:

    ROOT_INODE=0

    def __init__(self):

        # create a 'custom' subclass of CIPath that associates all its instances
        # with this particular ArchiveFS instance; allows having multiple active
        # arcfs' without complex systems to keep paths associated with the right one.
        self.CIPath = get_associated_pathtype(self)

        # list of paths, where an item's index in the list corresponds to its inode number.
        self.inode_table = []
        """:type: list[InodeRecord|None]"""

        # mapping of directory-inodes to set of inodes they contain
        self.directories = dict() # type: dict [int, set [int]]
        # inode -> {inode, ...}

        # create root of filesystem
        # only root should have its parent be the same as itself
        self._root=InodeRecord("/", 0, 0)
        self._rootpath = self.CIPath(self._root.name)
        self.inode_table.append(self._root)

        self.directories[0]=set() # create empty set

        self.sorting=SortFlags.Default

        # initialize caches with root information
        self.caches = {
            "inodeof":           {self._rootpath: self.ROOT_INODE},
            "_inode_name":       {self.ROOT_INODE: "/"},
            "_inode_name_lower": {self.ROOT_INODE: "/"},
            "pathfor":           {self.ROOT_INODE: self._rootpath},
            "listdir":           {self.ROOT_INODE: []},
            # verbose version of listdir:
            "vlistdir":          {self.ROOT_INODE: []},
        }

    @property
    def root(self):
        """
        :return: the root InodeRecord of this filesystem
        """
        return self._root

    @property
    def rootpath(self):
        """
        :return: The CIPath object of the filesystem root
        """
        return self._rootpath

    def clearcaches(self, *which):
        """
        Entirely clear all or specified caches.

        :param which: One or more names/labels of caches to clear. If omitted, all caches will be cleared.
        """
        if not which:
            which = self.caches.keys()

        for c in which:
            self.caches[c].clear()

    def remove_cached_values(self, cache_name, *keys):
        """
        Remove the specified items from the named cache.

        :param cache_name: Name of cache from which to delete items
        :param keys: items to delete from the cache. If omitted, no items will be removed.
        """
        # don't want to ignore KeyErrors here
        cache = self.caches[cache_name]

        for key in keys:
            try:
                # but here we do
                del cache[key]
            except KeyError:
                # the key may not have been in the cache, which is fine
                pass

    def del_from_caches(self, cache_list, *keys):
        """
        Remove the same key(s) from multiple caches

        :param cache_list: sequence of cache names.
        :param keys: items to delete from each cache named in `cache_list`
        """
        for c in cache_list:
            self.remove_cached_values(c, *keys)

    ##=====================================================
    ## File Access/stats
    ##-----------------------------------------------------
    ## Below, we will often use a version of singledispatch
    ## that dispatches on the second argument (rather than
    ## the first, as the original function does) to allow
    ## it to work with instance methods.
    ##=====================================================

    def inodeof(self, ppath):
        """
        Return the inode number of the file represented by `path`.

        :raise: Error_ENOENT (File Not Found) if the path does not refer to an existing file.
        """
        path = PureCIPath(ppath)

        try:
            return self.caches["inodeof"][path]
        except KeyError:

            parts = path.parts

            if parts[0] != "/":
                raise ValueError("Path must be absolute: ".format(path))

            if len(parts)==1:
                self.caches["inodeof"][path] = self.ROOT_INODE
                return self.ROOT_INODE

            ir=self.root
            for p in parts[1:]:

                try:
                    # `ir` is the parent of the current path part
                    for i in self.dir_inodes(ir.inode):
                        if self._inode_name_lower(i) == p.lower():
                            ir = self.inode_table[i]
                            break
                    else:
                        raise Error_ENOENT(
                            PureCIPath(*parts[:parts.index(p) + 1])) from None
                except Error_EIO:
                    raise Error_ENOENT(
                        PureCIPath(*parts[:parts.index(p) + 1])) from None

            res = self.caches["inodeof"][path] = ir.inode
            return res

    def _inode_name(self, int_inode:int):
        """
        If the inode exists, return its current file name. Raises Error_EIO if the inode is not registered.

        :param int_inode:
        :return:
        """

        try:
            return self.caches["_inode_name"][int_inode]
        except KeyError:
            try:
                n = self.caches["_inode_name"][int_inode] = self.inode_table[int_inode].name
                return n
            except (IndexError, AttributeError):
                raise Error_EIO(int_inode) from None

    def _inode_name_lower(self, inode:int):
        """:return: a lower-case version of the stored name, for case-insensitive comparisons"""
        try:
            return self.caches["_inode_name_lower"][inode]
        except KeyError:
            n = self.caches["_inode_name_lower"][
                inode] = self._inode_name(inode).lower()
            return n

    def pathfor(self, inode:int):
        """
        :return: the absolute path to the current location of the file pointed to by `inode`.
        """
        try:
            return self.caches["pathfor"][inode]
        except KeyError:


            try:
                # grab the inode record from the table
                ir = self.inode_table[inode]

                # means the file that this inode referred to has been deleted
                if ir is None:
                    raise Error_EIO(inode) from None
            except IndexError:
                # and raise error if the inode doesn't exists
                raise Error_EIO(inode) from None

            path_parts = []

            while ir.inode > 0: # since inode 0 == root
                path_parts.append(ir.name)
                ir = self.inode_table[ir.parent]

            # now add the root path
            path_parts.append(self.root.name)

            # and return a constructed path (requires reverse iteration of path_parts)
            path = self.caches["pathfor"][
                inode] = self.CIPath(*path_parts[::-1])

            return path

    def get_path(self, path):
        """
        If `path` is a string or a path object, return the version of `path` that is built from the inode-table; this mainly just guarantees that the path case matches that of the stored inode names, but can also be useful to ensure that the returned path type is associated with this ArchiveFS instance.
        """
        return self.pathfor(self.inodeof(path))

    @singledispatch_m
    def dir_inodes(self, directory):
        """
        :return: the set of inodes for the files contained by `directory`
        """
        try:
            return self._dii(self.inodeof(directory))
        # could be raised from the exception handler in _dii
        except Error_EIO:
            # I'd consider this a more specific (or maybe less specific...
            # but certainly easier to understand) version of EIO
            raise Error_ENOENT(directory) from None
        except Error_ENOTDIR:
            # reraise with actual path
            raise Error_ENOTDIR(directory) from None

    @dir_inodes.register(int)
    def _dii(self, directory):
        try:
            return self.directories[directory]
        except KeyError:
            raise Error_ENOTDIR(directory) #from None


    def dir_length(self, directory):
        """
        Returns the number of items contained by `directory`

        :param directory: Can be a string, a path, or the directory's inode number (int)
        :return: number of items contained by `directory`
        """
        # let the singledispatch mechanics take care of the type for directory
        return len(self.dir_inodes(directory))

    @singledispatch_m
    def ls(self, directory, verbose=False, conv=None):
        """
        List of names of all items in `directory`
        :param directory:
        :param verbose:  if True, each entry in the returned list will be a ``cistat`` object. In a ``cistat`` result, the attribute `st_type` is a single character "d" or "f", denoting whether the entry is a directory or a file, respectively. The `st_ino` attribute is the inode number of the entry, while `st_name` is the entry's filename.
        :param conv: If given, must be a callable that takes a single string (in this case, the filename), performs some conversion, and returns the modified string. The converted filenames will be returned in place of the originals.
        :return:
        """
        # PRINT() << "listdir(" << directory << "):" << self.dir_inodes(directory)

        results = self._ls_inode(self.inodeof(directory), verbose)

        if conv is not None:
            if verbose:
                return [s._replace(st_name=conv(s.st_name)) for s in results]
            return [conv(n) for n in results]

        return results

    @ls.register(int)
    def _ls_inode(self, dirinode, verbose=False):

        if verbose:
            try:
                return self.caches["vlistdir"][dirinode]
            except KeyError:
                filelist = self.caches["vlistdir"][dirinode] = [
                    ## cistat(st_type, st_ino, st_name)
                    cistat("d" if i in self.directories else "f",
                           i, self._inode_name(i))
                    for i in self.directories[dirinode]]
                return filelist
        else:
            try:
                return self.caches["listdir"][dirinode]
            except KeyError:
                filelist = self.caches["listdir"][dirinode] = [
                    self._inode_name(i)
                    for i in self.directories[dirinode]]
                return filelist

    # XXX: is there a need to cache the results of this function (the list of paths)? All the sub-functions it calls are cached, so it'd be slightly redundant; for now let's just watch how everything performs and see about it later.
    def listdir(self, directory):
        """
        :return: list of paths objects for `directory` contents.
        """
        return [self.pathfor(i) for i in self.dir_inodes(directory)]

    def iterdir(self, directory):
        """
        Yield path objects of `directory` contents
        """
        yield from (self.pathfor(i) for i in self.dir_inodes(directory))

    def iterls(self, directory, verbose=False):
        """
        Yield, in no particular order, the names of the files and folders found in `directory`.

        :param directory:
        :param verbose: if True, instead yield tuples with signature (int, ``cistat``). The first item is the depth (from root) of the yielded item, the second is a ``cistat`` object describing the file's properties
        """
        if verbose:
            yield from self._iterls_verbose(directory)
        else:
            yield from (self._inode_name(i) for i in self.dir_inodes(directory))


    def _iterls_verbose(self, directory):

        for i in self.dir_inodes(directory):
            if i in self.directories:
                yield cistat("d", i, self.inode_table[i].name)
            else:
                yield cistat("f", i, self.inode_table[i].name)

    def lstree(self, root="/", include_root=True, verbose=False):
        """
        Return a generator that recursively yields all names of files under the specified directory 'root'. The only requirements for `root` are that it be an existing directory within the filesystem, though the method will not fail if a file-path is passed instead (the `root` filename will be the only value yielded in that case, and only if `include_root` is True.)

         If `include_root` is True, the name of the `root` item itself will be the first item yielded by the generator; if False, the root will be not be included in the output and iteration will begin with the root's children.

        Directory entries are visited in a depth-first manner: the name of each entry is returned as soon as it is encountered; then, if the entry is a directory, the contents of the entry will be yielded (recursively), with iteration of the remaining children in the current directory resuming only once the full subtree for the entry has been returned.

        Note that, since there is no context for the filenames (they are just strings, after all, and do not include the leading path), this basically "flattens" the children of `root` into a list of file names. For a bit more information, set `verbose`=True, or use ``itertree()`` instead.

        :param str|PurePath root: must be absolute
        :param bool include_root:
        :param bool verbose: Return ``cistat`` objects instead of just filenames
        """
        rootpath = PureCIPath(root)
        root_inode = self.inodeof(rootpath)

        if verbose:
            yield from self._lstree_verbose(root_inode, include_root)

        else:
            # if root was actually a file, just yield that filename
            if not self.is_dir(rootpath):
                if include_root:
                    yield self._inode_name(root_inode)
            else:

                def _iter(basenode):
                    for c in self.dir_inodes(basenode):
                        yield self._inode_name(c)
                        if self.is_dir(c):
                            yield from _iter(c)

                if include_root:
                    yield self._inode_name(root_inode)

                yield from _iter(root_inode)

    def _lstree_verbose(self, root_inode, include_root):
        """
        Almost identical to itertree, but yields a tuple with signature (int, ``cistat``). The first item is the depth (from root) of the yielded item, the second is a ``cistat`` object describing the file. For the cistat object, the ``st_type`` codes are:

            * d - Directory
            * f - File

        :param root_inode:
        :param include_root:
        """
        if not self.is_dir(root_inode):
            if include_root:
                yield (0, cistat("f", root_inode,  self._inode_name(root_inode)))
        else:

            depth = -1
            if include_root:
                depth += 1
                yield (0, cistat("f", root_inode,  self._inode_name(root_inode)))

            def _iter(basenode):
                nonlocal depth
                depth += 1
                for c in self.dir_inodes(basenode):
                    if self.is_dir(c):
                        yield (depth, cistat("d", c, self._inode_name(c)))
                        yield from _iter(c)
                    else:
                        yield (depth, cistat("f", c, self._inode_name(c)))
                depth -= 1

            yield from _iter(root_inode)

    def itertree(self, root="/", include_root=False, verbose=False):
        """
        Recursively yield full paths for the directory tree under initial path `root`.

        :param str|PurePath root: starting point of the tree.
        :param include_root: Whether to yield `root` as the first item.
        :param verbose: If True, returns additional information: Each item yielded will be a tuple with signature (int, str, CIPath). The first item is the depth (from root) of the yielded path, the second is a single character indicating the type of file the path refers to, and the third is the path object. The type codes are as for the cistat result object:

            * d - Directory
            * f - File
        """
        rootpath = self.get_path(PureCIPath(root))

        if verbose:
            yield from self._itertree_verbose(rootpath, include_root)
        else:
            if not self.is_dir(rootpath):
                yield rootpath

            else:

                def _iter(base_path, base_node):
                    for inode in self.dir_inodes(base_node):
                        # build the item's path from the current path + saved name
                        childpath = self.CIPath(base_path, self._inode_name(inode))
                        # yield children as found
                        yield childpath
                        # then recurse if needed
                        if self.is_dir(inode):
                            yield from _iter(childpath, inode)

                if include_root:
                    yield rootpath

                yield from _iter(rootpath, self.inodeof(rootpath))


    def _itertree_verbose(self, rootpath, include_root):
        """
        Like itertreepaths, but returns additional information: Each item yielded is a tuple with signature (int, CIPath, str). The first item is the depth (from root) of the yielded path, the second is the path object, and the third is a single character indicating the type of file the path refers to. For now, the only type-codes are:

            * d - Directory
            * f - File

        :param CIPath rootpath:
        :param include_root:
        """

        if not self.is_dir(rootpath):
            yield (0, "f", rootpath)

        else:
            depth=-1

            if include_root:
                depth+=1
                yield (0, "d", rootpath)

            def _iter(base_path, base_node):
                nonlocal depth
                depth += 1
                for inode in self.dir_inodes(base_node):
                    # build the item's path from the current path + saved name
                    childpath = self.CIPath(base_path,
                                            self._inode_name(inode))

                    # yield children as found,
                    # then recurse if needed
                    if self.is_dir(inode):
                        yield (depth, "d", childpath)
                        yield from _iter(childpath, inode)
                    else:
                        yield (depth, "f", childpath)
                depth-=1

            yield from _iter(rootpath, self.inodeof(rootpath))



    @singledispatch_m
    def is_dir(self, path):
        """
        :return: True if `path` is a directory, False if `path` is a regular file
        """
        return self._idi(self.inodeof(path))

    @is_dir.register(int) # directly given inode
    def _idi(self, inode):
        """

        :param inode: inode number of path
        :return: True if `inode` is the inode of a directory
        """
        return inode in self.directories

    @singledispatch_m
    def exists(self, path): # should catch str and other path-types
        """
        Check that `path` refers to an existing file or folder.
        """
        try:
            # if it finds it...it's because it was findable
            self.inodeof(path)
            return True
        except Error_ENOENT:
            return False

    @exists.register(int) # for checking inodes
    def _ei(self, inode):
        return inode < len(self.inode_table) and self.inode_table[inode] is not None

    ##===============================================
    ## File Creation
    ##===============================================

    def touch(self, path, name=None):
        """
        Create a file.
        By default, any parents of `path` that do not exist will be created. If `path` already exists, this function does nothing.

        :param path:
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

        :param path:
        :param exist_ok: if True, an error will not be raised when the directory already exists
        """
        path = PureCIPath(path)

        try:
            inode = self._create(path)
            # print("created directory {}".format(path))
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
            raise Error_EEXIST(path.str)

        # new inode numbers are always == 1+current maximum inode.
        # since they start at 0, this is == the len of the table
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

        # un-cache the parent-dir's file list
        self.del_from_caches(("listdir", "vlistdir"), parent_inode)


    ##===============================================
    ## File Deletion
    ##===============================================

    def rm(self, path):
        """
        Delete a file path and null-out its inode-reference
        Use rmdir for directories.

        :param str|PurePath path:
        """
        path = PureCIPath(path)

        if self.is_dir(path):
            raise Error_EISDIR(path)

        self._unlink(self.inodeof(path))

        self.remove_cached_values("inodeof", path)

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

        # finally, remove the cached inodeof() value
        self.remove_cached_values("inodeof", dirpath)

    def rmtree(self, directory):
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
        par_inode = self.inode_table[dirinode].parent
        self.directories[par_inode].remove(dirinode)

        # delete cached listdir() result for its parent
        self.del_from_caches(("listdir", "vlistdir"), par_inode)

        # and, since figuring out exactly which paths were deleted
        # could be an expensive, superflous operation, it's easier
        # just to clear the entire inodeof() cache
        self.caches["inodeof"].clear()

    def _del_dir(self, dirinode):
        """
        Unconditionally delete the directory specified by `dirinode`.
        No checks, just does the job.

        :param int dirinode:
        """
        # remove it from directory table & listdir cache
        del self.directories[dirinode]
        self.del_from_caches(("listdir", "vlistdir"), dirinode)

        # now delete it like any other file
        self._unlink(dirinode)

    def _del_dir_tree(self, dirinode:int):

        # will raise ENOTDIR if directory is not...a directory.
        child_inodes = self.dir_inodes(dirinode)
        for childnode in child_inodes:
            if not self.is_dir(childnode):
                # don't need to bother removing it from the directory's
                # node list since we're deleting the directory in just
                # a second anyway.
                self.inode_table[childnode] = None

            else:
                self._del_dir_tree(childnode)

        # remove cached values
        self.del_from_caches(("_inode_name", "pathfor", "_inode_name_lower"),
                             *child_inodes)

        # remove the empty dir when it's all done
        del self.directories[dirinode]
        self.inode_table[dirinode]=None
        self.del_from_caches(("listdir", "vlistdir"), dirinode)


    def _unlink(self, inode):
        """
        Instead of deleting the inode from the inode table,
        (thus changing the length of the list and messing up all our inodes),
        this replaces the index in the table with ``None``. Also removes
        the inode from its parent's list of child-inodes
        :param int inode:
        :return:
        """
        inorec = self.inode_table[inode]

        # remove this node from its parent-directory's nodelist
        self.directories[inorec.parent].remove(inode)

        # clear it from some of the caches
        self._cleanup_inode_cache(inorec)

        # and null out its entry in the inode table
        self.inode_table[inode] = None

    def _cleanup_inode_cache(self, inode_record):
        """
        :param InodeRecord inode_record:
        """
        # clear some cache values
        self.del_from_caches(("_inode_name", "_inode_name_lower", "pathfor"),
                             inode_record.inode)

        self.del_from_caches(("listdir", "vlistdir"), inode_record.parent)


    ##===============================================
    ## Name/Path Manipulation
    ##===============================================

    def move(self, path, destination, overwrite=OverwriteMode.PROMPT):
        """...
        Move the file or directory pointed to by `path` to `destination`.

        :param path:
        :param destination:
            If `destination` is an existing directory, `path` will become a child of `destination`. Otherwise, the filesystem path of the file-object `path` will be changed to `destination`.
        :param overwrite:
            If `destination` is an already-existing file and `overwrite` is False, a File-Exists error will be raised; if overwrite is True, `destination` will be deleted and replaced with `path`
        :return: True if all went well
        """

        # PRINT() << "move(" << path << ", " << destination << ")"

        src = PureCIPath(path)
        dst = PureCIPath(destination)

        # if someone attempted to move an item to itself, just return
        if src == dst: return True

        # if the destination is an existing directory, move the source inside of it.
        if self.is_dir(dst):
            dst = PureCIPath(dst, src.name)

            # if someone attempted to move an item inside its own parent, just return
            if dst == path:
                return True

        # and now this is a rename operation
        return self._dorename(src, dst, overwrite)

    def rename(self, path, destination, overwrite=OverwriteMode.PROMPT):
        """...
        Functions much like ``move``; the main difference is that, if the destination is a directory, instead of moving path inside that directory, an attempt will be made to overwrite it; if the destination directory is empty, this attempt will always succeed. If it is a file or non-empty directory, success depends on the value of `overwrite`.

        :param path: path being renamed
        :param destination: target path
        :param overwrite: If True, then an existing target will be unconditionally replaced--this means that, if the target is a non-empty directory, all contents of that directory tree will be removed.
        :return: True if the operation was successful; False if the operation could not be completed for some reason but the error was suppressed (most likely this means `overwrite`==``OverwriteMode.IGNORE``)
        """

        # PRINT() << "rename(" << path << ", " << destination << ")"

        src = PureCIPath(path)
        dest = PureCIPath(destination)

        if src == dest:
            return True

        return self._dorename(src, dest, overwrite)

    def _dorename(self, src, dest, overwrite):
        """
        Perform the rename operation

        :param src:
        :param dest:
        :param overwrite:
        :return:
        """
        # PRINT() << "_dorename(" << src << ", " << dest << ")"


        if self.exists(dest) and self.is_dir(dest):
            try:  # if the directory is empty, this will succeed and
                # we can just rename the src
                self.rmdir(dest)
            except Error_ENOTEMPTY:
                # if overwrite & OverwriteMode.MERGE:
                    # PRINT() << "merging"
                    # return self._merge_dirs(src, dest, overwrite)
                if overwrite & OverwriteMode.REPLACE:
                    self.rmtree(dest)
                elif overwrite & OverwriteMode.IGNORE:
                    return False
                else:
                    raise

        else:  # file
            try:
                self._check_collision(dest, overwrite)
            except Error_EEXIST:
                PRINT() << "collided"

                if overwrite & OverwriteMode.IGNORE:
                    return False
                raise

            if dest.parent == src.parent:
                return self._change_name(src, dest.name)

        return self._move(src, dest)

    def chname(self, path, new_name, overwrite=OverwriteMode.PROMPT):
        """...
        A simplified rename that just changes the file name (final path component) of `path` to `new_name`

        :param path:
        :param new_name:
        :param overwrite:
        :return:
        """

        # PRINT() << "chname(" << path << ", " << new_name << ")"

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
                    # noinspection PyUnresolvedReferences
                    e.msg = "Will not overwrite directory '{dest}' with non-directory '{path}'".format(
                        dest=dest)
                    raise e
            # dest is file:
            else:
                try:
                    self._check_collision(dest, overwrite)
                except Error_EEXIST:
                    if overwrite & OverwriteMode.IGNORE:
                        return False
                    raise

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
        self.rename(path, destination, OverwriteMode.REPLACE)

    def _move_to_dir(self, path, dest_dir, overwrite):
        """
        Move file or dir `path` inside directory `dest_dir`
        """

        # PRINT() << "_move_to_dir(" << path << ", " << dest_dir << ")"

        dest_path = PureCIPath(dest_dir, path.name)

        self._check_collision(dest_path, overwrite)

        # if someone attempted to move an item inside its own parent, just return
        if dest_path == path:
            return True

        return self._move(path, dest_path)

    def _move(self, from_path, to_path):
        """
        Perform the final move of `from_path` to destination `to_path`. At this point, `to_path` can be assumed not to exist and to have been cleared from all appropriate caches.
        """

        # PRINT() << "_move(" << from_path << ", " << to_path << ")"

        inorec = self.inode_table[
            self.inodeof(from_path) ] # get inode record from current path value

        # remove from old dir
        self.directories[inorec.parent].remove(inorec.inode)
        self.del_from_caches(("listdir", "vlistdir"), inorec.parent)

        # change name and parent
        inorec.name = to_path.name
        inorec.parent = self.inodeof(to_path.parent)

        # add to new dir
        self.directories[inorec.parent].add(inorec.inode)

        ## final cleanup of some cache values ##

        # clear listdir results for new parent
        self.del_from_caches(("listdir", "vlistdir"), inorec.parent)

        if self.is_dir(inorec.inode):
            # if we move a directory, a lot of paths may have changed,
            # so we're just going to clear the entire inodeof() and
            # pathfor() caches
            self.clearcaches("inodeof", "pathfor")
        else:
            # but if it was just a file, we don't need to be so dramatic
            self.remove_cached_values("pathfor", inorec.inode)
            self.remove_cached_values("inodeof", from_path)

        # if the item changed names, also clear the name caches
        if from_path.name != to_path.name:
            self.del_from_caches(("_inode_name", "_inode_name_lower"), inorec.inode)

        return True

    def _change_name(self, path, new_name):
        """
        Just change the name of the file or directory pointed to by path
        (simpler version of _move())

        :param path:
        :param str new_name:
        """
        # PRINT() << "_change_name(" << path << ", " << new_name << ")"


        inorec = self.inode_table[self.inodeof(path)]
        inorec.name = new_name

        self._cleanup_inode_cache(inorec)

        if self.is_dir(inorec.inode):
            self.clearcaches("inodeof", "pathfor")
        else:
            self.remove_cached_values("pathfor", inorec.inode)
            self.remove_cached_values("inodeof", path)

        return True

    def _check_collision(self, target, overwrite):
        """...
        If the file `target` exists and overwrite is True, `target` will be deleted. If `target` exists and `overwrite` is False, raise Error_EEXIST. If `target` does not exist, do nothing.

        :param target: must not be a directory
        :param overwrite:
        """
        # PRINT() << "_check_collision(" << target << ", " << overwrite << ")"

        if self.exists(target):
            if overwrite & OverwriteMode.REPLACE:
                self.rm(target)
            else:
                raise Error_EEXIST(target)

    # thoughts: there needs to be some way to prompt the user during the merge operation about further collisions and then continue where it left off. Turning this method into some sort of generator and yielding on EEXIST errors might be a way to do that.
    # def _merge_dirs(self, dir1, dir2, overwrite=OverwriteMode.MERGE):
    #     # PRINT() << "_merge_dirs(" << dir1 << ", " << dir2 << ")"
    #
    #     for child in self.iterdir(dir1):
    #         self._dorename(child, PureCIPath(dir2, child.relative_to(dir1)), overwrite)
    #     #after all children moved, remove source dir
    #     try:
    #         self.rmdir(dir1)
    #     except Error_ENOTEMPTY:
    #         if overwrite & OverwriteMode.IGNORE:
    #             return False
    #         raise
    #     return True

    # def merge(self, srcdir, destdir, overwrite=OverwriteMode.MERGE):
    #     # PRINT() << "merge(" << srcdir << ", " << destdir << ")"
    #
    #
    #     src_dst_pairs = [(sc, destdir / sc.relative_to(srcdir)) for sc in self.itertree(srcdir)]
    #
    #     # [print(p) for p in src_dst_pairs]
    #
    #     return True

        # for child in self.iterdir(srcdir):
        #     if not self.is_dir(child):
        #         try:
        #             self._dorename(child, destdir / child.name)


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

        for p in self.itertree(from_path, include_root=False):
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

    def fsck(self, root="/"):
        return fsck_modfs(self, root)

    def fsck_quick(self, root="/"):
        """
        Check the root directory of the file hierarchy for viable game data.

        :param root:
        :return: True if matching data was found.
        """
        return fsck_modfs_quick(self, root)


def fsck_modfs(modfs, root="/"):
    """
    Check if the pseudo-filesystem represented by `modfs` contains recognized game-data on its top level.
    Return an object containing the recognized items.

    This method is far more complex than fsck_quick, and is likely unnecessary.

    :param arcfs.ArchiveFS modfs:
    :param root:
    :return: 3-tuple:
        (number_of_recognized_valid_toplevel_items,
         dict_of_that_data_and_other_stuff,
         directory_which_contains_the_game_data),

         where the last item may not be the same as the original root of `modfs`. (It will only be different if the only item in root was a directory that held all the actual data, i.e. should have just been the root directory in the first place.)
    """
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

    for fstat in modfs.iterls(root, verbose=True):
        if fstat.st_type=="d" and fstat.st_name.lower() in TopLevelDirs_Bain:
            mod_data["folders"].append(fstat.st_name)

        elif fstat.st_type=="f" and fstat.st_name.rsplit(".", 1)[-1].lower() in TopLevelSuffixes:
        # elif topitem.suffix.lower().lstrip(".") in TopLevelSuffixes:
            mod_data["files"].append(fstat.st_name)

        elif doc_match.search(fstat.st_name):
            mod_data["docs"].append(fstat.st_name)

    # one last check if the previous searches turned up nothing:
    # if there is only one item on the top level
    # of the mod and that item is a directory, then check inside that
    # directory for the necessary files.
    if not (mod_data["folders"] and mod_data["files"]):
        _list = modfs.ls(root, verbose=True)
        if len(_list) == 1 and _list[0].st_type == "d":
            return fsck_modfs(modfs, PureCIPath(root, _list[0].st_name).str)

    return len(mod_data["folders"]) + len(
        mod_data["files"]), mod_data, root

def fsck_modfs_quick(modfs, root="/"):
    """
    Check the root directory of the file hierarchy for viable game data.

    :param ArchiveFS modfs: the filesystem to check
    :param root: Path to the root directory, default '/'
    :return: True upon finding the first file/directory that is recognized as game data; False if no files or directories in the root match this condition.
    """


    for topinfo in modfs.iterls(root, verbose=True):
        if (topinfo.st_type == "d" and topinfo.st_name.lower()
                         in TopLevelDirs_Bain) \
        or (topinfo.st_type == "f" and topinfo.st_name.rsplit(".", 1)[-1].lower()
                         in TopLevelSuffixes): return True

    return False


# def __test1():
#     cip = PureCIPath("test", "rest")
#     CIP = PureCIPath("TEST", "REST")
#     Cip = PureCIPath("Test", "Rest")
#
#     print(cip, CIP, Cip, sep="\n")
#
#     print(cip == CIP)
#     print(Cip == CIP)
#     print(Cip == cip)
#
#     pathlist = [cip, PureCIPath("not", "the", "same")]
#     print(CIP in pathlist)
#
#     pathdict = {Cip: "hello"}
#
#     print (pathdict[cip])
#
#
#
# if __name__ == '__main__':
#     # from skymodman.managers.archive_7z import ArchiveHandler
#     __test1()
