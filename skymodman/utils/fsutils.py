from contextlib import contextmanager
from functools import singledispatch
from pathlib import Path

import os
import shutil
from os.path import (exists as _exists,
                     expanduser as _expand,
                     join as _join)

from skymodman.exceptions import FileAccessError, FileDeletionError, MultiFileError
from skymodman.utils.safewrite import SafeWriter as _safewriter

__all__ = ["check_path", "join_path", "change_dir", "dir_move_merge"]

# alias os.listdir
listdir=os.listdir

def check_path(path, exp_user=False):
    """
    Verifies that path is not None or an empty string, then returns
    whether the path exists on the filesystem.

    :param str path:
    :param bool exp_user: expand ~ in path string
    """

    if path:
        return _exists(_expand(path)) if exp_user else _exists(path)
    return False

def join_path(base_path, *path_parts, as_path_object=False):
    """

    :param str base_path: first part of the path
    :param str path_parts: any number of additional path pieces to join
    :param bool as_path_object: if True, return the result as a
        pathlib.Path object; otherwise, it is returned as a string
    :return:
    """

    if as_path_object:
        return Path(base_path, *path_parts)

    return _join(base_path, *path_parts)

@contextmanager
def change_dir(dir_):
    """
    A context manager that changes to the working directory to the path
    given by `dir` for the operations given in the with block, then
    changes back to the original wd on exit.  The full path of the
    original working directory is returned as the value of the
    contextmanager and can be bound with ``as``; this can be useful for
    referencing paths that are relative to the original wd.

    :param dir_:
    """

    pwd = os.getcwd()
    os.chdir(dir_)
    yield pwd

    os.chdir(pwd)


def dir_move_merge(source, destination,
                   overwite=True, name_mod=lambda n:n):
    """
    Moves a directory `source` to the directory `destination`. If
    `destination` does not exist, then `source` is simply renamed to
    `destination`. If `destination` is an existing directory, then the
    contents of `source` are recursively moved or merged with the
    contents of `destination` as needed.

    :param str|Path source:
    :param str|Path destination:
    :param name_mod: A callable used when recursively merging
        sub-directories; takes as an argument the str path of a
        sub-directory in `source` relative to `source` and returns a
        modified version of that relpath; the returned path will be
        appended to `destination` to form the final, absolute
        destination path. The default value for this parameter just
        returns the original relpath unaltered.
    :param overwite: If `overwrite` is True, any files from `source`
        that are in conflict with an existing file of the same name in
        `destination` will replace the destination's file with the
        version coming from the source, irreversibly deleting the file
        in `destination`. If `overwrite` is False, then the pre-existing
        file in `destination` will be kept and the version from `source`
        will be deleted.
    """
    src = Path(source)
    dst = Path(destination)

    if not dst.exists():
        # create the parent hierarchy to the destination
        dst.mkdir(parents=True, exist_ok=True)

    # recursively merge; we can't just do a rename if the destination
    # doesn't exist because we need to make sure every item gets run
    # through name_mod()
    _merge_dir(src, dst, overwite, name_mod)


def _merge_dir(src, dst, ow, name_mod):
    for child in src.iterdir():
        if child.is_dir():
            dir_move_merge(child,
                           dst / name_mod(str(child.relative_to(src))),
                           ow, name_mod)
        elif ow:
            child.replace(dst / name_mod(str(child.relative_to(src))))
        else:
            child.unlink()
    # after all children taken care of, remove the source
    src.rmdir()

def move_path(src, dst):
    """
    Given two pathlib.Path objects, recursively rename `src` to `dst`,
    creating any necessary intermediate directories.
    :param Path src:
    :param Path dst:
    :return:
    """
    # if the destination does not exist or is a directory,
    # move using default shutil semantics (i.e. move the item inside
    # the destination directory, or create the destination and parent dirs)
    if not dst.exists() or dst.is_dir():
        shutil.move(str(src), str(dst))
    else:
        raise FileAccessError(
            str(dst),
            "'{file}' must be a directory or must not already exist.")

