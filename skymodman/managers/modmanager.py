from skymodman import utils, exceptions
from skymodman.managers import config, database, profiles


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
        # set the most-recently loaded profile as active.
        self._profile_manager.setActiveProfile(self._config_manager.lastprofile)

        # Prepare the database, but do not load any information
        # until it is requested.
        self._db_manager = database.DBManager(self)

        # try to read modinfo file
        # aaaaactually...let's wait until someone requests the modinfo to load it up...
        # if not self._db_manager.loadModDB(self.active_profile.modinfo):
        #     # if it fails, re-read mod data from disk
        #     self._db_manager.getModDataFromModDirectory(self._config_manager.paths.dir_mods)
        #     # and [re]create the cache file
        #     self.saveModList()



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
        """
        Retrieves the presently loaded Profile from the
        Profile Manager.
        :return: The active Profile object
        """
        return self.Profiler.active_profile

    @active_profile.setter
    def active_profile(self, profile:str):
        """
        Set `profile` as currently loaded
        :param profile:
        :return:
        """
        self.Profiler.setActiveProfile(profile)

    def getProfiles(self, names_only = True):
        """Generator that iterates over all existing profiles.
        :param names_only: if True, only yield the profile names. If false, yield tuples of (name, Profile) pairs"""
        if names_only:
            yield from (n for n in self.Profiler.profile_names)
        else:
            yield from self.Profiler.profilesByName()

    def newUserProfile(self, name: str, copy_from: profiles.Profile = None):
        """
        Create and return a new Profile object with the specified name, optionally
        copying config files from the `copy_from` Profile
        :param name:
        :param copy_from:
        :return:
        """
        return self.Profiler.newProfile(name, copy_from)

    def loadActiveProfileData(self):
        """
        Asks the Database Manager to load the information stored
        on disk for the given profile into an in-memory database
        that will be used to provide data to the rest of the app.
        :return:
        """

        # try to read modinfo file
        if self.DB.loadModDB(self.active_profile.modinfo):
            # if successful, validate modinfo
            self.validateModInstalls()

        else:
            # if it fails, re-read mod data from disk
            self.DB.getModDataFromModDirectory(self.Config.paths.dir_mods)
            # and [re]create the cache file
            self.saveModList()


    def validateModInstalls(self):
        """
        Queries the disk and the database to see if the respective
        lists of mods are in sync. If not, any issues encountered
        are recorded on the active profile object.
        :return: True if no errors encountered, False otherwise
        """
        try:
            self.DB.validateModsList(self.Config.listModFolders())
        except exceptions.FilesystemDesyncError as e:
            self.LOGGER.error(e)
            if e.count_not_listed:
                # add them to the end of the list and notify the user
                self.active_profile.recordErrors(profiles.Profile.SyncError.NOTLISTED, e.not_listed)
            if e.count_not_found:
                # mark them somehow in the list display, and notify the user. Don't automatically remove from the list or anything silly like that.
                self.active_profile.recordErrors(profiles.Profile.SyncError.NOTFOUND, e.not_found)
            return False
        return True


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

    def basicModInfo(self):
        """Convenience method for table-display
        :return: tuples of form (enabled-status, mod ID, version, name)
        """
        yield from self.DB.execute_("SELECT enabled, modid, version, name FROM mods")

    def enabledMods(self):
        yield from self.DB.enabledMods(True)

    def disabledMods(self):
        yield from self.DB.disabledMods(True)



    def saveModList(self):
        """Request that database manager save modinfo to disk"""
        self.DB.saveModDB(self.active_profile.modinfo)



