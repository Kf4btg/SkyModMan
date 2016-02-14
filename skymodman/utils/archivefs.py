from collections import namedtuple
from pathlib import PurePath, _PosixFlavour

from skymodman.exceptions import Error

class FSError(Error):
    """ Represents some sort of error in the ArchiveFS """
class Error_EEXIST(FSError):
    """ File Exists Error """
class Error_ENOTDIR(FSError):
    """ Not a Directory """
class Error_EISDIR(FSError):
    """ Is a directory """
class Error_ENOTEMPTY(FSError):
    """ Directory not Empty """
class Error_ENOENT(FSError):
    """ No such File or Directory """
class Error_EIO(FSError):
    """ Input/Output Error (inode not found) """

fileinfo = namedtuple("fileinfo", "inode is_dir is_file path name")



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


class ArchiveFS:

    # noinspection PyUnresolvedReferences
    def __init__(self):
        # list of paths, where an item's index in the list corresponds to its inode number.
        self.i2p_table = [] # type: list[PureCIPath]
        self.inodePathTable = []
        # inode -> path

        # mapping of filepaths to inodes
        self.p2i_table = dict() # type: dict[PureCIPath, int]
        self.pathInodeTable = dict()
        # path -> inode

        # mapping of directory-inodes to set of inodes they contain
        self.directories = dict() # type: dict[int, set[int]]
        # inode -> {inode, ...}

        # mapping of inodes to a CIFile instance describing the current state of a file representing that inode
        # self.file_table = {} # inode -> CIFile

        # create root of filesystem
        self._root=PureCIPath("/")
        self.i2p_table.append(self._root) # inode 0
        self.p2i_table[self._root]=0
        self.directories[0]=set() # create empty list

    @property
    def root(self):
        return self._root

    # File Access/stats

    def inodeof(self, path):
        try:
            return self.p2i_table[path]
        except KeyError:
            raise Error_ENOENT(path.str)

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

    def dir_inodes(self, dirpath):
        try:
            return self.directories[self.inodeof(dirpath)]
        except KeyError:
            raise Error_ENOTDIR(dirpath.str)

    def listdir(self, directory):
        return [self.i2p_table[i] for i in self.dir_inodes(directory)]

    def iterdir(self, directory):
        #            inode -> path
        yield from (self.i2p_table[i] for i in self.dir_inodes(directory))

    def is_dir(self, path):
        return self.inodeof(path) in self.directories

    def exists(self, path):
        return path in self.p2i_table



    # File Creation

    def _create(self, path):
        """
        By default, any parents of `path` that do not exist will be created.
        :param path:
        :return:
        """

        if path in self.p2i_table:
            raise Error_EEXIST(path.str)

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

        # inode=self._create(fullpath)
        self._create(fullpath)

        # self.file_table[inode] = CIFile(inode, self.inodeof(fullpath.parent), False, fullpath.name)

    def mkdir(self, path, exist_ok=False):
        """
        By default, any parents of `path` that do not exist will be created.

        :param exist_ok: if True, an error will not be raised when the directory already exists
        """
        try:
            inode=self._create(PureCIPath(path))
            self.directories[inode]=set()
        except Error_EEXIST:
            if not exist_ok:
                raise

    ## File Deletion

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

    ## File manipulation

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

        # if destination path is in the same folder as the source, this is just a name change
        if dst.parent == src.parent:
            return self._change_name(src, dst.name)

        # and if we made it here, we can finally just move src to dst
        return self._move_to_path(src, dst)

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
        :param new_name:
        :return:
        """
        # if dest.parent == src.parent:
        #     # just moving to a new name in the same directory;
        #     # only need to change the file name. Use dest.name
        #     # instead of just putting dest in src's place so that
        #     # the case of the names of any parents remains consistent.
        #     self._change_name(src, dest.name)
        #     return True

        inode = self.inodeof(path)
        new_path = path.with_name(new_name)
        self.i2p_table[inode] = new_path

        del self.p2i_table[path]
        self.p2i_table[new_path] = inode
        return True

    def _check_collision(self, target, overwrite):
        if self.exists(target):

            if overwrite: self.rm(target)

            else: raise Error_EEXIST(target.str)

    def rename(self, path, destination, overwrite=False):
        src = PureCIPath(path)
        dest = PureCIPath(destination)

        if src == dest: return True

        if self.is_dir(dest):
            try:
                # if the directory is empty, this will succeed and we will just rename the src
                self.rmdir(dest)
            except Error_ENOTEMPTY:
                if overwrite: self.rmtree(dest)
                else: raise

        else:
            self._check_collision(dest, overwrite)

            if dest.parent == src.parent:
                return self._change_name(src, dest.name)

        return self._move_to_path(src, dest)

    def replace(self, path, destination):
        """

        :param path:
        :param destination: If exists, will be unconditionally replaced; if it is a directory all its contents will be removed
        :return:
        """
        self.rename(path, destination, True)


    # todo: copy and copytree (maybe...since our 'files' are really just names and contain no data, a 'copy' operation may be unnecessary)








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
    __test1()