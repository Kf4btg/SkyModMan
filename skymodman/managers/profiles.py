from enum import Enum
from pathlib import Path
from typing import List, Dict

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

    class SyncError(Enum):
        NOTFOUND = 0
        NOTLISTED = 1



    def __init__(self, profiles_dir: Path, name: str = "default", copy_profile: 'Profile' = None):

        self._name = name

        self._folder = profiles_dir / name


        self.localfiles = {}  # type: Dict[str, Path]

        if not self._folder.exists():
            # create the directory if it doesn't exist
            self._folder.mkdir()

            # since we're creating a new profile, check to see we're cloning
            # an already existing one
            if copy_profile is not None:
                import shutil
                for fpath in copy_profile.localfiles.values():
                    #copy the other profile's files to our new profile dir
                    shutil.copy(str(fpath), str(self._folder))

        for f in [self._folder / Profile.Files(p).value for p in Profile.Files]:
            # populate a dict with references to the files local to this profile,
            # keyed by the filenames sans extension (e.g. 'modinfo' for 'modinfo.json')

            self.localfiles[f.stem] = f

            if not f.exists():
                # if the file doesn't exist (perhaps because this is a new profile)
                # create blank placeholders for them
                f.touch()

        # create a container to hold any issues found during
        # validation of this profile's mod list
        self.syncErrors = {Profile.SyncError.NOTFOUND: [],
                           Profile.SyncError.NOTLISTED: []}

        # self.LOGGER.debug(self.localfiles)

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

    def recordErrors(self, error_type: SyncError, *errors):
        """
        Save any disk-sync errors discovered with the profile
        to be retrieved and handled at the appropriate time.
        Note that this method overwrites the list of errors
        for the given type; it does not append to it.
        :param error_type: either "not_found" or "not_listed"
        """
        self.syncErrors[error_type] = [e for e in errors]




@withlogger
class ProfileManager:
    """
    Manages loading and saving user profiles

    """


    # maintain a cache of previously loaded profiles; if one is requested that has already been
    # created, simply return that profile from the cache.
    # TODO: since all profiles are loaded by the profile selector at app start, we'll need to make sure
    # that this doesn't take too much memory (the Profile objects are pretty small) or take too long to start
    __cache = {} # type: Dict[str, Profile]


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
                # self.LOGGER.debug("Found profile {}: appending to profiles list.".format(p.name))
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


    def loadProfile(self, profilename, copy_from:Profile = None):
        # self.LOGGER.info("Loading profile '{}'.".format(profilename))

        if profilename in self.__cache:
            self.LOGGER.info("Profile {} found in cache; returning cached object.".format(profilename))
        else:
            self.__cache[profilename] = Profile( self._profiles_dir, profilename, copy_from)

        return self.__cache[profilename]


    def setActiveProfile(self, profilename: str):
        if self._current_profile is None or \
            self._current_profile.name != profilename:

            self._current_profile = self.loadProfile(profilename)


        return self._current_profile


    @property
    def profile_names(self) -> List[str]:
        return self._available_profiles

    def iterProfiles(self):
        for p in self._available_profiles:
            yield p

    def profilesByName(self):
        """
        :return: list of (name, Profile) pairs, sorted by name
        """
        self._available_profiles = sorted(self._available_profiles)
        pzip = zip(self._available_profiles,
                  (self.loadProfile(p) for p in self._available_profiles))

        # self.LOGGER.debug("{}".format([z for z in pzip]))

        yield from pzip



    def newProfile(self, profile_name, copy_from: Profile = None) -> Profile:
        """
        Makes a new folder in the configured
        profiles directory and creates empty
        placeholder config-files with it
        :param copy_from: if not None, copy settings from the specified pre-existing profile to the newly created one
        :param profile_name: name of new profile. Must not already exist or a nameError will be raised
        :return: the pathlib.Path object for the newly created directory
        """
        new_pdir = self._profiles_dir / profile_name

        if new_pdir.exists():
            raise exceptions.ProfileExistsError(profile_name)

        try:
            new_prof = self.loadProfile(profile_name, copy_from)
        except exceptions.ProfileError:
            raise

        self._available_profiles.append(profile_name)
        return new_prof



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









