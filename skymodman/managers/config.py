import configparser
import os
from pathlib import Path
from copy import deepcopy
from collections import defaultdict

import appdirs

from skymodman import exceptions
from skymodman.managers import Submanager
from skymodman.utils import withlogger, fsutils
from skymodman.utils.fsutils import check_path
from skymodman.constants import EnvVars, FALLBACK_PROFILE, keystrings, APPNAME, PROFILES_DIRNAME, MAIN_CONFIG

# for convenience and quicker lookup
_SECTION_GENERAL = keystrings.Section.GENERAL
_SECTION_DIRS = keystrings.Section.DIRECTORIES

_KEY_LASTPRO = keystrings.INI.LASTPROFILE
_KEY_DEFPRO  = keystrings.INI.DEFAULT_PROFILE
_KEY_PROFDIR = keystrings.Dirs.PROFILES
_KEY_MODDIR  = keystrings.Dirs.MODS
_KEY_VFSMNT  = keystrings.Dirs.VFS
_KEY_SKYDIR  = keystrings.Dirs.SKYRIM

## config file schema (and default values) ##
# MAIN_CONFIG = "skymodman.ini"
# PROFILES_DIRNAME = "profiles"
# APPNAME =

_DEFAULT_CONFIG_={
    _SECTION_GENERAL: {
        _KEY_LASTPRO: FALLBACK_PROFILE,
        _KEY_DEFPRO:  FALLBACK_PROFILE
    },
    _SECTION_DIRS: {
        _KEY_PROFDIR: appdirs.user_config_dir(APPNAME) + "/profiles",
        _KEY_SKYDIR: "",
        _KEY_MODDIR: appdirs.user_data_dir(APPNAME) +"/mods",
        _KEY_VFSMNT: appdirs.user_data_dir(APPNAME) +"/skyrimfs",
    }
}


# _pathvars = ("file_main", "dir_config", "dir_data", "dir_profiles", "dir_mods", "dir_vfs", "dir_skyrim")

# class ConfigPaths:
#     __slots__=("file_main", "dir_config", "dir_data", "dir_profiles", "dir_mods", "dir_vfs", "dir_skyrim")
#
#     def __init__(self, *, file_main=None, dir_config=None, dir_data=None, dir_mods=None, dir_profiles=None, dir_skyrim=None, dir_vfs=None) :
#         """
#
#         :param Path file_main:
#         :param Path dir_config:
#         :param Path dir_data:
#         :param Path dir_mods:
#         :param Path dir_profiles:
#         :param Path dir_skyrim:
#         :param Path dir_vfs:
#         """
#
#         self.file_main    = file_main
#         self.dir_config   = dir_config
#         self.dir_data     = dir_data
#         self.dir_mods     = dir_mods
#         self.dir_profiles = dir_profiles
#         self.dir_skyrim   = dir_skyrim
#         self.dir_vfs      = dir_vfs
#
#     def __getitem__(self, config_file_or_dir):
#         """
#         Use dict-access to get the string version of a stored path.
#         E.g.: paths['dir_mods'] -> '/path/to/mod/install/directory'
#
#         :param str config_file_or_dir:
#         :return: the path as a string or "" if the item was not found (or was None)
#         """
#
#         path = self._getpath(config_file_or_dir)
#         return str(path) if path else ""
#
#     def __setitem__(self, key, value):
#         """
#         Use dict-like access to update the stored paths. If key is invalid,
#         no changes will be made
#
#         :param str key:
#         :param Path value:
#         """
#
#         if key in ConfigPaths.__slots__:
#             if isinstance(value, str):
#                 setattr(self, key, Path(value))
#             else:
#                 setattr(self, key, value)
#
#     def _getpath(self, item) -> Path:
#         """
#         Get a Path object stored in this instance by property name.
#         :param str item:
#         :return: str(path) or "" if not found or None
#         """
#         if item in ConfigPaths.__slots__:
#             return getattr(self, item, None)
#         return None


