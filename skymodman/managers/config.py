import configparser
import os
from pathlib import Path
from enum import Enum
from copy import deepcopy

from skymodman import skylog, utils, exceptions, constants

__myname = "skymodman"

# Messenger Idiom shamelessly pilfered from:
# http://python-3-patterns-idioms-test.readthedocs.org/en/latest/Messenger.html
# (aka "Do I need to use addict anymore?" idiom)
# class Messenger:
#     def __init__(self, **kwargs):
#         self.__dict__ = kwargs


# making these strEnums because I tire of typing .value over and over...
class Section(str, Enum):
    """Only one section at the moment"""
    DEFAULT = "General"
    GENERAL = DEFAULT

class Key(str, Enum):
    LASTPROFILE = "lastprofile"
    MODDIR = "modsdirectory"
    VFSMOUNT = "virtualfsmountpoint"


class ConfigPaths:
    __slots__=["file_main", "dir_config", "dir_data", "dir_profiles", "dir_mods", "dir_vfs"]

    def __init__(self, *, file_main=None, dir_config=None, dir_data=None, dir_profiles=None, dir_mods=None, dir_vfs=None) :
        """

        :param Path file_main:
        :param Path dir_config:
        :param Path dir_data:
        :param Path dir_profiles:
        :param Path dir_mods:
        :param Path dir_vfs:
        """

        self.file_main    = file_main
        self.dir_config   = dir_config
        self.dir_data     = dir_data
        self.dir_profiles = dir_profiles
        self.dir_mods     = dir_mods
        self.dir_vfs      = dir_vfs



