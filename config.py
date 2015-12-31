import configparser
import json
import os
from pathlib import Path
# import logging
import skylog
# from pprint import pprint
from typing import Tuple

from utils import withlogger

__myname = "skymodman"

#
# class LogMixin(object):
#     @property
#     def logger(self):
#         name = '.'.join([__name__, self.__class__.__name__])
#         return skylog.newLogger(name)


# Messenger Idiom shamelessly pilfered from:
# http://python-3-patterns-idioms-test.readthedocs.org/en/latest/Messenger.html
# (aka "Do I need to use addict anymore?" idiom)
class Messenger:
    def __init__(self, **kwargs):
        self.__dict__ = kwargs

@withlogger
class ConfigManager:

    __MAIN_CONFIG = "skymodman.ini"
    __DEFAULT_PROFILE = "default"
    __PROFILES_DIRNAME = "profiles"
    __APPNAME = "skymodman"

    # __DEFAULT_DATADIR = os.path.join(os.getenv("XDG_DATA_HOME", os.path.expanduser("~/.local/share")),__APPNAME)

    def __init__(self, *args, **kwargs):
        super(ConfigManager, self).__init__(*args, **kwargs)
        # self._file,
        self._messenger = None # type: Messenger

        self._main_config = None # type: Path
        self._config_dir = None # type: Path
        self._data_dir = None # type: Path
        self._profiles_dir = None # type: Path
        self._mods_dir = None # type: Path

        self.ensureDefaultSetup()

        # make the configuration variables
        # directly accessible on the ConfigManager
        # for k,v in self._messenger.__dict__.items():
        #     assert k not in self.__dict__
        #     self.__dict__[k] = v


    def ensureDefaultSetup(self):
        """
        Make sure that all the required files and directories exist,
        creating them if not.
        :return:
        """

        ## set up paths ##
        # use XDG_CONFIG_HOME if set, else default to ~/.config
        user_config_dir = os.getenv("XDG_CONFIG_HOME", os.path.expanduser("~/.config"))

        self._config_dir = Path(user_config_dir) / self.__APPNAME
        self._profiles_dir = self._config_dir / "profiles"

        self._main_config = self._config_dir / "{}.ini".format(self.__APPNAME)

        ## check for config dir ##
        if not self._config_dir.exists():
            self.logger.warning("Configuration directory not found.")
            self.logger.info("Creating configuration directory at: {}".format(self._config_dir))
            self._config_dir.mkdir(parents=True)

        ## check for profiles dir ##
        if not self._profiles_dir.exists():
            self.logger.info("Creating profiles directory at: {}".format(self._profiles_dir))
            self._profiles_dir.mkdir(parents=True)
            def_pro = self._profiles_dir / self.__DEFAULT_PROFILE
            def_pro.mkdir()


        ## check that main config exists ##
        if not self._main_config.exists():
            self.logger.info("Creating default configuration file.")
            self.create_default_config()

        ## Load configuration ##
        config = configparser.ConfigParser()
        config.read(str(self._config_dir))

        # i know this isn't the right way to do this... i should get some sleep
        vals = {d: v[d] for k, v in config.items() for d in v}
        self._messenger = Messenger(**vals)
        # print (cm.profile)

        #check for data dir, mods dir
        self._mods_dir = Path(config['General']['modsdirectory'])
        ## TODO: maybe we shouldn't create the mod directory by default?
        if not self._mods_dir.exists():
            # for now, only create if the location in the config is same as the default
            if str(self._mods_dir) == os.path.join(os.getenv("XDG_DATA_HOME", os.path.expanduser("~/.local/share")),
                                                   self.__APPNAME,
                                                   "mods"):
                self.logger.info("Creating new mods directory at: {}".format(self._mods_dir))
                self._mods_dir.mkdir(parents=True)
            else:
                self.logger.error("Configured mods directory not found")




        # make the configuration variables
        # directly accessible on the ConfigManager
        for k, v in self._messenger.__dict__.items():
            assert k not in self.__dict__
            self.__dict__[k] = v






        # check for mod dir

    def create_default_config(self):


        # default data directory
        # TODO: will need to figure something else out if I want this to work on a Mac, too
        default_data_dir = Path(os.getenv("XDG_DATA_HOME", os.path.expanduser("~/.local/share"))) / self.__APPNAME


        config = configparser.ConfigParser()
        config['General'] = {
            'ModsDirectory': default_data_dir / "mods",
            'VirtualFSMountPoint': default_data_dir / "skyrimfs",
        }

        config['State'] = {
            "Profile": self.__DEFAULT_PROFILE
        }

        with self._main_config.open('w') as configfile:
            config.write(configfile)


    def updateConfig(self, section, key, value):
        self._config[section][key] = value

        # todo: verify data before writing
        # also, maybe this operatoin should be queued?
        with open(self._file, "w") as f:
            self._config.write(f)

        ## resync cconfig vars
        self._syncMessenger()

    def _syncMessenger(self):
        """
        (re)syncs the __dict__ of this class with the Messenger
        object that holds the config variables
        :return:
        """

        # make a copy of current messenger keys
        keys = self._messenger.__dict__.keys()

        # remove these keys from this obj's dict
        for k in keys:
            del self.__dict__[k]

        vals = {d: v[d] for k,v in self._config.items() for d in v }
        self._messenger = Messenger(**vals)

        for k,v in self._messenger.__dict__.items():
            assert k not in self.__dict__
            self.__dict__[k] = v

    @property
    def _current_profile_dir(self) -> str:
        _dir = os.path.join(self.profilesdirectory, self.profile)

        if not os.path.exists(_dir):
            self.logger.info("Creating profile directory for {}".format(self.profile))
            os.makedirs(_dir)

        return _dir

    @property
    def _installed_mods_file(self) -> str:
        return os.path.join(self._current_profile_dir, "installed.json")



    def saveModsList(self, mods_by_state: dict):
        """
        Saves to a config file which mods are marked as active in
        the mod-manager
        :param mods_by_state:
        :return:
        """

        with open(self._installed_mods_file, 'w') as f:
            json.dump(mods_by_state, f, indent=2)

        self.logger.info("Saved mod states to {}".format(self._installed_mods_file))


    def loadModsStatesList(self) -> dict:
        with open(self._installed_mods_file) as f:
            mdict = json.load(f)
        self.logger.debug("Loaded mod-activated states")

        return mdict





