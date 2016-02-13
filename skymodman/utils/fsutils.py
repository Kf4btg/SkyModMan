from contextlib import contextmanager
from pathlib import Path

import os
from os.path import (exists as _exists,
                     expanduser as _expand)

__all__ = ["checkPath", "change_dir", "dir_move_merge"]


def checkPath(path, exp_user=False):
    """
    Verifies that path is not None or an empty string, then returns whether
    the path exists on the filesystem.

    :param str path:
    :param exp_user: expand ~ in path string
    :return:
    """
    if exp_user:
        return path and _exists(_expand(path))
    return path and _exists(path)


@contextmanager
def change_dir(dir_):
    """
    A context manager that changes to the working directory to the path given by `dir` for the operations given in the with block, then changes back to the original wd on exit.  The full path of the original working directory is returned as the value of the contextmanager and can be bound with ``as``; this can be useful for referencing paths that are relative to the original wd.

    :param dir_:
    """

    pwd = os.getcwd()
    os.chdir(dir_)
    yield pwd

    os.chdir(pwd)


def dir_move_merge(source, destination, overwite=True):
    """
    Moves a directory `source` to the directory `destination`. If `destination` does not exist, then `source` is simply renamed to `destination`. If `destination` is an existing directory, then the contents of `source` are recursively moved or merged with the contents of `destination` as needed.



    :param str|Path source:
    :param str|Path destination:
    :param overwite: If `overwrite` is True, any files from `source` that are in conflict with an existing file of the same name in `destination` will replace the destination's file with the version coming from the source, irreversibly deleting the file in `destination`. If `overwrite` is False, then the pre-existing file in `destination` will be kept and the version from `source` will be deleted.
    """
    src = Path(source)
    dst = Path(destination)

    if dst.exists():
        for child in src.iterdir():
            if child.is_dir():
                dir_move_merge(child, dst / child.relative_to(src))
            elif overwite:
                child.replace(dst / child.relative_to(src))
            else:
                child.unlink()
        # after all children taken care of, remove the source
        src.rmdir()
    else:
        # create the parent hierarchy to the destination
        dst.mkdir(parents=True, exist_ok=True)
        # move source into place
        src.replace(dst)