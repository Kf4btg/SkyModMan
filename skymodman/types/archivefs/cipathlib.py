from pathlib import PurePath, _PosixFlavour
from collections import namedtuple

# from skymodman.types.archivefs.fserrors import *
from skymodman.constants import OverwriteMode

cistat = namedtuple("cistat", "st_type st_ino st_name")
# noinspection PyUnresolvedReferences
cistat.__doc__ = "A simplified version of os.stat_result, this contains the fields `st_type` for file type, `st_ino` for inode number, and `st_name` for current file name."

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
            # noinspection PyAttributeOutsideInit
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
            # noinspection PyAttributeOutsideInit
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


# this won't run, but it lets the type checker recognize the
# ArchiveFS type
if __name__ == '__main__':
    from .archivefs import ArchiveFS