def getConfig() -> Tuple[configparser.ConfigParser, str, Messenger]:

    cfile = createAsNecessary()
    config = configparser.ConfigParser()
    config.read(cfile)

    # i know this isn't the right way to do this... i should get some sleep
    vals = {d: v[d] for k,v in config.items() for d in v }
    msgr = Messenger(**vals)
    # print (cm.profile)

    return config, cfile, msgr

def createAsNecessary():
    user_config_dir = os.getenv("XDG_CONFIG_HOME", os.path.expanduser("~/.config"))

    config_dir = os.path.join(user_config_dir, __myname)

    if not (os.path.exists(config_dir)):
        # _logger.warning(config_dir + " does not exist")
        # _logger.info("creating directory "+config_dir)
        os.mkdir(config_dir)

    cfile = os.path.join(config_dir, "skymodman.ini")

    if not (os.path.exists(cfile)):
        # _logger.info("Creating default configuration file.")
        create_default_config(cfile)

    return cfile


def create_default_config(path_to_config_file: str):

    conf_dir = os.path.dirname(path_to_config_file)

    # default data directory
    data_home = os.getenv("XDG_DATA_HOME",
                         os.path.expanduser("~/.local/share"))
    smm_data_dir = os.path.join(data_home, "skymodman")


    config = configparser.ConfigParser()
    config['General'] = {
        'ModsDirectory': os.path.join(smm_data_dir, "mods"),
        'VirtualFSMountPoint': os.path.join(smm_data_dir, "skyrimfs"),
        'ProfilesDirectory': os.path.join(conf_dir, "profiles"),
    }

    config['State'] = {
        "Profile": "default"
    }

    with open(path_to_config_file, "w") as configfile:
        config.write(configfile)

def _getDataDir():
    data_home = os.getenv("XDG_DATA_HOME",
                             os.path.expanduser("~/.local/share"))
    smm_data_dir = os.path.join(data_home, "skymodman")

    if not (os.path.exists(smm_data_dir)):
        # _logger.warning(smm_data_dir + " does not exist")
        # _logger.info("creating directory "+smm_data_dir)
        os.mkdir(smm_data_dir)


    # BASE = Messenger(config_file = os.path)

if __name__ == '__main__':
    # getConfig()

    cm = ConfigManager()

    # _logger.debug("Current profile: " + cm.profile)

    skylog.stop_listener()