@utils.withlogger
class ConfigManager:

    __MAIN_CONFIG = "skymodman.ini"
    __DEFAULT_PROFILE = "default"
    __PROFILES_DIRNAME = "profiles"
    __APPNAME = "skymodman"

    __DEFAULT_CONFIG={
        Section.GENERAL.value: {
            Key.MODDIR.value: "##DATADIR##/mods",
            Key.VFSMOUNT.value: "##DATADIR##/skyrimfs",
            Key.LASTPROFILE.value: __DEFAULT_PROFILE
        }
    }

    def __init__(self, manager):
        """
        :param ModManager manager:
        """
        super().__init__()
        self.manager = manager


        self.__paths = ConfigPaths()
        self._lastprofile = None # type: str

        # keep a dictionary that is effectively an in-memory version of the main config file
        self.currentValues = deepcopy(ConfigManager.__DEFAULT_CONFIG)

        self.ensureDefaultSetup()



    @property
    def paths(self) -> ConfigPaths:
        """
        :return: object containing Path objects for all the main configuration directories and files
        """
        return self.__paths


    def __getitem__(self, config_file_or_dir) -> str:
        """
        Use dict-access to get string versions of any of the items from the "paths"
        of this config instance by property name
        E.g.: config['dir_mods']

        :param str config_file_or_dir:
        :return: str(Path(...))
        """
        return str(getattr(self.paths, config_file_or_dir, None))

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
        # first, the mods dir

        env_md = os.getenv(constants.EnvVars.MOD_DIR)
        if env_md and os.path.exists(env_md):
            self.paths.dir_mods = Path(env_md)
        else:
            self.paths.dir_mods = Path(config[Section.GENERAL][Key.MODDIR])



        ######################################################################
        ######################################################################
        # then, which profile is loaded on boot

        env_lpname = os.getenv(constants.EnvVars.PROFILE)

        # see if the named profile exists in the profiles dir
        if env_lpname:
            env_lpname = env_lpname.lower() # ignore case
            for p in (d.name for d in self.paths.dir_profiles.iterdir() if d.is_dir()):
                if env_lpname == p.lower():
                    self._lastprofile = p # but make sure we get the proper-cased name here
                    break

        # if it wasn't set above, get the value from config file
        if not self._lastprofile:
            self._lastprofile = config[Section.GENERAL][Key.LASTPROFILE]



        ######################################################################
        ######################################################################
        # now check env for vfs mount

        env_vfs = os.getenv(constants.EnvVars.VFS_MOUNT)

        # check to see if the given path is a valid mount point
        # todo: this is assuming that the vfs has already been mounted manually; I'd much rather do it automatically, so I really should just check that the given directory is empty
        if env_vfs and os.path.exists(env_vfs) and os.path.ismount(env_vfs):
            self.paths.dir_vfs = Path(env_vfs)
        else:
            self.paths.dir_vfs = Path(config[Section.GENERAL][Key.VFSMOUNT])

        # update config-file mirror
        self.currentValues[Section.GENERAL.value][Key.MODDIR.value] = str(self.paths.dir_mods)
        self.currentValues[Section.GENERAL.value][Key.VFSMOUNT.value] = str(self.paths.dir_vfs)
        self.currentValues[Section.GENERAL.value][Key.LASTPROFILE.value] = self._lastprofile



    def ensureDefaultSetup(self):
        """
        Make sure that all the required files and directories exist,
        creating them if not.
        """

        ## set up paths ##
        # use XDG_CONFIG_HOME if set, else default to ~/.config
        user_config_dir = os.getenv("XDG_CONFIG_HOME", os.path.expanduser("~/.config"))

        self.paths.dir_config = Path(user_config_dir) / self.__APPNAME

        self.paths.file_main = self.paths.dir_config / "{}.ini".format(self.__APPNAME)

        ## check for config dir ##
        if not self.paths.dir_config.exists():
            self.LOGGER.warning("Configuration directory not found.")
            self.LOGGER.info("Creating configuration directory at: {}".format(self.paths.dir_config))
            self.paths.dir_config.mkdir(parents=True)

        ## check for profiles dir ##

        self.paths.dir_profiles = self.paths.dir_config / ConfigManager.__PROFILES_DIRNAME

        if not self.paths.dir_profiles.exists():
            self.LOGGER.info("Creating profiles directory at: {}".format(self.paths.dir_profiles))
            self.paths.dir_profiles.mkdir(parents=True)

            def_pro = self.paths.dir_profiles / ConfigManager.__DEFAULT_PROFILE

            self.LOGGER.info("Creating directory for default profile.")
            def_pro.mkdir()


        ## check that main config file exists ##
        if not self.paths.file_main.exists():
            self.LOGGER.info("Creating default configuration file.")
            # create it w/ default values if it doesn't
            self.create_default_config()

        ## Load configuration from file ##
        self.loadConfig()


        #check for data dir, mods dir
        ## TODO: maybe we shouldn't create the mod directory by default?
        if not self.paths.dir_mods.exists():
            # for now, only create if the location in the config is same as the default
            if str(self.paths.dir_mods) == \
                    os.path.join(os.getenv("XDG_DATA_HOME",
                                           os.path.expanduser("~/.local/share")),
                                 ConfigManager.__APPNAME,
                                 "mods"):
                self.LOGGER.info("Creating new mods directory at: {}".format(self.paths.dir_mods))
                self.paths.dir_mods.mkdir(parents=True)
            else:
                self.LOGGER.error("Configured mods directory not found")

        # ensure that 'lastprofile' exists in profiles dir, or fallback to default
        lpdir = self.paths.dir_profiles / self._lastprofile
        if not lpdir.exists():
            self.LOGGER.error("Directory for last-loaded profile '{}' could not be found! Falling back to default.".format(self._lastprofile))
            self._lastprofile = self.__DEFAULT_PROFILE


    def create_default_config(self):
        """
        Called if the main configuration file does not exist in the expected location.
        Creates 'skymodman.ini' with default values
        """
        #TODO: perhaps just include a default config file and copy it in place.

        # default data directory
        # TODO: will need to figure something else out if there's ever a need to get this working on a non-linux OS (e.g. OS X)
        default_data_dir = Path(os.getenv("XDG_DATA_HOME",
                                          os.path.expanduser("~/.local/share"))) / ConfigManager.__APPNAME

        config = configparser.ConfigParser()

        # construct the default config, replacing the placeholder with the actual data directory
        for section,vallist in ConfigManager.__DEFAULT_CONFIG.items():
            config[section] = {}
            for prop, value in vallist.items():
                config[section][prop] = value.replace('##DATADIR##', str(default_data_dir))

        with self.paths.file_main.open('w') as configfile:
            config.write(configfile)


    def updateConfig(self, value, key, section=Section.DEFAULT.value):
        """
        Update saved configuration file

        :param  value: the new value to set
        :param str key: which key will will be set to the new value
        :param str section: only valid section is 'General' for the moment
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
        if key in [Key.MODDIR, Key.VFSMOUNT]:
            p=Path(value)

        elif key == Key.LASTPROFILE:
            p = self.paths.dir_profiles / value
        else:
            raise exceptions.InvalidConfigKeyError(key)

        if p.exists() and p.is_dir():

            for case in [key.__eq__]:
                if case(Key.MODDIR):
                    self.paths.dir_mods = p
                elif case(Key.VFSMOUNT):
                    self.paths.dir_vfs = p
                elif case(Key.LASTPROFILE):
                    self._lastprofile = value

            else: # should always run since we didn't use 'break' above
                # now insert new value into saved config
                config[section][key] = value
                self.currentValues[section][key] = value

        else:
            raise FileNotFoundError(filename=value)


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


if __name__ == '__main__':
    # getConfig()

    cm = ConfigManager()

    skylog.stop_listener()