# @humanize
@withlogger
class ConfigManager(Submanager):

    def __init__(self, *args):
        super().__init__(*args)

        # self.paths = ConfigPaths()

        self.paths = self.mainmanager.Paths

        # keep a dictionary that is effectively an in-memory version
        # of the main config file
        self.currentValues = deepcopy(_DEFAULT_CONFIG_)

        # track errors encountered while loading paths
        self.path_errors=defaultdict(list)

        # list of MissingConfigKeyError exceptions
        self.missing_keys = []

        # hold all environment variables and their values (if any) here.
        self._environment = {k:os.getenv(k, "") for k in EnvVars}

        # read config file, make sure all required data is present or at default
        self.ensure_default_setup()

    # @property
    # def paths(self) -> ConfigPaths:
    #     """
    #     :return: object containing Path objects for all the main configuration directories and files
    #     """
    #     return self.paths


    def __getitem__(self, config_var):
        """
        Use dict-access to get the value of any of items in this config instance by property name. E.g:

        >>> config['dir_mods']
        '/path/to/mod/install/directory'
        >>> config['last_profile']
        'default'

        :param str config_var:
        :return: the value or None if the value/key cannot be found
        """
        # if config_var in _pathvars:
        #     return self.paths[config_var]

        # since our keys are (as of right now) all unique (the sections
        # are more of a visual aid than anything else), take advantage
        # of that fact to track down the requested value
        for s in self.currentValues.values():
            if config_var in s.keys():
                return s[config_var]

        # if all else fails return none
        return None

    @property
    def last_profile(self) -> str:
        """
        :return: Name of most recently active profile
        """
        return self.currentValues[_SECTION_GENERAL][_KEY_LASTPRO]

    @last_profile.setter
    def last_profile(self, name):
        """
        Set `name` as the value of the 'lastproifile;' cobfig key
        and write the change to the configuration file

        :param name:
        """
        self.currentValues[_SECTION_GENERAL][_KEY_LASTPRO] = name
        self._save_value(_SECTION_GENERAL, _KEY_LASTPRO, name)

    @property
    def default_profile(self):
        """
        :return: Name of the profile marked as default
        """
        return self.currentValues[_SECTION_GENERAL][_KEY_DEFPRO]

    @default_profile.setter
    def default_profile(self, name):
        """
        Set `name` as the valuie of the 'default_profile' config key
        and write the change to tghe configuration file
        :param str name:
        """
        self.currentValues[_SECTION_GENERAL][_KEY_DEFPRO] = name
        self._save_value(_SECTION_GENERAL, _KEY_DEFPRO, name)


    @property
    def env(self):
        """
        :return: the dictionary containing the defined environment variables
        """
        return self._environment

    def getenv(self, var):
        """

        :param var:
        :return: the value of the environment variable specified by `var`
        """
        return self._environment[var]

    ##=============================================
    ## Setup and Sanity Checks
    ##=============================================

    def ensure_default_setup(self):
        """
        Make sure that all the required files and directories exist,
        creating them if not.
        """

        ## set up paths ##

        ##=================================
        ## Main Config dir/file
        ##---------------------------------

        # get the path to the our folder within the user's configuration directory
        # (e.g. ~/.config), using appdirs
        self.paths.dir_config = Path(appdirs.user_config_dir(APPNAME))
        ## check that config dir exists, create if missing ##
        self._check_path_exist(self.paths.dir_config, True)

        ## check that main config file exists ##
        self._check_main_config()

        ## Load settings from main config file ##
        config = configparser.ConfigParser()
        config.read(self.paths['file_main'])

        ##=================================
        ## Profile Directory
        ##---------------------------------

        ## get the configured or default profiles directory:
        # path to directory which holds all the profile info
        # TODO: should this stuff actually be in XDG_DATA_HOME??
        try:
            self.paths.dir_profiles = Path(config[_SECTION_DIRS][_KEY_PROFDIR])
        except KeyError:
            self.missing_keys.append(exceptions.MissingConfigKeyError(_KEY_PROFDIR, _SECTION_DIRS))

            self.LOGGER.warning("Key for profiles directory missing; using default.")
            self.paths.dir_profiles = Path(_DEFAULT_CONFIG_[_SECTION_DIRS][_KEY_PROFDIR])

        ## check that profiles dir exists, create if missing ##
        if not self._check_dir_exist('dir_profiles', True):
            # if it was missing, also create the folder for the default/fallback profile
            self.LOGGER.info("Creating directory for default profile.")
            (self.paths.dir_profiles / FALLBACK_PROFILE).mkdir()


        ##=================================
        ## Last/Default profile
        ##---------------------------------

        # store {last,default} profile in local clone

        for key in (_KEY_LASTPRO, _KEY_DEFPRO):
            try:
                # attempt to load saved values from config
                self.currentValues[_SECTION_GENERAL][key] = self._load_config_value(config, _SECTION_GENERAL, key)

            except exceptions.MissingConfigKeyError as e:
                self.missing_keys.append(e)
                self.LOGGER << "setting "+key+" to default value"
                self.currentValues[_SECTION_GENERAL][key] = FALLBACK_PROFILE

            finally:
                # and now check that the folders for those dirs exist
                self._check_for_profile_dir(key)


        ##=================================
        ## Game-Data Storage Folders*
        ##---------------------------------

        # *&c.

        ## load stored paths of game-data folders
        ## |-> this loads dir_mods, dir_skyrim, dir_vfs
        self._load_data_dirs(config)

        ## check that mods directory exists, but only create it if the
        # location in the config is same as the default
        self._check_dir_exist('dir_mods',
                              create=self.paths['dir_mods'] ==
                                     _DEFAULT_CONFIG_[_SECTION_DIRS]
                                     [_KEY_MODDIR])

        ## and finally, let's fill in any blank spots in the config.
        ## note that this does NOT overwrite any _invalid_ settings,
        ## non-existing paths, etc. It just fills in the missing
        ## keys with default values. That way, a user may be able
        ## to manually correct an invalid path (say, their external
        ## drive was unmounted) without having to reconfigure the
        ## application afterwards.

        if self.missing_keys:
            for e in self.missing_keys:
                s, k = e.section, e.key

                # check if the section itself is missing
                if s not in config:
                    config[s] = {}

                config[s][k] = self.currentValues[s][k]

            with self.paths.file_main.open('w') as f:
                config.write(f)

    def _check_path_exist(self, path, create=False):
        """

        :param path: Path object
        :param create: if True and path does not exist, create it and
            any required parent directories.
        :return:
        """

        # if path is unset, there's not much we can do
        if not path:
            raise TypeError("path must not be None")

        if not path.exists():
            self.LOGGER.warning("{} not found.".format(path))

            if create:
                self.LOGGER.info("Creating {}".format(path))
                path.mkdir(parents=True)

            return False

        return True

    def _check_dir_exist(self, which, create=False):
        """
        Given a known configuration/data directory, check that it exists
         and create it if it doesn't

        :param which: key string for directory
        :param bool create: if True and the directory does not exist, create it and any required parents dirs
        :return: True if the directory existed, False if it did not/had to be created, None if it was unset
        """

        p = self.paths.path(which)

        try:
            return self._check_path_exist(p, create)
        except TypeError:
            raise exceptions.ConfigValueUnsetError(which, _SECTION_DIRS)

        # if path is unset, there's not much we can do
        # if not p:
        #     raise exceptions.ConfigValueUnsetError(which, _SECTION_DIRS)
        #
        # if not p.exists():
        #     self.LOGGER.warning("{} not found.".format(which))
        #
        #     if create:
        #         self.LOGGER.info("Creating {} at: {}".format(which, p))
        #         p.mkdir(parents=True)
        #
        #     return False
        #
        # return True


    def _check_main_config(self):
        """
        Ensure main configuration file exists, creating if necessary
        """

        self.paths.file_main = self.paths.dir_config / MAIN_CONFIG

        ## check that main config file exists ##
        if not self.paths.file_main.exists():
            self.LOGGER.info("Creating default configuration file.")
            # create it w/ default values if it doesn't
            self.create_default_config()

    def _check_for_profile_dir(self, key):
        """
        Check that profile for the given key (last or default) exists.
        If it doesn't, fallback to the fallback profile for that one.

        :param key:
        """
        pname = self.currentValues[_SECTION_GENERAL][key]
        pdir = self.paths.dir_profiles / pname

        if not pdir.exists():
            self.LOGGER.warning("{}: Profile directory '{}' not found".format(key, pname))

            # if the profile is not already the default, set it so.
            if pname != FALLBACK_PROFILE:
                self.LOGGER << "falling back to default."
                self.currentValues[_SECTION_GENERAL][
                    key] = FALLBACK_PROFILE
                # and go ahead and recurse this once,
                # to ensure that the default folder is created
                self._check_for_profile_dir(key)
            else:
                self.LOGGER << "creating default profile directory"
                # if it is the default, create the directory
                pdir.mkdir()

    def _load_data_dirs(self, config):
        """
        Lookup the paths for the directories of game-related data (e.g.
        the main Skyrim folder, the mods-installation directory, and the
        virtual fs mount point). If the user has not configured these, use
        the default.

        :param configparser.ConfigParser config:
        """

        for evar, path_key in (
                (EnvVars.SKYDIR, _KEY_SKYDIR),
                (EnvVars.MOD_DIR, _KEY_MODDIR),
                (EnvVars.VFS_MOUNT, _KEY_VFSMNT),
        ):
            p = None  # type: Path

            # first, check if the user has specified an environment variable
            envval = self._environment[evar]
            if envval:
                if check_path(envval):
                    p = Path(envval)
                else:
                    self.path_errors[path_key].append(envval)

            # if they didn't or it didn't exist, pull the config value
            if p is None:
                try:
                    config_val = self._load_config_value(config, _SECTION_DIRS, path_key)
                except exceptions.MissingConfigKeyError as e:
                    self.missing_keys.append(e)
                else:
                    if check_path(config_val):
                        p = Path(config_val)
                    else:
                        self.path_errors[path_key].append(config_val)

            if p is None:
                # if key wasn't in config file for some reason,
                # check that we have a default value (skydir, for example,
                # does not (i.e. the default val is ""))
                def_path = _DEFAULT_CONFIG_[_SECTION_DIRS][
                        path_key]

                # if we have a default and it exists, use that.
                # otherwise log the error
                if check_path(def_path):
                    p = Path(def_path)
                else:
                    # noinspection PyTypeChecker
                    self.path_errors[path_key].append(
                        "default invalid: '{}'".format(def_path))

            # finally, if we have successfully deduced the path, set
            # it on the PathManager
            if p is not None:
                ## use setattr to avoid circular reference during setup
                setattr(self.paths, path_key, p)

            # update config-file mirror
            self.currentValues[_SECTION_DIRS][path_key] = self[path_key]

        if self.path_errors:
            for att, errlist in self.path_errors.items():
                for err in errlist:
                    self.LOGGER << "Path error [" + att + "]: " + err

        ######################################################################
        #  check env for vfs mount
        ## THIS IS ALREADY DONE ABOVE; just preserving the notes down here...


        # env_vfs = os.getenv(EnvVars.VFS_MOUNT)

        # check to see if the given path is a valid mount point
        # todo: this is assuming that the vfs has already been mounted manually; I'd much rather do it automatically, so I really should just check that the given directory is empty
        # if check_path(env_vfs) and os.path.ismount(env_vfs):
        #     self.paths.dir_vfs = Path(env_vfs)
        # else:
        #     self.paths.dir_vfs = Path(config[_SECTION_GENERAL][_KEY_VFSMNT])

    def _load_config_value(self, config, section, key):
        """
        Loads the saved data for "last_profile" and "default_profile"

        :param configparser.ConfigParser config:
        """
        try:
            return config[section][key]
        except KeyError as e:
            self.LOGGER.error(repr(e))
            raise exceptions.MissingConfigKeyError(key, section) from e

        ## just load in the saved value; other parts of the program
        ## can check the environment


    def create_default_config(self):
        """
        Called if the main configuration file does not exist in the expected location.
        Creates 'skymodman.ini' with default values
        """
        #TODO: perhaps just include a default config file and copy it in place.

        self.LOGGER << "Creating default configuration file"

        config = configparser.ConfigParser()

        # construct the default config
        for section,vallist in _DEFAULT_CONFIG_.items():
            config[section] = {}
            for prop, value in vallist.items():
                config[section][prop] = value

        with self.paths.file_main.open('w') as configfile:
            config.write(configfile)

    def update_dirpath(self, path_key):
        """
        Update the saved value of a configurable directory path
        using the current value from the PathManager (thus the
        PathManager should be updated first; actually, this is called
        from the PathManager itself, so all path changes should go
        through there and one need not worry about ever calling this
        method directly.
        """
        if path_key in _DEFAULT_CONFIG_[_SECTION_DIRS]:
            self._update_value(_SECTION_DIRS, path_key, self.paths[path_key])
        else:
            raise exceptions.InvalidConfigKeyError(path_key,
                                                   _SECTION_DIRS)

    def update_genvalue(self, key, value):
        """
        Update the value of a General setting

        :param key:
        :param value:
        :return:
        """

        if key in _DEFAULT_CONFIG_[_SECTION_GENERAL]:
            self._update_value(_SECTION_GENERAL, key, value)
        else:
            raise exceptions.InvalidConfigKeyError(key, _SECTION_GENERAL)

    def update_config(self, key, section, value):
        """
        Update saved configuration file

        :param  value: the new value to set
        :param str key: which key will will be set to the new value
        :param str section: valid values are "General" and "Directories" (or the enum value)
        """

        # validate new value against schema
        try:
            _DEFAULT_CONFIG_[section][key]
        except KeyError as e:
            raise exceptions.InvalidConfigKeyError(key, section) from e

        self._update_value(section, key, value)

        # get new configurator
        # config = configparser.ConfigParser()
        # populate with current values

        # because we don't want to overwrite saved config values with
        # session-temporary values (e.g. from ENV vars or cli-options),
        # we read the saved data from disk again.
        # config.read(self.paths['file_main'])

        # if section == _SECTION_DIRS:
        #     # means we're updating a data path
        #     self.paths[key] = value

            # if value is e.g. an empty string, clear the setting
            # p=Path(value) if value else None

            # leave verification to someone else...
            # if check_path(str(p)):

            # self.paths[key] = p

            # update the ConfigPaths object
            # for case in [key.__eq__]:
            #     if case(_KEY_MODDIR):
            #         self.paths.dir_mods = p
            #     elif case(_KEY_VFSMNT):
            #         self.paths.dir_vfs = p
            #     elif case(_KEY_SKYDIR):
            #         self.paths.dir_skyrim = p

        # elif section == _SECTION_GENERAL:
            # means we're setting either the default or most-recent profile
            # p = self.paths.dir_profiles / value



            # elif case(_KEY_LASTPRO) or case(_KEY_DEFPRO):
            #     self.currentValues[_SECTION_GENERAL][key] = value
                # self.last_profile = value

        # else: # should always run since we didn't use 'break' above

        # now insert new value into saved config
        # config[section][key] = value
        # self.currentValues[section][key] = value
        #
        # # else:
        # #     raise FileNotFoundError(filename=value)
        #
        #
        # # write the new data to disk
        # # todo: maybe this operation should be async? Maybe it already is?
        # with self.paths.file_main.open('w') as f:
        #     config.write(f)

    def _update_value(self, section, key, value):
        """
        Save a value to the config file and also update the local
        config mirror.

        :param section:
        :param key:
        :param value:
        """

        self._save_value(section, key, value)
        self.currentValues[section][key] = value


    def _save_value(self, section, key, value):
        """
        Update thje config file with a single value.
        Performs no validation or error-handling.
        Only meant to be called internally

        :param section:
        :param key:
        :param value:
        :return:
        """
        config = configparser.ConfigParser()

        config.read(self.paths['file_main'])

        config[section][key] = value

        with self.paths.file_main.open('w') as f:
            config.write(f)

    def move_dir(self, dir_label, destination, remove_old_dir=True):
        """
        Change the storage path for the given directory and move the
        current contents of that directory to the new location.

        :param dir_label: label (e.g. 'dir_mods') for the dir to move
        :param str destination: where to move it
        :raises: ``exceptions.FileAccessError`` if the destination exists and is not an empty directory, or if there is an issue with removing the original directory after the move has occurred. If errors occur during the move operation itself, an ``exceptions.MultiFileError`` will be raised. The ``errors`` attribute on this exception object is a collection of tuples for each file that failed to copy correctly, containing the name of the file and the original exception.
        :param remove_old_dir: if True, remove the original directory from disk after
            moving all its contents
        """
        curr_path = self.paths.path(dir_label)

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

            if len(os.listdir(destination)) > 0:
                raise exceptions.FileAccessError(destination, "The directory '{file}' must be nonexistent or empty.")
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

        if copy_contents:
            for item in curr_path.iterdir():
                # move all items inside the new path
                try:
                    fsutils.move_path(item, new_path)
                except (OSError, exceptions.FileAccessError) as e:
                    self.LOGGER.error(e)
                    errors.append((item, e))

            ## after all that, we can remove the old dir...hopefully
            if remove_old_dir and not errors:
                try:
                    curr_path.rmdir()
                except OSError as e:
                    raise exceptions.FileAccessError(curr_path, "The original directory '{file}' could not be removed") from e
        else:
            # new_path does not exist, so we can just move the old dir to the destination
            try:
                fsutils.move_path(curr_path, new_path)
            except (OSError, exceptions.FileAccessError) as e:
                self.LOGGER.error(e)
                errors.append((curr_path, e))

        if errors:
            raise exceptions.MultiFileError(errors, "Errors occurred during move operation.")


    def list_mod_folders(self):
        """
        Just get a list of all mods installed in the mod directory
        (i.e. a list of folder names)

        :return: list of names
        """
        self.LOGGER.info("Getting list of mod directories from {}".format(self.paths['dir_mods']))
        return os.listdir(self.paths['dir_mods'])


