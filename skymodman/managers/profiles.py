# from enum import Enum
from pathlib import Path
# from collections import namedtuple
from configparser import ConfigParser as confparser

from skymodman import exceptions
# from skymodman.managers import modmanager as Manager
from skymodman.constants import SyncError as SE
from skymodman.utils import withlogger, diqt, open_for_safe_write


# well...that's all for now i guess!
# _psettings = namedtuple("_psettings", "modlist_onlyactive")


ProfileFiles = (MODINFO, LOADORDER, INIEDITS, OVERWRITE, HIDDEN, SETTINGS) = (
    "modinfo.json", "loadorder.json", "iniedits.json",
    "overwrites.json", "hiddenfiles.json", "settings.ini")



# from skymodman.utils import humanizer
# @humanizer.humanize
@withlogger
class Profile:
    """
    Represents a User profile with customized mod combinations, ini edits, loadorder, etc.
    """
    __default_settings = {
        "File Viewer": {
            "activeonly": True,
        }
    }


    def __init__(self, profiles_dir, name="default",
                 copy_profile=None, create_on_enoent=True):
        """

        :param Path profiles_dir:
        :param str name:
        :param Profile copy_profile:
        :param bool create_on_enoent: Whether to create the profile folder if it does not already exist
        """

        self.name = name

        self.folder = profiles_dir / name # type: Path

        if not self.folder.exists():
            if create_on_enoent:
                # create the directory if it doesn't exist
                self.folder.mkdir()

                # since we're creating a new profile, check to see if
                # we're cloning an already existing one
                if copy_profile is not None:
                    import shutil
                    for fpath in (copy_profile.folder / fname for fname in ProfileFiles):
                        #copy the other profile's files to our new profile dir
                        shutil.copy(str(fpath), str(self.folder))
                    del shutil
            else:
                raise exceptions.ProfileDoesNotExistError(name)

        for f in [self.folder / p for p in ProfileFiles]:

            if not f.exists():
                # if the file doesn't exist (perhaps because this is a new profile)
                # create empty placeholder for it
                f.touch()
                if f.name == SETTINGS:
                    # put default vals in the ini file
                    c = confparser()
                    c.read_dict(self.__default_settings)
                    with f.open('w') as ini:
                        c.write(ini)

        # we don't worry about the json files, but we need to load in
        # the values from the ini file and store it.
        self._config = self.load_profile_settings()
        # self.LOGGER << "Loaded profile-specific settings: {}".format(self.settings)

        # create a container to hold any issues found during
        # validation of this profile's mod list
        self.syncErrors = {SE.NOTFOUND: [],
                           SE.NOTLISTED: []}

    @property
    def Config(self):
        # has a capital C to differentiate from path properties
        return self._config

    @property
    def modinfo(self) -> Path:
        return self.folder / MODINFO

    @property
    def loadorder(self) -> Path:
        return self.folder / LOADORDER

    @property
    def iniedits(self) -> Path:
        return self.folder / INIEDITS

    @property
    def overwrites(self) -> Path:
        return self.folder / OVERWRITE

    @property
    def hidden_files(self):
        return self.folder / HIDDEN

    @property
    def settings(self):
        return self.folder / SETTINGS



    def rename(self, new_name):
        """

        :param str new_name:
        :return:
        """
        if self.name.lower() == "default":
            raise exceptions.DeleteDefaultProfileError()

        new_dir = self.folder.with_name(new_name) #type: Path

        ## if the folder exists or if it matches (case-insensitively)
        ##  one of the other profile dirs, raise exception
        if new_dir.exists() or \
            new_name.lower() in [f.name.lower() for f in self.folder.parent.iterdir()]:
            raise exceptions.ProfileExistsError(new_name)

        ## rename the directory (doesn't affect path obj)
        self.folder.rename(new_dir)

        ## verify that rename happened successfully
        if not new_dir.exists() or self.folder.exists():
            raise exceptions.ProfileError(self.name,
                                          "Error while renaming profile '{name}' to '{new_name}'".format(name=self.name, new_name=new_name))

        ## update reference
        self.folder = new_dir
        self.name = new_name



    def recordErrors(self, error_type, errors):
        """
        Save any disk-sync errors discovered with the profile
        to be retrieved and handled at the appropriate time.
        Note that this method overwrites the list of errors
        for the given type; it does not append to it.

        :param error_type: either constants.SyncError.NOTFOUND or constants.SE.NOTLISTED
        :param errors: a list of the errors encountered
        """
        self.syncErrors[error_type] = errors

    def load_profile_settings(self):
        config = confparser()
        config.read(str(self.settings))

        # for now, just turn the config parser into a dict and return it;
        # the checks below should deal with most of the conversions we'd need
        # to worry about
        sett={}
        for sec, sub in self.__default_settings.items():
            sett[sec]={}
            for k,v in sub.items():
                if isinstance(v, bool):
                    # fallback to default vals if key or section is missing
                    sett[sec][k] = config.getboolean(sec, k, fallback=v)
                elif isinstance(v, int):
                    sett[sec][k] = config.getint(sec, k, fallback=v)
                elif isinstance(v, float):
                    sett[sec][k] = config.getfloat(sec, k, fallback=v)
                else:
                    sett[sec][k] = v # strings for everyone else
        return  sett

    def save_setting(self, section, name, value):
        """Change a setting value and write the updated values to disk"""
        assert section in self._config
        assert name in self._config[section]

        self._config[section][name] = value

        self._save_profile_settings()

    def _save_profile_settings(self):
        """Overwrite the settings file with the current values"""

        config = confparser()
        config.read_dict(self._config)

        with open_for_safe_write(self.settings) as ini:
            config.write(ini)




