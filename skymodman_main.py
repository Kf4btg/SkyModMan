#!/usr/bin/env python3
import sys
from typing import List, Tuple
import configparser
import os

from config import ConfigManager
from dbmanager import DBManager
import skylog
from utils import withlogger


@withlogger
class ModManager:
    def __init__(self):
        self._config_manager = ConfigManager()
        self._db_manager = DBManager()

        # self._loaded_profile = self._config_manager.profile
        # self.installed_mods = self.modListFromDirectory(self._config_manager.modsdirectory)

        self._mod_states = self._config_manager.loadModsStatesList()

    @property
    def mod_states(self):
        return self._mod_states

    @property
    def profile(self):
        return self._config_manager.profile


    @property
    def Config(self) -> ConfigManager:
        return self._config_manager


    def modListFromDirectory(self, mod_install_dir: str) -> List[Tuple[str, str, str]] :
        """
        Examine the configured mods-directory and create a list of installed mods where each folder in said directory is considered a mod. If a meta.ini file (in the format used by ModOrganizer) exists in a mod's folder, extra mod details are read from it.
        :param mod_install_dir:
        :return: A list of tuples in the form (mod-name, mod-id, mod-version)
        """

        self.logger.info("Reading mods from mod directory")

        configP = configparser.ConfigParser()

        mods_list = []
        for moddir in os.listdir(mod_install_dir):
            inipath = "{}/{}/{}".format(mod_install_dir, moddir, "meta.ini")
            configP.read(inipath)
            mods_list.append((moddir, configP['General']['modid'], configP['General']['version']))

        return mods_list

    def saveModStates(self, mods_by_state):
        """
        call the save-mod-states function of the config
        manager and update this manager's modstates property
        :param mods_by_state:
        :return:
        """
        self._mod_states = mods_by_state
        self._config_manager.saveModsList(mods_by_state)








def main():

    MM = ModManager()


USE_QT_GUI = os.getenv("USE_QT_GUI", True)

if __name__ == '__main__':

    if USE_QT_GUI:
        from PyQt5.QtWidgets import QApplication
        from PyQt5.QtGui import QGuiApplication
        from qt_launch import ModManagerWindow

        app = QApplication(sys.argv)
        MM = ModManager()

        w = ModManagerWindow(MM)
        w.resize(QGuiApplication.primaryScreen().availableSize()*3/5)
        w.show()

        sys.exit(app.exec_())
    else:
        main()

    skylog.stop_listener()
