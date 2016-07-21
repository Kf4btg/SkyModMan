from skymodman.exceptions import Error

__all__ = ['FSError', 'Error_EEXIST', 'Error_ENOTDIR', 'Error_EISDIR',
           'Error_EISDIR', 'Error_ENOTEMPTY', 'Error_ENOENT',
           'Error_EIO']

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