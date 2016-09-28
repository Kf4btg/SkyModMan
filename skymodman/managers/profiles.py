from skymodman import exceptions
from skymodman.managers.base import Submanager
from skymodman.types import Profile, diqt
from skymodman.constants import FALLBACK_PROFILE, overrideable_dirs
from skymodman.log import withlogger

# @humanizer.humanize
@withlogger
class ProfileManager(Submanager):
    """
    Manages loading and saving user profiles
    """

    # maintain a cache of previously loaded profiles; if one is
    # requested that has already been created, simply return that
    # profile from the cache.
    # TODO: since all profiles are loaded by the profile selector at app start, we'll need to make sure that this doesn't take too much memory (the Profile objects are pretty small) or take too long to start

    # only hold the 5 most recently loaded profiles (this session)
    __cache = diqt(maxlen_=5)


    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

        # self._profiles_dir = directory
        self._current_profile = None # type: Profile

        _profiles_dir = self.mainmanager.Folders['profiles'].path

        # make sure directory exists
        if not _profiles_dir.exists():
            raise FileNotFoundError("Profile directory not found: {}"
                                    .format(_profiles_dir))

        ## load profile names from folders in profiles-dir
        self.LOGGER.info("loading profiles from {}".format(_profiles_dir))
        self._profile_names = [] # type: list [str]

        for p in _profiles_dir.iterdir():
            if p.is_dir():
                self._profile_names.append(p.name)

        if len(self._profile_names) == 0:
            self.LOGGER.warning("No profiles found. Creating default profile.")
            self._profile_names.append(FALLBACK_PROFILE)
            self.load_profile(FALLBACK_PROFILE)

    ################
    ## Properties ##
    ################

    @property
    def active_profile(self):
        return self._current_profile

    @property
    def profile_names(self):
        return self._profile_names

    @property
    def _profiles_dir(self):
        # TODO: just use the Folders instance directly
        return self.mainmanager.Folders['profiles'].path

    #######################
    ## Choosing Profiles ##
    #######################

    def __getitem__(self, profilename):
        """
        Provides mapping-like access to profiles: use
        ``profmanager['my_profile']`` to retrieve the Profile object for
        the profile named 'my_profile' (loading it from disk if not
        cached).

        Unlike the default behavior of 'load_profile', this will NOT
        create a new profile if one by the given name can't be found.
        A ProfileDoesNotExistError will be raised instead.

        :param profilename: name of the profile to load
        :return: Profile object
        """

        return self.load_profile(profilename, create=False)



    def load_profile(self, profilename, copy_from = None, create=True) -> Profile:
        """

        :param str profilename:
            name of profile to load.
        :param str copy_from:
            If `copy_from` is specified and is the name of a currently
            existing profile, settings will be copied from that profile
            to the new one rather than creating the typical default
            configuration files.
        :param create:
            If True, and no profile by the given name exists, a new one
            with that name will be created and returned, copying
            configuration from `copy_from` if specified. If False and
            the profile does not exist, a ProfileError will be raised.
        :return: loaded or created Profile object
        """
        # self.LOGGER.info("Loading profile '{}'.".format(profilename))

        if profilename in self.__cache:
            self.LOGGER.info("Profile {} found in cache;"
                             " returning cached object.".format(
                profilename))
        elif copy_from:
            try:
                based_on=self[copy_from]
            except exceptions.ProfileDoesNotExistError as e:
                # copy_from was invalid...just ignore it
                self.LOGGER.error(e)
                self.__cache.append(profilename,
                                    Profile(self._profiles_dir,
                                            profilename,
                                            create_on_enoent=create))
            else:
                self.__cache.append(profilename,
                                Profile(self._profiles_dir, profilename,
                                        copy_profile=based_on,
                                            create_on_enoent=create))
        else:
            self.__cache.append(profilename,
                                Profile(self._profiles_dir,
                                        profilename,
                                        create_on_enoent=create))


        return self.__cache[profilename]

    def set_active_profile(self, profilename=None):
        """

        :param str|None profilename: name of the profile to activate; if it
            does not already exist on disk, it will be created. If this
            parameter is ``None``, then the ``active_profile`` property
            will be unset.
        :return: the newly activated Profile object
        """

        if profilename is None:
            # unset the active profile
            self._current_profile = None
        else:
            if self._current_profile is None or \
                self._current_profile.name != profilename:

                self._current_profile = self.load_profile(profilename)

                # check for and en/dis-able directory overrides as needed
                for dkey in overrideable_dirs:
                    try:
                        ovrd = self._current_profile.get_override_path(dkey)
                    except KeyError as e:
                        self.LOGGER.exception(e)
                        self.mainmanager.Folders[dkey].remove_override()
                    else:
                        if ovrd:
                            self.mainmanager.Folders[dkey].set_override(
                                ovrd)
                        else:
                            self.mainmanager.Folders[dkey].remove_override()

                # for odir, opath in self._current_profile.overrides():
                #     try:
                #         self.mainmanager.Folders[odir].set_override(opath)
                #     except KeyError as e:
                #         self.LOGGER.exception(e)

        return self._current_profile

    #############################
    ## Iterating over Profiles ##
    #############################

    def iter_profiles(self):
        """Iterate over the list of known profiles"""
        # yield from self._profile_names
        yield from (self.load_profile(p) for p in sorted(self._profile_names))

    def profiles_by_name(self):
        """
        iterator of (name, Profile) pairs, sorted by name
        """
        self._profile_names = sorted(self._profile_names)
        yield from zip(self._profile_names,
                       (self.load_profile(p)
                            for p in self._profile_names))


    #####################
    ## Adding/Removing ##
    #####################

    def new_profile(self, profile_name, copy_from = None) -> Profile:
        """
        Create a new folder in the configured profiles directory and
        generate empty placeholder config-files within it. If an
        existing Profile is specified in `copy_from`, config files are
        duplicated from that Profile directory into the the new one,
        rather than being created empty.

        :param str profile_name:
            name of new profile. Must not already exist or an Exception
            will be raised
        :param str copy_from:
            if not None, copy settings from the specified pre-existing
            profile to the newly created one
        :return: the Profile object for the newly created profile
        """
        new_pdir = self._profiles_dir / profile_name

        if new_pdir.exists():
            raise exceptions.ProfileExistsError(profile_name)

        try:
            new_prof = self.load_profile(profile_name, copy_from)
        except exceptions.ProfileError:
            raise

        self._profile_names.append(profile_name)
        return new_prof


    def delete_profile(self, profile):
        """
        Removes the folder and all config files for the specified profile.

        :param profile:
            either a Profile object or the name of an existing profile

        """

        # if the profile name was passed, get its Profile object
        if isinstance(profile, str):
            profile = Profile(self._profiles_dir, profile)

        # now make sure we have a Profile instance
        assert isinstance(profile, Profile)

        # don't allow deletion of the fallback; .lower() is redundant on
        # FALLBACK_PROFILE as it is, but just to future-proof it...
        if profile.name.lower() == FALLBACK_PROFILE.lower():
            raise exceptions.DeleteDefaultProfileError()

        # remove from available_profiles list
        self._profile_names.remove(profile.name)
        # and from cache
        if profile.name in self.__cache:
            self.__cache.remove(profile.name)

        try:
            # delete files in folder
            profile.delete_files()
            # remove folder
            profile.folder.rmdir()
        except OSError as e:
            self.LOGGER.error(e)
            raise exceptions.ProfileDeletionError(profile.name) from e

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

