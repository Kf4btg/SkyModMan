from pathlib import Path, PurePath

from skymodman.utils import fsutils
from skymodman.exceptions import FileDeletionError


class AppFolder:
    """
    Represents one of the directories that is required by the
    application. The directory should be accessible through this object
    at any time, no matter what its actual file-system path is, and
    even if the user changes such path.
    """

    def __init__(self, name, display_name, default_path=None, current_path=None, *, change_listeners=None):
        """

        :param str name: this will be the key used to identify the
            directory throughout the application
        :param str display_name: the name that will shown to the user
            if information regarding this directory is requested or
            presented.
        :param str|Path default_path: if the folder should have a default path,
            provide one here. If neither this nor `current_path` is provided,
            the path for this AppFolder will be unset until the user sets it.
        :param str|Path current_path: to initialize this object with a
            current path value different that its default, provide a
            string or Path object here.
        :param change_listeners: a callable or iterable of callables
            that will be notified when the path for this AppFolder
            changes.
        """

        self.name = name
        self.display_name = display_name

        ## default path ##

        self.default_path = None

        # if not None or ""
        if default_path:
            if isinstance(default_path, str):
                self.default_path = Path(default_path)
            elif isinstance(default_path, Path):
                self.default_path = default_path
            ## anything not a str or Path will be ignored.

        ## current path ##

        self.current_path = self.default_path

        if current_path:
            if isinstance(current_path, str):
                self.current_path = Path(current_path)
            elif isinstance(current_path, Path):
                self.current_path = current_path

        ## placeholder for override ##
        self._override=None
        self._override_active=False

        ## listeners, if any ##

        # callables listening for a change in the path
        self._listeners = set()

        if change_listeners is not None:
            if hasattr(change_listeners, '__iter__') and not isinstance(change_listeners, (str, bytes)):
                self._listeners = set(change_listeners)
            elif callable(change_listeners):
                self._listeners = {change_listeners}

    @property
    def path(self):
        """Returns the current path of this folder as a Path object"""
        return self._override if self._override_active else self.current_path

    @path.setter
    def path(self, value):
        """Set the path for this folder to `value`. No validation
        will be performed."""
        self.set_path(value)

    @property
    def spath(self):
        """Returns the current path of this folder as a string"""
        return self.__str__()

    ##=============================================
    ## validation properties
    ##=============================================

    @property
    def is_set(self):
        """Return true if the current path for this folder is any
        value other than None, even if it is not a valid filesystem
        path."""
        return self.path is not None

    @property
    def is_valid(self):
        """Return True iff a path has been set and that path exists
        on the filesystem."""
        return self.is_set and self.path.exists()

    @property
    def is_overriden(self):
        """Return True if an override has been set and is active."""
        return self._override_active

    ##=============================================
    ## magic method overrides
    ##=============================================

    def __str__(self):
        if self.path:
            return str(self.path)
        return ""

    def __repr__(self):
        # returns a representation of the CURRENT state of the object,
        # which is not necessarily the same as its initialization state.
        return "AppFolder(name={0.name}, display_name={0.display_name}, default_path={0.default_path}, current_path={0.current_path}".format(self)

    def __eq__(self, other):
        # can compare with strings, paths, or other AppFolders
        if isinstance(other, (str, bytes)):
            return self.__str__() == other
        elif isinstance(other, AppFolder) or isinstance(other, PurePath):
            return self.__str__() == str(other)
        else:
            return NotImplemented

    def __bool__(self):
        """Shortcut to the ``is_valid`` property"""
        return self.is_valid

    def __iter__(self):
        """
        Iterate over the names (as strings) of the subdirectories
        contained within this appfolder. For path objects or all files,
        use the ``iter_contents()`` method
        """
        if not self.path or not self.path.exists():
            raise StopIteration

        yield from (d.name for d in self.path.iterdir() if d.is_dir())

    ##=============================================
    ## Modification
    ##=============================================

    def _change_current(self, new):
        """internal method for updating the path and notifying listeners"""
        prev=self.spath
        self.current_path = new

        if prev!=self.spath:
            self._notify(prev, self.spath)

    def clear_path(self):
        """Unset this path. Do not revert to the default path even if
        there is one."""
        self._change_current(None)

    def reset_path(self):
        """Reset to the default path. If there is no default,
        clears the path."""
        self._change_current(self.default_path)

    def set_path(self, new_path, validate=False):
        """

        :param new_path: New path location to point to. If this is passed
            as None, an empty string, or some other False-like value,
            reset the path to default (to clear the path completely
            without resetting to default, use ``clear_path()``)
        :param validate: If True, check that `new_path` exists before
            updating.
        :return: True if the path was updated, False if not
        """

        # if new_path is None or "" or something, reset to default
        # path.

        # print("<==Folder["+self.name+"].set_path("+repr(new_path)+")")

        if not new_path:
            self.reset_path()
            # return True
        else:
            _new = Path(new_path)

            if not validate or _new.exists():
                self._change_current(_new)

    def set_override(self, path, validate=False):
        """
        While this override is active, `path` will be returned as the
        value of this AppFolder rather than whatever is set as the
        current path. The value of the current path will not, however,
        be forgotten, and can be reverted to by calling remove_override().

        Triggers a change notification.

        :param path:
        :param validate:
        """

        prev=self.spath

        if not path:
            self._override = None
        else:
            self._override = Path(path)

        self._override_active = True

        # dont notify if override is same as current
        if prev!=self.spath:
            self._notify(prev, self.spath)


    def remove_override(self):
        """Deactivate the current override and revert to ``current_path``"""
        if self._override_active:
            self._override_active = False
            if self.current_path!=self._override:
                self._notify(self._override, self.current_path)



    ##=============================================
    ## Other methods
    ##=============================================

    def get_path(self, ignore_override=True, as_string=True):
        """Like the ``path`` property, but by default ignores any
        profile override that has been set. Set `ignore_override` to
        False to change this behavior.

        :param ignore_override:
        :param as_string:
        :return: The current path for this appfolder as a Path object
            (or as a string if `as_string` is True; in this case, an
            unset value will be returned as "", rather than None
            or an empty Path).
        """

        if ignore_override or not self._override_active:
            ret=self.current_path
        else:
            ret=self._override

        if as_string:
            return "" if ret is None else str(ret)
        return ret

    def get_default(self, as_string=True):
        """
        Return the default path for this AppFolder.

        :param as_string: if True, return the path as a string rather
            than a Path object. In this case, an unset path will return
            "".
        """

        if as_string:
            return "" if self.default_path is None else str(self.default_path)
        return self.default_path


    def move(self, new_path, remove_old=False, as_override=False):
        """
        Update this folder's path to point to `new_path` on the
        filesystem, which must either not exist or be an empty
        directory. If this AppFolder currently contains data, move that
        data to the new location. If `remove_old` is True, also remove
        the (empty) old directory upon successfully transferring the
        data.

        :raises skymodman.exceptions.FileDeletionError:
            if the old path could not be removed
            for some reason, but all data was successfully transferred
            to the new location. The path WILL still be updated to
            `new_path` if this error occurs.
        :raises skymodman.exceptions.FileAccessError:
            if there is a problem with the
            destination directory. No data will be copied in this case,
            and the path will not updated.
        :raises skymodman.exceptions.MultiFileError:
            This means that some or all data within the current
            directory could not be moved to the new location. The path
            will NOT be updated to `new_path` in this case, but
            depending on the errors, some data may have been transferred
            there.

        """

        if not new_path:
            raise ValueError("new_path must have a valid value, not '{}'".format(new_path))

        try:
            fsutils.move_dir_contents(self.spath, str(new_path),
                                      remove_old)
        except FileDeletionError:
            # if the only error was that the old folder could not be
            # deleted, go ahead and update the current value of the path
            self.set_path(new_path, False)
            # then re-raise the error
            raise

        # all other exceptions will propagate up

        # but if there were no other errors, set the path
        if not as_override:
            self.set_path(new_path, False)
        else:
            self.set_override(new_path, False)

    def iter_contents(self, dirs_only=False):
        """
        Return an iterator over the contents of this folder; contents
        will be returned as path objects.
        """
        if not self.path or not self.path.exists():
            raise StopIteration
        if dirs_only:
            yield from (d for d in self.path.iterdir() if d.is_dir())
        else:
            yield from self.path.iterdir()

    ##=============================================
    ## change-event listeners
    ##=============================================

    def register_change_listener(self, listener):
        """`listener` should be a callable; it will be invoked with this
        AppFolder instance as its first positional parameter upon
        a path change"""
        # """
        # `listener` should be a callable that accepts 3 parameters;
        # it will be invoked as ``listener(appfolder, old_path, new_path)``,
        # where appfolder is this AppFolder instance, and old_path/new_path
        # are strings.
        # """

        if callable(listener):
            self._listeners.add(listener)

    def remove_listener(self, listener):
        """Remove a listener by providing the same callable object
        that was used to register it"""
        self._listeners.discard(listener)

    def _notify(self, old, new):
        """Invoke--in no particular or guaranteed order--all registered
         change-listeners with the change information"""
        for l in self._listeners:
            l(self)
            # l(self, old, new)
