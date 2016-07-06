import configparser
import os
from pathlib import Path
from copy import deepcopy
from collections import defaultdict

import appdirs

from skymodman import exceptions
from skymodman.utils import withlogger
from skymodman.utils.fsutils import checkPath
# from skymodman.managers import modmanager as Manager
from skymodman.constants import (EnvVars, INISection, KeyStr)

# bind these values locally, since we need the actual string more often than not here
_SECTION_GENERAL = INISection.GENERAL.value
_SECTION_DIRS = INISection.DIRECTORIES.value

# for convenience
_KEY_LASTPRO = KeyStr.INI.LASTPROFILE
_KEY_DEFPRO  = KeyStr.INI.DEFAULT_PROFILE
_KEY_PROFDIR = KeyStr.Dirs.PROFILES
_KEY_MODDIR  = KeyStr.Dirs.MODS
_KEY_VFSMNT  = KeyStr.Dirs.VFS
_KEY_SKYDIR  = KeyStr.Dirs.SKYRIM

## config file schema (and default values) ##
_MAIN_CONFIG_ = "skymodman.ini"
_FALLBACK_PROFILE_ = "default"
_PROFILES_DIRNAME_ = "profiles"
_APPNAME_ = "skymodman"

_DEFAULT_CONFIG_={
    _SECTION_GENERAL: {
        _KEY_LASTPRO: _FALLBACK_PROFILE_,
        _KEY_DEFPRO:  _FALLBACK_PROFILE_

    },
    _SECTION_DIRS: {
        _KEY_PROFDIR: appdirs.user_config_dir(_APPNAME_) + "/profiles",
        _KEY_SKYDIR: "",
        _KEY_MODDIR: appdirs.user_data_dir(_APPNAME_) +"/mods",
        _KEY_VFSMNT: appdirs.user_data_dir(_APPNAME_) +"/skyrimfs",
    }
}


_pathvars = ("file_main", "dir_config", "dir_data", "dir_profiles", "dir_mods", "dir_vfs", "dir_skyrim")

class ConfigPaths:
    __slots__=("file_main", "dir_config", "dir_data", "dir_profiles", "dir_mods", "dir_vfs", "dir_skyrim")

    def __init__(self, *, file_main=None, dir_config=None, dir_data=None, dir_mods=None, dir_profiles=None, dir_skyrim=None, dir_vfs=None) :
        """

        :param Path file_main:
        :param Path dir_config:
        :param Path dir_data:
        :param Path dir_mods:
        :param Path dir_profiles:
        :param Path dir_skyrim:
        :param Path dir_vfs:
        """

        self.file_main    = file_main
        self.dir_config   = dir_config
        self.dir_data     = dir_data
        self.dir_mods     = dir_mods
        self.dir_profiles = dir_profiles
        self.dir_skyrim   = dir_skyrim
        self.dir_vfs      = dir_vfs

    def __getitem__(self, config_file_or_dir):
        """
        Use dict-access to get the string version of a stored path.
        E.g.: paths['dir_mods'] -> '/path/to/mod/install/directory'

        :param str config_file_or_dir:
        :return: the path as a string or "" if the item was not found (or was None)
        """

        path = self._getpath(config_file_or_dir)
        return str(path) if path else ""

    def __setitem__(self, key, value):
        """
        Use dict-like access to update the stored paths. If key is invalid,
        no changes will be made

        :param str key:
        :param Path value:
        """

        if key in ConfigPaths.__slots__:
            if isinstance(value, str):
                setattr(self, key, Path(value))
            else:
                setattr(self, key, value)

    def _getpath(self, item) -> Path:
        """
        Get a Path object stored in this instance by property name.
        :param str item:
        :return: str(path) or "" if not found or None
        """
        if item in ConfigPaths.__slots__:
            return getattr(self, item, None)
        return None


