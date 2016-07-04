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
from skymodman.constants import (EnvVars, INIKey, INISection)

__myname = "skymodman"

# bind these values locally, since we need the actual string more often than not here
_SECTION_GENERAL = INISection.GENERAL.value
_SECTION_DIRS = INISection.DIRECTORIES.value
_KEY_LASTPRO = INIKey.LASTPROFILE.value
_KEY_MODDIR  = INIKey.MODDIR.value
_KEY_VFSMNT  = INIKey.VFSMOUNT.value
_KEY_SKYDIR  = INIKey.SKYRIMDIR.value

class ConfigPaths:
    __slots__=["file_main", "dir_config", "dir_data", "dir_profiles", "dir_mods", "dir_vfs", "dir_skyrim"]

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


# @humanize
@withlogger
class ConfigManager:

    __MAIN_CONFIG = "skymodman.ini"
    __DEFAULT_PROFILE = "default"
    __PROFILES_DIRNAME = "profiles"
    __APPNAME = "skymodman"

    __DEFAULT_CONFIG={
        _SECTION_GENERAL: {
            _KEY_LASTPRO: __DEFAULT_PROFILE
        },
        _SECTION_DIRS: {
            _KEY_SKYDIR: "",
            _KEY_MODDIR: appdirs.user_data_dir(__APPNAME) +"/mods",
            _KEY_VFSMNT: appdirs.user_data_dir(__APPNAME) +"/skyrimfs",
        }
    }

    def __init__(self):
        super().__init__()

        self.__paths = ConfigPaths()
        self._lastprofile = None # type: str

        # keep a dictionary that is effectively an in-memory version of the main config file
        self.currentValues = deepcopy(ConfigManager.__DEFAULT_CONFIG)

        # track errors encountered while loading paths
        self.path_errors=defaultdict(list)

        self.ensureDefaultSetup()

    @property
    def paths(self) -> ConfigPaths:
        """
        :return: object containing Path objects for all the main configuration directories and files
        """
        return self.__paths


    def __getitem__(self, config_file_or_dir):
        """
        Use dict-access to get string versions of any of the items from the "paths"
        of this config instance by property name
        E.g.: config['dir_mods'] -> '/path/to/mod/install/directory'

        :param str config_file_or_dir:
        :return: str(Path(...)), or None if the item was not found or was actually None
        """
        path = getattr(self.paths, config_file_or_dir, None)
        return str(path) if path else None
        # return str(getattr(self.paths, config_file_or_dir, None))

    @property
    def lastprofile(self) -> str:
        """
        :return: Name of most recently active profile
        """
        return self._lastprofile

    def loadConfig(self):
        """
        Based on values from defined Environment values (first priority) and settings in config file (second priority), setup the configuration that will be used throughout this session.
        """
        config = configparser.ConfigParser()
        config.read(str(self.paths.file_main))

        ######################################################################
        # allow setting some things via ENV
        ######################################################################
        # first, the skyrim installation, mod storage, vfs mount

        for evar, paths_attr, inikey in (
                (EnvVars.SKYDIR, 'dir_skyrim', _KEY_SKYDIR),
                (EnvVars.MOD_DIR, 'dir_mods', _KEY_MODDIR),
                (EnvVars.VFS_MOUNT, 'dir_vfs', _KEY_VFSMNT),
        ):
            p=None #type: Path

            # first, check if the user has specified an environment variable
            envval = os.getenv(evar)
            if envval:
                if checkPath(envval):
                    p=Path(envval)
                else:
                    self.path_errors[paths_attr].append(envval)

            # if they didn't or it didn't exist, pull the config value
            if p is None:
                try:
                    config_val = config[_SECTION_DIRS][inikey]

                    if checkPath(config_val):
                        p = Path(config_val)
                    else:
                        self.path_errors[paths_attr].append(config_val)

                except KeyError:
                    self.path_errors[paths_attr].append("config key '"+inikey+"' not found")


            if p is None:
                # if key wasn't in config file for some reason,
                # check that we have a default value (skydir, for example,
                # does not (i.e. the default val is ""))
                def_path = ConfigManager.__DEFAULT_CONFIG[_SECTION_DIRS][
                    inikey]

                # if we have a default and it exists, use that.
                # otherwise log the error
                # noinspection PyTypeChecker
                if checkPath(def_path):
                    p = Path(def_path)
                else:
                    # noinspection PyTypeChecker
                    self.path_errors[paths_attr].append("default: "+def_path)

            if p is not None:
                setattr(self.paths, paths_attr, p)

            # if checkPath(envval):
            #     setattr(self.paths, paths_attr,
            #         Path(envval))
            # else:
            #     try:
            #         p = Path(config[_SECTION_GENERAL][inikey])
            #     except KeyError:
            #         # if key wasn't in config file for some reason,
            #         # check that we have a default value (skydir, for example, does not (i.e. the default val is ""))
            #         def_path = ConfigManager.__DEFAULT_CONFIG[_SECTION_GENERAL][inikey] # type: str
            #         # if we have a default and it exists, use that.
            #         # otherwise log the error
            #         if checkPath(def_path):
            #             p = Path(def_path)
            #         else:
            #             p=None
            #     finally:
            #         setattr(self.paths, paths_attr, p)
            # update config-file mirror
            self.currentValues[_SECTION_DIRS][inikey] = self[paths_attr]

        if self.path_errors:
            for att, errlist in self.path_errors.items():
                for err in errlist:
                    self.LOGGER << "Path error ["+ att + "]: " + err


        ######################################################################
        ######################################################################
        # then, which profile is loaded on boot

        env_lpname = os.getenv(EnvVars.PROFILE)

        # see if the named profile exists in the profiles dir
        if env_lpname:
            env_lpname = env_lpname.lower() # ignore case
            for p in (d.name for d in self.paths.dir_profiles.iterdir() if d.is_dir()):
                if env_lpname == p.lower():
                    self._lastprofile = p # but make sure we get the proper-cased name here
                    break

        # if it wasn't set above, get the value from config file
        if not self._lastprofile:
            self._lastprofile = config[_SECTION_GENERAL][_KEY_LASTPRO]

        self.currentValues[_SECTION_GENERAL][_KEY_LASTPRO] = self._lastprofile

        ######################################################################
        #  check env for vfs mount

        # env_vfs = os.getenv(EnvVars.VFS_MOUNT)

        # check to see if the given path is a valid mount point
        # todo: this is assuming that the vfs has already been mounted manually; I'd much rather do it automatically, so I really should just check that the given directory is empty
        # if checkPath(env_vfs) and os.path.ismount(env_vfs):
        #     self.paths.dir_vfs = Path(env_vfs)
        # else:
        #     self.paths.dir_vfs = Path(config[_SECTION_GENERAL][_KEY_VFSMNT])


    def ensureDefaultSetup(self):
        """
        Make sure that all the required files and directories exist,
        creating them if not.
        """

        ## set up paths ##

        self._check_default_dirs(self.paths)

        ## check that main config file exists ##
        self._check_main_config(self.paths)

        ## Load settings from main config file ##
        self.loadConfig()

        ## check that mods directory exists
        self._check_for_mods_dir(self.paths)

        ## check that folder for MRU profile exists
        self._check_for_lastprofile_dir(self.paths)

    def _check_default_dirs(self, config_paths):
        """

        :type config_paths: ConfigPaths
        """

        config_paths.dir_config = Path(appdirs.user_config_dir(self.__APPNAME))

        config_paths.dir_profiles = config_paths.dir_config / ConfigManager.__PROFILES_DIRNAME

        ## check for config dir ##
        if not config_paths.dir_config.exists():
            self.LOGGER.warning("Configuration directory not found.")
            self.LOGGER.info(
                "Creating configuration directory at: {}".format(
                    config_paths.dir_config))

            config_paths.dir_config.mkdir(parents=True)

        ## check for profiles dir ##
        if not config_paths.dir_profiles.exists():
            self.LOGGER.info(
                "Creating profiles directory at: {}".format(
                    config_paths.dir_profiles))

            config_paths.dir_profiles.mkdir(parents=True)

            default_prof = config_paths.dir_profiles / ConfigManager.__DEFAULT_PROFILE

            self.LOGGER.info("Creating directory for default profile.")
            default_prof.mkdir()

    def _check_main_config(self, config_paths):
        """
        Ensure main configuration file exists, creating if necessary

        :param config_paths:
        """

        config_paths.file_main = config_paths.dir_config / "{}.ini".format(
            self.__APPNAME)

        ## check that main config file exists ##
        if not config_paths.file_main.exists():
            self.LOGGER.info("Creating default configuration file.")
            # create it w/ default values if it doesn't
            self.create_default_config()

    def _check_for_mods_dir(self, paths):
        ## TODO: maybe we shouldn't create the mod directory by default?
        if not paths.dir_mods.exists():
            # for now, only create if the location in the config is same as the default
            if str(paths.dir_mods) == \
                            appdirs.user_data_dir(
                                self.__APPNAME) + "/mods":

                self.LOGGER.info(
                    "Creating new mods directory at: {}".format(
                        paths.dir_mods))

                paths.dir_mods.mkdir(parents=True)
            else:
                self.LOGGER.error("Configured mods directory not found")

    def _check_for_lastprofile_dir(self, paths):
        """
        See if the directory for the most recently-loaded profile exists;
        if not, set "default" as the MRU profile

        :param paths:
        """

        lpdir = paths.dir_profiles / self._lastprofile
        if not lpdir.exists():
            self.LOGGER.error(
                "Directory for last-loaded profile '{}' could not be found! Falling back to default.".format(
                    self._lastprofile))

            self._lastprofile = self.__DEFAULT_PROFILE

    def create_default_config(self):
        """
        Called if the main configuration file does not exist in the expected location.
        Creates 'skymodman.ini' with default values
        """
        #TODO: perhaps just include a default config file and copy it in place.

        config = configparser.ConfigParser()

        # construct the default config
        for section,vallist in ConfigManager.__DEFAULT_CONFIG.items():
            config[section] = {}
            for prop, value in vallist.items():
                config[section][prop] = value

        with self.paths.file_main.open('w') as configfile:
            config.write(configfile)


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

        elif section == _SECTION_GENERAL and key == _KEY_LASTPRO:
        # elif key == _KEY_LASTPRO:
            p = self.paths.dir_profiles / value
        else:
            raise exceptions.InvalidConfigKeyError(key)

        # leave verification to someone else...
        # if checkPath(str(p)):

        for case in [key.__eq__]:
            if case(_KEY_MODDIR):
                self.paths.dir_mods = p
            elif case(_KEY_VFSMNT):
                self.paths.dir_vfs = p
            elif case(_KEY_SKYDIR):
                self.paths.dir_skyrim = p
            elif case(_KEY_LASTPRO):
                self._lastprofile = value

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


