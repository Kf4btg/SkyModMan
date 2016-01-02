from enum import Enum
from pathlib import Path
from typing import List

from skymodman import exceptions
from skymodman.utils import withlogger


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

        if not self._folder.exists():
            # create the directory if it doesn't exist
            self._folder.mkdir()

        self.localfiles = {} # type: Dict[str, Path]
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
    def name(self) -> str:
        return self._name

    @property
    def folder(self) -> Path:
        return self._folder

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
    """
    Manages loading and saving user profiles

    """


    def __init__(self, manager, directory: Path):
        """
        :param manager: reference to ModManager
        :param directory: the application's 'profiles' storage directory
        """
        super(ProfileManager, self).__init__()
        self.manager = manager

        self._profiles_dir = directory
        self._current_profile = None

        # make sure directory exists
        if not self._profiles_dir.exists():
            raise FileNotFoundError("Profile directory not found: {}".format(self._profiles_dir))


        ## load profile names from folders in profiles-dir
        self.LOGGER.info("loading profiles from {}".format(self._profiles_dir))
        self._available_profiles = []

        for p in self._profiles_dir.iterdir():
            if p.is_dir():
                self.LOGGER.debug("Found profile {}: appending to profiles list.".format(p.name))
                self._available_profiles.append(p.name)

        if len(self._available_profiles) == 0:
            self.LOGGER.warning("No profiles found. Creating default profile.")
            self._available_profiles.append("default")
            self._current_profile = self.loadProfile("default")


    @property
    def active_profile(self) -> Profile:
        if self._current_profile is None:
            self._current_profile = self.loadProfile("default")
        return self._current_profile


    def loadProfile(self, profilename):
        self.LOGGER.info("Loading profile '{}'.".format(profilename))
        return Profile( self._profiles_dir, profilename )


    def setActiveProfile(self, profilename: str):
        if self._current_profile is None or self._current_profile.name != profilename:
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


    def newProfile(self, profile_name) -> Profile:
        """
        Makes a new folder in the configured
        profiles directory and creates empty
        placeholder config-files with it
        :param profile_name: name of new profile. Must not already exist or a nameError will be raised
        :return: the pathlib.Path object for the newly created directory
        """
        new_pdir = self._profiles_dir / profile_name

        if new_pdir.exists():
            raise exceptions.ProfileExistsError(profile_name)


        return self.loadProfile(profile_name)


    def deleteProfile(self, profile, confirm = False):
        """
        Removes the folder and all config files for the specified profile.
        :param profile: either a Profile object or the name of an existing profile
        :param confirm: must pass true for this to work. This option will likely be removed;
        it's mainly to prevent me from doing stupid things during development
        :return:
        """

        assert confirm
        if isinstance(profile, str):

            profile = Profile(self._profiles_dir, profile)

        assert isinstance(profile, Profile)

        if profile.name == "default":
            raise exceptions.DeleteDefaultProfileError("default")


        for f in profile.localfiles.values():
            if f.exists(): f.unlink()

        profile.folder.rmdir()









