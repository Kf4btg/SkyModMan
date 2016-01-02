import utils
# import configparser
# from typing import List, Tuple
# import os
# import sys

from managers import database, profiles, config


@utils.withlogger
class ModManager:
    """
    Manages all the backend interaction; this includes access to the Configuration,
    profile manager, database manager, etc. This is a singleton class: only one
    instance will be created during any run of the application.
    """

    _instance = None
    def __new__(cls, *args, **kwargs):
        """Override __new__ to allow only one instance of this class to exist, even
        if it is called multiple times.  Makes this class a singleton"""
        if cls._instance is not None:
            return cls._instance
        self = object.__new__(cls, *args, **kwargs)
        cls._instance = self
        return self


    def __init__(self):
        self._config_manager = config.ConfigManager(self)

        # must be created after config manager
        self._profile_manager = profiles.ProfileManager(self, self._config_manager.paths.dir_profiles)
        self._profile_manager.setActiveProfile(self._config_manager.lastprofile)

        self._db_manager = database.DBManager(self)

        # try to read modinfo file
        if not self._db_manager.loadModDB(self.active_profile.modinfo):
            # if it fails, re-read mod data from disk
            self._db_manager.getModDataFromModDirectory(self._config_manager.modsdirectory)
            # and [re]create the cache file
            self.saveModList()


    @property
    def Config(self) -> config.ConfigManager:
        return self._config_manager

    @property
    def DB(self) -> database.DBManager:
        return self._db_manager

    @property
    def Profiler(self) -> profiles.ProfileManager:
        return self._profile_manager

    @property
    def active_profile(self) -> profiles.Profile:
        return self.Profiler.active_profile


    def allmods(self):
        """
        Obtain an iterator of all the currently installed mods; contains
        information on with their installation order, nexus id, current
        version, name of FS folder that holds their data, user-customized
        name for the mod, and whether they're enabled in the load order or not.

        :return:This is returned as a list of tuples with the following structure:
            (
                Install Order (int),
                Mod-ID (int),
                Version (str),
                directory (str),
                name (str),
                enabled-status (int, either 0 or 1)
            )
        """
        yield from self.DB.getModInfo()


    def enabledMods(self):
        yield from self.DB.enabledMods(True)
        # self.LOGGER.debug(str(em))
        # # return self.DB.enabledMods(True)
        # return em

    def disabledMods(self):
        yield from self.DB.disabledMods(True)

    def saveModList(self):
        self.DB.saveModDB(self.active_profile.modinfo)


    # def modListFromDirectory(self, mod_install_dir: str) -> List[Tuple[str, str, str]] :
    #     """
    #     Examine the configured mods-directory and create a list of installed mods where each folder in said directory is considered a mod. If a meta.ini file (in the format used by ModOrganizer) exists in a mod's folder, extra mod details are read from it.
    #     :param mod_install_dir:
    #     :return: A list of tuples in the form (mod-name, mod-id, mod-version)
    #     """
    #
    #     self.LOGGER.info("Reading mods from mod directory")
    #
    #     configP = configparser.ConfigParser()
    #
    #     mods_list = []
    #     for moddir in os.listdir(mod_install_dir):
    #         inipath = "{}/{}/{}".format(mod_install_dir, moddir, "meta.ini")
    #         configP.read(inipath)
    #         mods_list.append((moddir, configP['General']['modid'], configP['General']['version']))
    #
    #     return mods_list

    # def saveModStates(self, mods_by_state):
    #     """
    #     call the save-mod-states function of the config
    #     manager and update this managers's modstates property
    #     :param mods_by_state:
    #     :return:
    #     """
    #     self._mod_states = mods_by_state
    #     self._config_manager.saveModsList(mods_by_state)