# @humanize
@withlogger
class ConfigManager:

    def __init__(self):
        super().__init__()

        self.__paths = ConfigPaths()

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
        self.ensureDefaultSetup()

    @property
    def paths(self) -> ConfigPaths:
        """
        :return: object containing Path objects for all the main configuration directories and files
        """
        return self.__paths


    def __getitem__(self, config_var):
        """
        Use dict-access to get the value of any of items in this config instance by property name. E.g:

        >>> config['dir_mods']
        '/path/to/mod/install/directory'
        >>> config['lastprofile']
        'default'

        :param str config_var:
        :return: the value or None if the value/key cannot be found
        """
        if config_var in _pathvars:
            return self.paths[config_var]

        # since our keys are (as of right now) all unique (the sections
        # are more of a visual aid than anything else), take advantage
        # of that fact to track down the requested value
        for s in self.currentValues.values():
            if config_var in s.keys():
                return s[config_var]

        # if all else fails return none
        return None

    @property
    def lastprofile(self) -> str:
        """
        :return: Name of most recently active profile
        """
        return self.currentValues[_SECTION_GENERAL][_KEY_LASTPRO]

    @lastprofile.setter
    def lastprofile(self, value):
        self.currentValues[_SECTION_GENERAL][_KEY_LASTPRO] = value

    @property
    def default_profile(self):
        """
        :return: Name of the profile marked as default
        """
        return self.currentValues[_SECTION_GENERAL][_KEY_DEFPRO]

    @default_profile.setter
    def default_profile(self, value):
        self.currentValues[_SECTION_GENERAL][_KEY_DEFPRO] = value

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

    def ensureDefaultSetup(self):
        """
        Make sure that all the required files and directories exist,
        creating them if not.
        """

        ## set up paths ##
        # self._check_default_dirs(self.paths)

        # get the path to the our folder within the user's configuration directory
        # (e.g. ~/.config), using appdirs
        self.paths.dir_config = Path(
            appdirs.user_config_dir(_APPNAME_))

        ## check that config dir exists, create if missing ##
        self._check_dir_exist('dir_config')

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
        if not self._check_dir_exist('dir_profiles'):
            # if it was missing, also create the folder for the default/fallback profile
            self.LOGGER.info("Creating directory for default profile.")
            (self.paths.dir_profiles / _FALLBACK_PROFILE_).mkdir()




        # store {last,default} profile in local clone

        for key in (_KEY_LASTPRO, _KEY_DEFPRO):
            try:
                # attempt to load saved values from config
                self.currentValues[_SECTION_GENERAL][key] = self._load_config_value(config, _SECTION_GENERAL, key)

            except exceptions.MissingConfigKeyError as e:
                self.missing_keys.append(e)
                self.LOGGER << "setting "+key+" to default value"
                self.currentValues[_SECTION_GENERAL][key] = _FALLBACK_PROFILE_

            finally:
                # and now check that the folders for those dirs exist
                self._check_for_profile_dir(key)

        # self.loadConfig()

        ##=================================
        ## Game-Data Storage Folders*
        ##---------------------------------

        # *&c.

        ## load stored paths of game-data folders
        self._load_data_dirs(config)

        ## check that mods directory exists
        # self._check_for_mods_dir()

        ## check that mods directory exists, but only create it if the
        # location in the config is same as the default
        self._check_dir_exist('dir_mods',
                              create=self.paths['dir_mods'] == _DEFAULT_CONFIG_[_SECTION_DIRS][_KEY_MODDIR])

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

                config[s][k] = self.currentValues[s][k]

            with self.paths.file_main.open('w') as f:
                config.write(f)






    # def _check_default_dirs(self, config_paths):
    #     """
    #
    #     :type config_paths: ConfigPaths
    #     """
    #
    #     # get the path to the our folder within the user's configuration directory
    #     # (e.g. ~/.config), using appdirs
    #     config_paths.dir_config = Path(appdirs.user_config_dir(_APPNAME_))
    #
    #     # path to directory which holds all the profile info
    #     # TODO: should this stuff actually be in XDG_DATA_HOME??
    #     config_paths.dir_profiles = config_paths.dir_config / _PROFILES_DIRNAME_
    #
    #     ## check for config dir, create if missing ##
    #     self._check_dir_exist('dir_config')
    #
    #     ## check for profiles dir, create if missing ##
    #     if not self._check_dir_exist('dir_profiles'):
    #         # if it was missing, also create the folder for the default/fallback profile
    #         self.LOGGER.info("Creating directory for default profile.")
    #         (config_paths.dir_profiles / _FALLBACK_PROFILE_).mkdir()


        # if not config_paths.dir_config.exists():
        #     self.LOGGER.warning("Configuration directory not found.")
        #     self.LOGGER.info(
        #         "Creating configuration directory at: {}".format(
        #             config_paths.dir_config))
        #
        #     config_paths.dir_config.mkdir(parents=True)
        #
        ## check for profiles dir, create if missing ##
        # if not config_paths.dir_profiles.exists():
        #     self.LOGGER.info(
        #         "Creating profiles directory at: {}".format(
        #             config_paths.dir_profiles))
        #
        #     config_paths.dir_profiles.mkdir(parents=True)
        #
        #     default_prof = config_paths.dir_profiles / _FALLBACK_PROFILE_
        #
        #     self.LOGGER.info("Creating directory for default profile.")
        #     default_prof.mkdir()

    def _check_dir_exist(self, which, create=True):
        """
        Given a known configuration/data directory, check that it exists and create it if it doesn't
        :param which:
        :param bool create: if True and the directory does not exist, create it and any required parents dirs
        :return: True if the directory existed, False if it did not/had to be created, None if it was unset
        """

        p = self.paths._getpath(which)

        # if path is unset, there's not much we can do
        if not p:
            raise exceptions.ConfigValueUnsetError(which, _SECTION_DIRS)

        if not p.exists():
            self.LOGGER.warning("{} not found.".format(which))

            if create:
                self.LOGGER.info("Creating {} at: {}".format(which, p))
                p.mkdir(parents=True)

            return False

        return True


    def _check_main_config(self):
        """
        Ensure main configuration file exists, creating if necessary
        """

        self.paths.file_main = self.paths.dir_config / "{}.ini".format(
            _APPNAME_)

        ## check that main config file exists ##
        if not self.paths.file_main.exists():
            self.LOGGER.info("Creating default configuration file.")
            # create it w/ default values if it doesn't
            self.create_default_config()

    def _check_for_mods_dir(self):
        """
        Check that configured directory for mods storage exists. If it does not, only
        create it if the configured is the same as the default path.
        """
        ## TODO: maybe we shouldn't create the mod directory by default?
        dir_mods = self.paths.dir_mods
        if not dir_mods.exists():
            # for now, only create if the location in the config is same as the default
            if str(dir_mods) == _DEFAULT_CONFIG_[_SECTION_DIRS][_KEY_MODDIR]:
                self.LOGGER.info(
                    "Creating new mods directory at: {}".format(
                        dir_mods))

                dir_mods.mkdir(parents=True)
            else:
                self.LOGGER.error("Configured mods directory not found")

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
            if pname != _FALLBACK_PROFILE_:
                self.LOGGER << "falling back to default."
                self.currentValues[_SECTION_GENERAL][
                    key] = _FALLBACK_PROFILE_
                # and go ahead and recurse this once,
                # to ensure that the default folder is created
                self._check_for_profile_dir(key)
            else:
                self.LOGGER << "creating default profile directory"
                # if it is the default, create the directory
                self.pdir.mkdir()




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
                if checkPath(envval):
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
                    if checkPath(config_val):
                        p = Path(config_val)
                    else:
                        self.path_errors[path_key].append(config_val)

            if p is None:
                # if key wasn't in config file for some reason,
                # check that we have a default value (skydir, for example,
                # does not (i.e. the default val is ""))
                def_path = \
                    _DEFAULT_CONFIG_[_SECTION_DIRS][
                        path_key]

                # if we have a default and it exists, use that.
                # otherwise log the error
                # noinspection PyTypeChecker
                if checkPath(def_path):
                    p = Path(def_path)
                else:
                    # noinspection PyTypeChecker
                    self.path_errors[path_key].append(
                        "default invalid: " + def_path)

            # finally, if we have successfully deduced the path, set
            # it on the ConfigPaths object
            if p is not None:
                self.paths[path_key] = p
                # setattr(self.paths, path_key, p)

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
        # if checkPath(env_vfs) and os.path.ismount(env_vfs):
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

        # try:
        #     # save in local clone
        #     self.lastprofile = config[_SECTION_GENERAL][_KEY_LASTPRO]
        # except KeyError as e:
        #     self.LOGGER.error(repr(e))
        #     self.LOGGER << "setting last profile to default value"
        #     self.missing_keys.append((_SECTION_GENERAL, _KEY_LASTPRO))
        #     # it should already be the default value
        #     # self.lastprofile = _FALLBACK_PROFILE_
        #     # self._lastprofile
        #
        # ## same for the default profile:
        # # self.currentValues[_SECTION_GENERAL][_KEY_DEFPRO] =\
        # try:
        #     self.default_profile = config[_SECTION_GENERAL][_KEY_DEFPRO]
        # except KeyError as e:
        #     self.LOGGER.error(repr(e))
        #     self.LOGGER << "setting default profile to default value"
        #     self.missing_keys.append((_SECTION_GENERAL, _KEY_DEFPRO))

    def create_default_config(self):
        """
        Called if the main configuration file does not exist in the expected location.
        Creates 'skymodman.ini' with default values
        """
        #TODO: perhaps just include a default config file and copy it in place.

        config = configparser.ConfigParser()

        # construct the default config
        for section,vallist in _DEFAULT_CONFIG_.items():
            config[section] = {}
            for prop, value in vallist.items():
                config[section][prop] = value

        with self.paths.file_main.open('w') as configfile:
            config.write(configfile)

    # def loadConfig(self):
    #     """
    #     Based on values from defined Environment values (first priority) and settings in config file (second priority), setup the configuration that will be used throughout this session.
    #     """
    #     config = configparser.ConfigParser()
    #     config.read(self.paths['file_main'])
    #
    #     ######################################################################
    #     # allow setting some things via ENV
    #     ######################################################################
    #     # first, the skyrim installation, mod storage, vfs mount
    #
    #     for evar, path_key in (
    #             (EnvVars.SKYDIR, _KEY_SKYDIR),
    #             (EnvVars.MOD_DIR, _KEY_MODDIR),
    #             (EnvVars.VFS_MOUNT, _KEY_VFSMNT),
    #     ):
    #         p = None  # type: Path
    #
    #         # first, check if the user has specified an environment variable
    #         envval = self._environment[evar]
    #         if envval:
    #             if checkPath(envval):
    #                 p = Path(envval)
    #             else:
    #                 self.path_errors[path_key].append(envval)
    #
    #         # if they didn't or it didn't exist, pull the config value
    #         if p is None:
    #             try:
    #                 config_val = config[_SECTION_DIRS][path_key]
    #             except KeyError:
    #                 self.missing_keys.append((_SECTION_DIRS, path_key))
    #                 self.path_errors[path_key].append(
    #                     "config key '" + path_key + "' not found")
    #             else:
    #                 if checkPath(config_val):
    #                     p = Path(config_val)
    #                 else:
    #                     self.path_errors[path_key].append(config_val)
    #
    #         if p is None:
    #             # if key wasn't in config file for some reason,
    #             # check that we have a default value (skydir, for example,
    #             # does not (i.e. the default val is ""))
    #             def_path = \
    #             _DEFAULT_CONFIG_[_SECTION_DIRS][
    #                 path_key]
    #
    #             # if we have a default and it exists, use that.
    #             # otherwise log the error
    #             # noinspection PyTypeChecker
    #             if checkPath(def_path):
    #                 p = Path(def_path)
    #             else:
    #                 # noinspection PyTypeChecker
    #                 self.path_errors[path_key].append(
    #                     "default invalid: " + def_path)
    #
    #         # finally, if we have successfully deduced the path, set
    #         # it on the ConfigPaths object
    #         if p is not None:
    #             self.paths[path_key] = p
    #             # setattr(self.paths, path_key, p)
    #
    #         # update config-file mirror
    #         self.currentValues[_SECTION_DIRS][path_key] = self[path_key]
    #
    #     if self.path_errors:
    #         for att, errlist in self.path_errors.items():
    #             for err in errlist:
    #                 self.LOGGER << "Path error [" + att + "]: " + err
    #
    #     ######################################################################
    #     ######################################################################
    #     # then, which profile is loaded on boot
    #
    #     ## just load in the saved value; other parts of the program
    #     ## can check the environment
    #
    #     try:
    #         # save in local clone
    #         self.lastprofile = config[_SECTION_GENERAL][_KEY_LASTPRO]
    #     except KeyError as e:
    #         self.LOGGER.error(repr(e))
    #         self.LOGGER << "setting last profile to default value"
    #         self.missing_keys.append((_SECTION_GENERAL, _KEY_LASTPRO))
    #         # it should already be the default value
    #         # self.lastprofile = _FALLBACK_PROFILE_
    #         # self._lastprofile
    #
    #     ## same for the default profile:
    #     # self.currentValues[_SECTION_GENERAL][_KEY_DEFPRO] =\
    #     try:
    #         self.default_profile = config[_SECTION_GENERAL][_KEY_DEFPRO]
    #     except KeyError as e:
    #         self.LOGGER.error(repr(e))
    #         self.LOGGER << "setting default profile to default value"
    #         self.missing_keys.append((_SECTION_GENERAL, _KEY_DEFPRO))
    #
    #         # self.default_profile = _FALLBACK_PROFILE_




    def updateConfig(self, key, section, value):
        """
        Update saved configuration file

        :param  value: the new value to set
        :param str key: which key will will be set to the new value
        :param str section: valid values are "General" and "Directories" (or the enum value)
        """

        # new configurator
        config = configparser.ConfigParser()
        # populate with current values
        # config.read_dict(self.currentValues)

        # because we don't want to overwrite saved config values with
        # session-temporary values (e.g. from ENV vars or cli-options),
        # we read the saved data from disk again.
        config.read(str(self.paths.file_main))

        # validate new value
        if section == _SECTION_DIRS and key in [_KEY_MODDIR, _KEY_VFSMNT, _KEY_SKYDIR]:
            # if value is e.g. an empty string, clear the setting
            p=Path(value) if value else None

        # elif section == _SECTION_GENERAL and key == _KEY_LASTPRO:
        elif section == _SECTION_GENERAL and key in [_KEY_LASTPRO, _KEY_DEFPRO]:
            p = self.paths.dir_profiles / value
        else:
            raise exceptions.InvalidConfigKeyError(key, section)

        # leave verification to someone else...
        # if checkPath(str(p)):

        for case in [key.__eq__]:
            if case(_KEY_MODDIR):
                self.paths.dir_mods = p
            elif case(_KEY_VFSMNT):
                self.paths.dir_vfs = p
            elif case(_KEY_SKYDIR):
                self.paths.dir_skyrim = p
            # elif case(_KEY_LASTPRO) or case(_KEY_DEFPRO):
            #     self.currentValues[_SECTION_GENERAL][key] = value
                # self.lastprofile = value

        else: # should always run since we didn't use 'break' above
            # now insert new value into saved config
            config[section][key] = value
            self.currentValues[section][key] = value

        # else:
        #     raise FileNotFoundError(filename=value)


        # write the new data to disk
        # todo: maybe this operation should be async? Maybe it already is?
        with self.paths.file_main.open('w') as f:
            config.write(f)

    def listModFolders(self):
        """
        Just get a list of all mods installed in the mod directory
        (i.e. a list of folder names)

        :return: list of names
        """
        self.LOGGER.info("Getting list of mod directories from {}".format(self.paths.dir_mods))
        return os.listdir(str(self.paths.dir_mods))


