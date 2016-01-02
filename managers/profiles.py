import os
from pathlib import Path
from typing import List, Union, Iterable, Tuple

from utils import withlogger
from enum import Enum


@withlogger
class Profile:
    """
    Represents a Manager profile with customized mod combinations, ini edits, loadorder, etc.
    """

    class Files(str, Enum):
        MODINFO   = "modinfo.json"
        LOADORDER = "loadorder.json"
        INIEDITS  = "iniedits.json"
        OVERWRITE = "overwrites.json"

    def __init__(self, profiles_dir: Path, name: str = "default"):
        self._name = name

        self._folder = profiles_dir / name

        self.localfiles = {}
        for f in [self._folder / Profile.Files(p).value for p in Profile.Files]:
            # populate a dict with references to the files local to this profile,
            # keyed by the filenames sans extension (e.g. 'modinfo' for 'modinfo.json')

            self.localfiles[f.stem] = f

            if not f.exists():
                # if the file doesn't exist (perhaps because this is a new profile)
                # create blank placeholders for them
                f.touch()

        self.LOGGER.debug(self.localfiles)

    @property
    def name(self) -> Path:
        return self._name

    @property
    def modinfo(self) -> Path:
        return self.localfiles['modinfo']

    @property
    def loadorder(self) -> Path:
        return self.localfiles['loadorder']

    @property
    def iniedits(self) -> Path:
        return self.localfiles['iniedits']

    @property
    def overwrites(self) -> Path:
        return self.localfiles['overwrites']




@withlogger
class ProfileManager:


    def __init__(self, manager, directory: Path):
        """

        :param manager: reference to ModManager
        :param directory: the application's 'profiles' storage directory
        """
        super(ProfileManager, self).__init__()
        self.manager = manager

        self._profiles_dir = directory

        # if not isinstance(profiles_dir, Path):
        #     self._profiles_dir = Path(profiles_dir)

        # make sure directory exists
        if not self._profiles_dir.exists():
            raise FileNotFoundError("Profile directory not found: {}".format(self._profiles_dir))


        ## load profile names from folders in profiles-dir
        self.logger.info("loading profiles from {}".format(self._profiles_dir))
        self._available_profiles = []

        for p in self._profiles_dir.iterdir():
            if p.is_dir():
                self.logger.debug("Found profile {}: appending to profiles list.".format(p.name))
                self._available_profiles.append(p.name)

        self._current_profile = self.loadProfile("default")


    @property
    def active_profile(self) -> Profile:
        return self._current_profile


    def loadProfile(self, profilename):
        # pdir = self._profiles_dir / profilename # type: Path

        self.logger.info("Loading profile '{}'.".format(profilename))
        return Profile( self._profiles_dir, profilename )


    def setActiveProfile(self, profilename):
        if self.active_profile.name != profilename:
            self._current_profile = self.loadProfile(profilename)

        return self._current_profile




    # @property
    # def profiles_dir(self) -> Path:
    #     return self._profiles_dir

    @property
    def profile_names(self) -> List[str]:
        return self._available_profiles

    def iterProfiles(self):
        for p in self._available_profiles:
            yield p



    # def getConfigFile(self, config_file: Union[ProfileFiles,str], profile_name: str="default") -> Path:
    #     """
    #     return a Path object for the requested file from the specified profile
    #     :param profile_name:
    #     :param config_file:
    #     :return:
    #     """
    #     return self._profiles_dir / profile_name / config_file


    def loadProfiles(self) -> List[str]:
        """

        :return: list of profile names
        """

        self.logger.info("loading profiles from {}".format(self._profiles_dir))
        profile_list = []

        for p in self._profiles_dir.iterdir():
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
        pdPath = Path(self._profiles_dir)


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

    def deleteProfile(self, profile):
        pass








