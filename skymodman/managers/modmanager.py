from skymodman import utils
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

    def getProfiles(self, names_only = True):
        if names_only:
            yield from (n for n in self.Profiler.profile_names)
        else:
            yield from self.Profiler.profilesByName()

    def newUserProfile(self, name: str, copy_from: profiles.Profile = None):
        self.Profiler.newProfile(name, copy_from)



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

    def disabledMods(self):
        yield from self.DB.disabledMods(True)

    def saveModList(self):
        self.DB.saveModDB(self.active_profile.modinfo)



