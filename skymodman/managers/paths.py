import appdirs

from pathlib import Path

from skymodman import constants, exceptions
from skymodman.constants import keystrings, overrideable_dirs, APPNAME
from skymodman.log import withlogger
from skymodman.managers.base import Submanager
from skymodman.utils import fsutils

_pathvars = ("file_main", "dir_config", "dir_data", "profiles", "mods", "vfs", "skyrim")

# these are the directory paths that can be customized by the user
# _dirvars = (keystrings.Dirs.MODS,
#             keystrings.Dirs.PROFILES,
#             keystrings.Dirs.SKYRIM,
#             keystrings.Dirs.VFS)

# aaaand these are the directories that can be overriden
# on a per-profile basis
# _overridedirs = (keystrings.Dirs.MODS,
#             keystrings.Dirs.SKYRIM,
#             keystrings.Dirs.VFS)

@withlogger
class PathManager(Submanager):
    """
    Keeps track of all configured paths used within the application.
    """

    def __init__(self, file_main=None, dir_config=None, dir_data=None,
                 mods=None, profiles=None, skyrim=None, vfs=None,
                 *args, **kwargs):
        """

        :param Path file_main:
        :param Path dir_config:
        :param Path dir_data:
        :param Path mods:
        :param Path profiles:
        :param Path skyrim:
        :param Path vfs:
        """

        ## Defaults if not provided ##

        # in user-config dir

        self.dir_config = Path(appdirs.user_config_dir(APPNAME)) \
            if not dir_config else dir_config

        self.file_main = self.dir_config / constants.MAIN_CONFIG \
            if not file_main else file_main

        self.profiles = Path(self.dir_config, 'profiles') \
            if not profiles else profiles


        # in user-data dir

        self.dir_data = Path(appdirs.user_data_dir(APPNAME)) \
            if not dir_data else dir_data

        self.mods = Path(self.dir_data, 'mods') \
            if not mods else mods

        self.vfs = Path(self.dir_data, 'skyrimfs') \
            if not vfs else vfs

        ## Skyrim folder has no default ##

        self.skyrim   = skyrim

        super().__init__(*args, **kwargs)

    ##=============================================
    ## Path validation
    ##=============================================

    def is_valid(self, key, use_profile_override=True, check_exists=False):
        """

        :param key:
        :param use_profile_override:
        :param check_exists:
        :return:
        """

        try:
            p = self.path(key, use_profile_override)
            return p.exists() if check_exists else True
        except exceptions.InvalidAppDirectoryError:
            return False

    def check_exists(self, key, use_profile=True, create=False):
        """
        Check whether the directory for the given key exists and return
        the result.


        :param key:
        :param create: if `True`, create the directory if it does not
            exist. The final return value will still be False in this
            case.
        :return:
        """

        p = self.path(key, use_profile)

        if create and not p.exists():
            p.mkdir(parents=True)
            return False

        return p.exists()

    ##=============================================
    ## Getting/setting paths
    ##=============================================

    def path(self, key, use_profile_override=True):
        """
        Get the current value for a given path as a Path object.

        Raises InvalidAppDirectoryError if the path is unset

        :param key:
        :param use_profile_override: If true and the active profile has
            defined an override path for this key, return that value
            instead of the main
        :return: the Path object for the stored value of the
            requested directory
        """

        # check that key is a path-key so we aren't returning arbitrary
        # instance attributes
        if key not in _pathvars:
            raise KeyError(key)

        if use_profile_override and key in overrideable_dirs:
            p = self.mainmanager.profile
            if p:
                do = p.diroverride(key)
                if do: return Path(do)

        val = getattr(self, key)

        if not val:
            raise exceptions.InvalidAppDirectoryError(key, None)

        return val

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
            if key in overrideable_dirs and self.mainmanager.profile:
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

            if key in keystrings.Dirs:
                # if it's a configurable directory, make sure
                # it's also recorded in the main Config file.
                self.mainmanager.Config.update_dirpath(key)

    def __getitem__(self, key):
        """
        Use dict-access to get the string version of a stored path.
        E.g.: paths['mods'] -> '/path/to/mod/install/directory'

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

            if key in keystrings.Dirs:
                self.mainmanager.Config.update_dirpath(key, value)
        else:
            raise KeyError(key)

    ##=============================================
    ## Some path manipulation
    ##=============================================

    def list_mod_folders(self, use_profile_override=True):
        """
        Just get a list of all mods installed in the mod directory
        (i.e. a list of folder names)

        :return: list of names
        """

        # allow invaliddir error to propagate
        mpath = self.path(keystrings.Dirs.MODS, use_profile_override)

        self.LOGGER.info("Getting list of mod directories from {}".format(mpath))

        # only return names of folders, not any other type of file
        return [f.name for f in mpath.iterdir() if f.is_dir()]

    def move_dir(self, key, destination, remove_old_dir=True, profile_override=False):
        """
        Change the storage path for the given directory and move the
        current contents of that directory to the new location.

        :param key: label (e.g. 'mods') for the dir to move
        :param str destination: where to move it
        :raises: ``exceptions.FileAccessError`` if the destination
            exists and is not an empty directory, or if there is an
            issue with removing the original directory after the move
            has occurred. If errors occur during the move operation
            itself, an ``exceptions.MultiFileError`` will be raised. The
            ``errors`` attribute on this exception object is a
            collection of tuples for each file that failed to copy
            correctly, containing the name of the file and the original
            exception.
        :param remove_old_dir: if True, remove the original directory
            from disk after moving all its contents
        """
        curr_path = self.path(key, profile_override)

        new_path = Path(destination)

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
                raise exceptions.FileAccessError(destination,
                                                 "'{file}' is not a directory")

            if len(fsutils.listdir(destination)) > 0:
                raise exceptions.FileAccessError(
                    destination,
                    "The directory '{file}' exists and is non-empty.")
            ## dir exists and is empty; easiest thing to do would be to remove
            ## it and move the old folder into its place; though if the dir is a
            ## symlink, that could really mess things up...guess we'll have to do
            ## it one-by-one, then.
            # copy_contents = True

        elif remove_old_dir:
            # The scenario where the destination does not exist and we're
            # removing the original folder is really the only situation
            # in which we can get away with simply moving the original...
            copy_contents=False

        ###########################
        ## actual move operation ##

        if copy_contents:
            for item in curr_path.iterdir():
                # move all items inside the new path
                try:
                    fsutils.move_path(item, new_path)
                except (OSError, exceptions.FileAccessError) as e:
                    self.LOGGER.error(e)
                    errors.append((item, e))

            if not errors:
                # if we managed it without error, update our configured path
                # (want to do it now before any possible errors with
                # removing the old directory)
                self.set_path(key, new_path, profile_override)

                ## after all that, we can remove the old dir...hopefully
                if remove_old_dir :
                    try:
                        curr_path.rmdir()
                    except OSError as e:
                        raise exceptions.FileAccessError(
                            curr_path,
                            "The original directory '{file}' "
                            "could not be removed") from e
        else:
            # new_path does not exist, so we can just move the old dir to the destination
            # (this intrinsically takes care of the 'remove_old_dir' flag)
            try:
                fsutils.move_path(curr_path, new_path)
            except (OSError, exceptions.FileAccessError) as e:
                self.LOGGER.exception(e)
                errors.append((curr_path, e))
            else:
                # if we managed it without error, update our configured path
                self.set_path(key, new_path, profile_override)

        if errors:
            raise exceptions.MultiFileError(errors, "Errors occurred during move operation.")