# @humanizer.humanize
@withlogger
class ProfileManager:
    """
    Manages loading and saving user profiles
    """

    # maintain a cache of previously loaded profiles; if one is
    # requested that has already been created, simply return that
    # profile from the cache.
    # TODO: since all profiles are loaded by the profile selector at app start, we'll need to make sure that this doesn't take too much memory (the Profile objects are pretty small) or take too long to start
    # __cache = {} # type: Dict[str, Profile]

    # only hold the 5 most recently loaded profiles (this session)
    __cache = diqt(maxlen_=5)


    def __init__(self, directory):
        """
        :param Path directory: the application's 'profiles' storage directory
        """
        super().__init__()

        self._profiles_dir = directory
        self._current_profile = None # type: Profile

        # make sure directory exists
        if not self._profiles_dir.exists():
            raise FileNotFoundError("Profile directory not found: {}".format(self._profiles_dir))

        ## load profile names from folders in profiles-dir
        self.LOGGER.info("loading profiles from {}".format(self._profiles_dir))
        self._profile_names = [] # type: List[str]

        for p in self._profiles_dir.iterdir():
            if p.is_dir():
                # self.LOGGER.debug("Found profile {}: appending to profiles list.".format(p.name))
                self._profile_names.append(p.name)

        if len(self._profile_names) == 0:
            self.LOGGER.warning("No profiles found. Creating default profile.")
            self._profile_names.append("default")
            # self._current_profile = self.loadProfile("default")
            self.loadProfile("default")

    ################
    ## Properties ##
    ################

    @property
    def active_profile(self):
        # if self._current_profile is None:
        #     self._current_profile = self.loadProfile("default")
        return self._current_profile

    @property
    def profile_names(self):
        return self._profile_names

    #######################
    ## Choosing Profiles ##
    #######################

    def __getitem__(self, profilename):
        """
        Provides mapping-like access to profiles: use ``profmanager['my_profile']``
        to retrieve the Profile object for the profile named 'my_profile'
        (loading it from disk if not cached).

        Unlike the default behavior of 'loadProfile', this will NOT
        create a new profile if one by the given name can't be found.
        A ProfileDoesNotExistError will be raised instead.

        :param profilename: name of the profile to load
        :return: Profile object
        """

        return self.loadProfile(profilename, create=False)



    def loadProfile(self, profilename, copy_from = None, create=True) -> Profile:
        """

        :param str profilename:
            name of profile to load.
        :param Profile copy_from:
            If `copy_from` is specified and is the name of a currently existing profile, settings will be copied from that profile to the new one rather than creating the typical default configuration files.
        :param create:
            If True, and no profile by the given name exists, a new one with that name will be created and returned, copying configuration from `copy_from` if specified. If False and the profile does not exist, a ProfileError will be raised.
        :return: loaded or created Profile object
        """
        # self.LOGGER.info("Loading profile '{}'.".format(profilename))

        if profilename in self.__cache:
            self.LOGGER.info("Profile {} found in cache; returning cached object.".format(profilename))
        else:
            self.__cache.append(profilename, Profile(self._profiles_dir, profilename, copy_profile=copy_from, create_on_enoent=create))


        return self.__cache[profilename]

    def setActiveProfile(self, profilename):
        """

        :param str profilename:
        :return: the newly created Profile object
        """
        if self._current_profile is None or \
            self._current_profile.name != profilename:

            self._current_profile = self.loadProfile(profilename)


        return self._current_profile

    #############################
    ## Iterating over Profiles ##
    #############################

    def iterProfiles(self):
        """Iterate over the list of known profiles"""
        yield from self._profile_names

    def profilesByName(self):
        """
        iterator of (name, Profile) pairs, sorted by name
        """
        self._profile_names = sorted(self._profile_names)
        yield from zip(self._profile_names,
                       (self.loadProfile(p) for p in self._profile_names))


    #####################
    ## Adding/Removing ##
    #####################

    def newProfile(self, profile_name, copy_from = None) -> Profile:
        """
        Create a new folder in the configured profiles directory and generate
        empty placeholder config-files within it. If an existing Profile is
        specified in `copy_from`, config files are duplicated from that
        Profile directory into the the new one, rather than being created empty.

        :param str profile_name:
            name of new profile. Must not already exist or an Exception will be raised
        :param Profile copy_from:
            if not None, copy settings from the specified pre-existing profile to the newly created one
        :return: the Profile object for the newly created profile
        """
        new_pdir = self._profiles_dir / profile_name

        if new_pdir.exists():
            raise exceptions.ProfileExistsError(profile_name)

        try:
            new_prof = self.loadProfile(profile_name, copy_from)
        except exceptions.ProfileError:
            raise

        self._profile_names.append(profile_name)
        return new_prof


    def deleteProfile(self, profile, confirm = False):
        """
        Removes the folder and all config files for the specified profile.

        :param profile:
            either a Profile object or the name of an existing profile
        :param confirm:
            must pass true for this to work. This option will likely be removed;
            it's mainly to prevent me from doing stupid things during development
        :return:
        """

        assert confirm

        # if the profile name was passed, get its Profile object
        if isinstance(profile, str):
            profile = Profile(self._profiles_dir, profile)

        # now make sure we have a Profile instance
        assert isinstance(profile, Profile)

        if profile.name.lower() == "default":
            raise exceptions.DeleteDefaultProfileError()

        # remove from available_profiles list
        self._profile_names.remove(profile.name)
        # and from cache
        if profile.name in self.__cache:
            self.__cache.remove(profile.name)

        # delete files in folder
        for f in profile.localfiles.values():
            if f.exists(): f.unlink()

        # remove folder
        profile.folder.rmdir()

    def rename_profile(self, profile, new_name):
        """
        Moves the directory containing the configuration files for Profile `profile` to a new directory with the name `new_name`, and updates all occurrences of the old name to the new.

        :param profile:
        :param new_name:
        :raises: ProfileExistsError: if a directory named `new_name` already exists
        """

        assert isinstance(profile, Profile)

        old_name = profile.name
        profile.rename(new_name)

        self.__cache.remove(old_name)
        self._profile_names.remove(old_name)
        self._profile_names.append(profile.name)

        self.__cache.append(profile.name, profile)



if __name__ == '__main__':
    from typing import List
