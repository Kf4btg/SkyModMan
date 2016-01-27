from functools import singledispatch
import os
import tempfile
from pathlib import Path
import shutil

from os.path import exists, isdir, join

class SafeWriter:
    """ A context manager that can be used to safely and atomically overwrite an existing file
    """

    def __init__(self, file_name, dest_dir, as_bytes=False):
        """

        :param str file_name:
        :param str dest_dir:
        :param bool as_bytes:
        :return:
        """
        assert file_name and dest_dir, "Names are required for both file name and destination directory"
        if exists(dest_dir):
            assert isdir(dest_dir), "Destination exists but is not a directory"
        else:
            os.makedirs(dest_dir) # create dest directory if it doesn't exist

        self.tmpdir = tempfile.TemporaryDirectory(prefix='smm_tmp')
        self.tmpfile = join(self.tmpdir.name, file_name)
        self.destfile = join(dest_dir, file_name)

        mode = 'w+b' if as_bytes else 'w'

        if exists(self.destfile):
            Path(self.tmpfile).touch() #create empty tmpfile

            # and copy all attributes from src file to our temp file
            # (perm, access/mod times, xattrs, etc.). This way it
            # will be as if we're just modifying the file's contents
            # rather than replacing it outright
            shutil.copystat(self.destfile, self.tmpfile)
        self.tmpfd = open(self.tmpfile, mode)

    def __enter__(self):
        return self.tmpfd

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.tmpfd.close()
        if exc_type is None:
            # replace destination with modified file, atomically
            try:
                # Path.replace() (and os.replace()) can fail with an 'Invalid cross-device link'
                # OSError; thus we have to use shutil.move() instead
                shutil.move(self.tmpfile, self.destfile)
            finally:
                self.tmpdir.cleanup()
        else:
            # remove tmpdir and contents
            self.tmpdir.cleanup()
        return False


@singledispatch
def open_for_safe_write(file_name, dest_dir, as_bytes=False):
    """

    This method has two forms:

        * ``open_for_safe_write(file_name, dest_dir, as_bytes=False)``
        * ``open_for_safe_write(dest_file_path, as_bytes=False)``

    In the first form, `file_name` and `dest_dir` are both strings. In the second, `dest_file_path` is a Path object. In both cases, as_bytes is a boolean value

    """
    return SafeWriter(file_name, dest_dir, as_bytes)

@open_for_safe_write.register(Path)
def _ofsw(dest_file_path, as_bytes=False):
    return SafeWriter(dest_file_path.name, str(dest_file_path.parent), as_bytes)