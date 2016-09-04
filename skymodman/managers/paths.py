from pathlib import Path

import appdirs

from skymodman.managers import Submanager
from skymodman.utils import withlogger
from skymodman import constants
from skymodman.constants import keystrings

_pathvars = ("file_main", "dir_config", "dir_data", "dir_profiles", "dir_mods", "dir_vfs", "dir_skyrim")

# these are the directory paths that can be customized by the user
_dirvars = (keystrings.Dirs.MODS,
            keystrings.Dirs.PROFILES,
            keystrings.Dirs.SKYRIM,
            keystrings.Dirs.VFS)

# aaaand these are the directories that can be overriden
# on a per-profile basis
_overridedirs = (keystrings.Dirs.MODS,
            keystrings.Dirs.SKYRIM,
            keystrings.Dirs.VFS)

@withlogger
class PathManager(Submanager):
    """
    Keeps track of all configured paths used within the application.
    """

    def __init__(self, mainmanager, file_main=None, dir_config=None, dir_data=None, dir_mods=None, dir_profiles=None, dir_skyrim=None, dir_vfs=None):
        """

        :param Path file_main:
        :param Path dir_config:
        :param Path dir_data:
        :param Path dir_mods:
        :param Path dir_profiles:
        :param Path dir_skyrim:
        :param Path dir_vfs:
        """

        super().__init__(mainmanager)

        self.file_main    = file_main
        self.dir_config   = dir_config
        self.dir_data     = dir_data
        self.dir_mods     = dir_mods
        self.dir_profiles = dir_profiles
        self.dir_skyrim   = dir_skyrim
        self.dir_vfs      = dir_vfs



    ##=============================================
    ## Getting/setting paths
    ##=============================================

    def path(self, key, use_profile_override=False):
        """
        Get the current value for a given path as a Path object

        :param key:
        :param use_profile_override: If true and the active profile has
            defined an override path for this key, return that value
            instead of the main
        :return: the Path object for the stored value of the
            requested directory
        """

        if use_profile_override:
            p = self.mainmanager.profile
            if p:
                do = p.diroverride(key)
                if do: return Path(do)

        # check that key is a path-key so we aren't returning arbitrary
        # instance attributes
        if key in _pathvars:
            return getattr(self, key, None)
        return None

    def set_path(self, key, value, profile_override=False):
        """
        Set the path for the given directory to `value`. If `key` is
        not a recognized directory key, nothing will be changed
        and no error will be thrown.

        :param key:
        :param value:
        :param profile_override: if True, then the given path key and
            value are set as an override on the current profile and the
            main config is not updated.
        """

        if profile_override:
            if key in _overridedirs and self.mainmanager.profile:
                self.mainmanager.profile.setoverride(key,
                    str(value) if value is not None else "")

            # if profile_override was True but the key was not a valid
            # overrideable directory, we still don't want to update the
            # main config since it was specifically specified not to.

        elif key in _pathvars:

            # we check for str instead of Path so that we can allow
            # setting attrs to values like None (that would fail the
            # isPath check and then would fail to convert to Path).
            if isinstance(value, str):
                # set to None if value is ""
                setattr(self, key, Path(value) if value else None)
            else:
                setattr(self, key, value)

            if key in _dirvars:
                # if it's a configurable directory, make sure
                # it's also recorded in the main Config file.
                self.mainmanager.Config.update_dirpath(key, value)

    def __getitem__(self, key):
        """
        Use dict-access to get the string version of a stored path.
        E.g.: paths['dir_mods'] -> '/path/to/mod/install/directory'

        Raises a keyerror if the key is not recognized.

        :param str key:
        :return: the path as a string or "" if the item was None
        """

        if key in _pathvars:
            p = getattr(self, key)
            # return string value of path if key was valid and path was
            # defined; if path was undefined, return empty str
            return str(p) if p else ""

        # if key invalid, raise KeyError
        raise KeyError(key)

    def __setitem__(self, key, value):
        """
        Like set_path, but can be used with dict-like access. Also
        unlike set_path, raises a KeyError if the given key is not
        recognized

        :param key:
        :param value:
        """

        if key in _pathvars:
            if isinstance(value, str):
                # set to None if value is ""
                setattr(self, key, Path(value) if value else None)
            else:
                setattr(self, key, value)

            if key in _dirvars:
                self.mainmanager.Config.update_dirpath(key, value)
        else:
            raise KeyError(key)