def move_dir_contents(src, dst, remove_old=False):
    """
    Move the contents of a directory `src` to a new location `dst` which
    must be an empty directory or non-existent.

    :param str src:
    :param str dst:
    :param bool remove_old: If True, attempt to remove the original
        source directory after its contents have been moved.
    """

    curr_path = Path(src)

    new_path = Path(dst)

    # list of 2-tuples; item1 is the file we were attempting to move,
    # item2 is the exception that occurred during that attempt
    errors = []

    # flag to indicate whether we should copy all the contents or
    # move the original dir itself
    copy_contents = True

    # make sure new_path does not exist/is empty dir
    if new_path.exists():

        # also make sure it's a directory
        if not new_path.is_dir():
            raise FileAccessError(dst, "'{file}' is not a directory")

        if len(os.listdir(dst)) > 0:
            raise FileAccessError(
                dst, "The directory '{file}' exists and is non-empty.")
        ## dir exists and is empty; easiest thing to do would be to remove
        ## it and move the old folder into its place; though if the dir is a
        ## symlink, that could really mess things up...guess we'll have to do
        ## it one-by-one, then.
        # copy_contents = True

    elif remove_old:
        # The scenario where the destination does not exist and we're
        # removing the original folder is really the only situation
        # in which we can get away with simply moving the original...
        copy_contents = False

    ###########################
    ## actual move operation ##

    if copy_contents:
        for item in curr_path.iterdir():
            # move all items inside the new path
            try:
                move_path(item, new_path)
            except (OSError, FileAccessError) as e:
                # self.LOGGER.error(e)
                errors.append((item, e))

        if not errors:
            ## after all that, we can remove the old dir...hopefully
            if remove_old:
                try:
                    curr_path.rmdir()
                except OSError as e:
                    raise FileDeletionError(
                        curr_path,
                        "The original directory '{file}' "
                        "could not be removed") from e
    else:
        # new_path does not exist, so we can just move the old dir to
        # the destination
        # (this intrinsically takes care of the 'remove_old_dir' flag)
        try:
            move_path(curr_path, new_path)
        except (OSError, FileAccessError) as e:
            # self.LOGGER.exception(e)
            errors.append((curr_path, e))
        # else:
            # if we managed it without error, update our configured path
            # self.set_path(key, new_path, profile_override)

    if errors:
        raise MultiFileError(errors, "Errors occurred during move operation.")

def create_dir(path, parents=True):
    """
    Create a directory. If parents is True, also create all intermediate
    directories. If parents is false and the necessary file hierarchy
    does not exist, the typical OSError will be raised.

    If the path already exists, no error will be raised, but the method
    will return False

    :param path: of the directory to create
    :param bool parents: create parent directories, if needed.
    :return: True if the directory was successfully created. False if it
        already existed.
    """

    if parents:
        try:
            os.makedirs(path, exist_ok=False)
        except OSError:
            # OSError is thrown if target already exists
            return False
    else:
        try:
            os.mkdir(path)
        except FileExistsError:
            return False

    return True


def recursive_delete(target, ignore_errors=False):
    """
    Mainly just a proxy for shutil.rmtree


    :param target:
    """
    # TODO: add support for removing only files, only empty dirs, ...

    if os.path.exists(target):
        shutil.rmtree(os.fspath(target), ignore_errors=ignore_errors)




##=================================
## Atomic-Write
##---------------------------------

@singledispatch
def open_atomic(file_name, dest_dir=None, as_bytes=False):
    """
    Obtain a context manager for for writing to a file safely and
    atomically. If something goes wrong during the write, nothing will
    have been overwritten. Can be used just like the built in open(f...)

    This method has two forms:

        * ``open_atomic(file_name, dest_dir, as_bytes=False)``
        * ``open_atomic(dest_file_path, as_bytes=False)``

    In the first form, `file_name` and `dest_dir` are both strings. If
    dest_dir is None, file_name will be assumed to be entire path to
    the file to open.

    In the second, `dest_file_path` is a Path object.

    In both cases, as_bytes is a boolean value

    :type file_name: str
    :type dest_dir: str
    :type as_bytes: bool
    """
    if dest_dir is None:
        dest_dir = os.path.dirname(file_name)
        file_name = os.path.basename(file_name)

    return _safewriter(file_name, dest_dir, as_bytes)

@open_atomic.register(Path)
def _ofsw(dest_file_path, as_bytes=False):
    """

    :param Path dest_file_path:
    :param bool as_bytes:
    """
    return _safewriter(dest_file_path.name, str(dest_file_path.parent), as_bytes)