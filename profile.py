import os
from pathlib import Path

import utils
# import skylog



@utils.withlogger
class ProfileManager:
    def __init__(self, profiles_dir):
        self.profiles_dir = profiles_dir


        self.available_profiles = self.loadProfiles()




    def loadProfiles(self) -> list:

        self.logger.info("loading profiles from "+self.profiles_dir)
        profile_list = []
        for p in os.scandir(self.profiles_dir):
            if p.is_dir():
                profile_list.append(p.name)

        return profile_list



    def newProfile(self, profile_name) -> Path:
        """
        Makes a new folder in the configured
        profiles directory and creates empty
        placeholder config-files with it
        :param profile_name: name of new profile. Must not already exist or a nameError will be raised
        :return: the pathlib.Path object for the newly created directory
        """
        pdPath = Path(self.profiles_dir)


        new_pdir = pdPath / profile_name

        if new_pdir.exists():
            raise NameError("A profile with the name {} already exists.".format(profile_name))

        self.logger.info("Creating new profile directory for {}".format(profile_name))
        # create the new profile dir
        new_pdir.mkdir()

        # create empty config files
        for pfile in ["installed.json", "loadorder.json", "overwrite.json", "installorder.json", "inimod.json"]:
            fpath = new_pdir / pfile
            fpath.touch()
            self.logger.debug("touched {}".format(pfile))

        return new_pdir
