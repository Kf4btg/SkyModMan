from skymodman import exceptions, ModEntry
from skymodman.utils import withlogger
from skymodman.managers import config, database, profiles
from skymodman import constants

from typing import List


@withlogger
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
    def active_profile(self, profile):
        """
        To be called by external interfaces.
        Set `profile` as currently loaded. Updates saved config file to mark this profile as the last-loaded profile,
        and loads the data for the newly-activated profile
        :param profile:
        :return:
        """
        # make sure we're dealing with just the name
        if isinstance(profile, profiles.Profile):
            profile = profile.name
        assert isinstance(profile, str)
        self.Profiler.setActiveProfile(profile)
        self.Config.updateConfig(profile, "lastprofile")

        # have to reinitialize the database
        self.DB.reinit()
        self.loadActiveProfileData()

    def getProfiles(self, names_only = True):
        """Generator that iterates over all existing profiles.
        :param names_only: if True, only yield the profile names. If false, yield tuples of (name, Profile) pairs"""
        if names_only:
            yield from (n for n in self.Profiler.profile_names)
        else:
            yield from self.Profiler.profilesByName()

    def newProfile(self, name: str, copy_from: profiles.Profile = None):
        """
        Create and return a new Profile object with the specified name, optionally
        copying config files from the `copy_from` Profile
        :param name:
        :param copy_from:
        :return:
        """
        return self.Profiler.newProfile(name, copy_from)

    def deleteProfile(self, profile):
        self.Profiler.deleteProfile(profile, True)


    def loadActiveProfileData(self):
        """
        Asks the Database Manager to load the information stored
        on disk for the given profile into an in-memory database
        that will be used to provide data to the rest of the app.
        """
        self.LOGGER.debug("loading data for active profile '{}'".format(self.active_profile.name))
        # try to read modinfo file
        if self.DB.loadModDB(self.active_profile.modinfo):
            self.LOGGER.debug("validating installed mods")
            # if successful, validate modinfo
            self.validateModInstalls()

        else:
            self.LOGGER.debug("Could not load mod info, reading from configured mods directory: {}".format(self.Config.paths.dir_mods))
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

    def basicModInfo(self):
        """
        Obtain an iterator over all the rows in the database which yields _all_ the info for a mod as a dict, intended for feeding to ModEntry(**d) or using directly.

        :rtype: __generator[dict[str, sqlite3.Row], Any, None]
        """
        #TODO: rename this.
        for row in self.DB.getModInfo():
            yield dict(zip(row.keys(), row))

    def enabledMods(self):
        """
        yields the names of enabled mods for the currently active profile
        """
        yield from self.DB.enabledMods(True)

    def disabledMods(self):
        yield from self.DB.disabledMods(True)

    def saveUserEdits(self, changes):
        """
        :param collections.abc.Iterable[ModEntry] changes: an iterable of ModEntry objects
        """

        rows_to_delete = [(m.ordinal, ) for m in changes]

        # a generator that creates tuples of values by sorting the values of the
        # modentry according the order defined in constants.db_fields
        dbrowgen = (tuple([getattr(m, f) for f in sorted(m._fields, key=lambda fld: constants.db_fields.index(fld)) ] ) for m in changes)

        # using the context manager may allow deferrable foreign to go unsatisfied for a moment
        with self.DB.conn:
            # delete the row with the given ordinal
            self.DB.conn.executemany("DELETE FROM mods WHERE ordinal=?", rows_to_delete)

            # and reinsert
            query = "INSERT INTO mods(" + ", ".join(constants.db_fields) + ") VALUES ("
            query += ", ".join("?" * len(constants.db_fields)) + ")"

            self.DB.conn.executemany(query, dbrowgen)

        # And finally save changes to disk
        self.saveModList()


    def saveModList(self):
        """Request that database manager save modinfo to disk"""
        self.DB.saveModDB(self.active_profile.modinfo)

    def updateModName(self, ordinal: int, new_name:str):
        """
        Have the DBMan update a mod's 'name' (e.g. the string that appears in the mod-table and which is customizable by the user)
        :return:
        """
        self.LOGGER.debug("New name for mod #{}: {}".format(ordinal, new_name))
        self.DB.update_("UPDATE mods SET name=? WHERE ordinal = ?", (new_name, ordinal))
        # print([t for t in self.DB.execute_("Select * from mods where ordinal = ?", (ordinal, ))])

    def updateModState(self, ordinal: int, enabled_status: bool):
        self.LOGGER.debug("New status for mod #{}: {}".format(ordinal, "Enabled" if enabled_status else "Disabled"))
        self.DB.update_("UPDATE mods SET enabled=? WHERE ordinal = ?", (int(enabled_status), ordinal))
        # print([t for t in self.DB.execute_("Select * from mods where ordinal = ?", (ordinal,))])

    def getModDir(self, modName):
        """
        queries the db for the directory associated with the given name
        :param modName:
        :return:
        """

        return self.DB.getOne('SELECT directory from mods where name= ? ', (modName, ))[0]


    def saveHiddenFiles(self):
        self.DB.saveHiddenFiles(self.active_profile.hidden_files)


    def getErrors(self, error_type):
        """
        Returns any recorded errors of the specified type from the active profile.
        'Not Found' means that a mod was in the profile's list of installed mods, but could not be found on disk.
        'Not Listed' means that a mod was found on disk that was not previously in the list of installed mods.

        :param int error_type: constants.SE_NOTFOUND = 0; constants.SE_NOTLISTED = 1
        """
        return self.active_profile.syncErrors[constants.SE_NOTFOUND]