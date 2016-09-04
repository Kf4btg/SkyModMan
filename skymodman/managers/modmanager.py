from pathlib import Path

from skymodman.types import ModEntry, Alert
from skymodman.managers import (config as _config,
                                database as _database,
                                profiles as _profiles,
                                paths as _paths
                                # installer as _install
                                )
from skymodman.constants import alerts, db_fields as _db_fields
from skymodman.constants.keystrings import (Dirs as ks_dir,
                                            Section as ks_sec,
                                            INI as ks_ini)
from skymodman.installer.common import FileState
from skymodman.utils import withlogger

__manager = None


Config = None   # type: _config.ConfigManager
Profiler = None # type: _profiles.ProfileManager
DB = None       # type: _database.DBManager

# singleton Manager
def Manager():
    global __manager
    if __manager is None:
        global Config, Profiler, DB
        __manager = _ModManager()

        Config = __manager.Config
        Profiler = __manager.Profiler
        DB = __manager.DB

    return __manager



@withlogger
class _ModManager:
    """
    The primary interface to all the management backends. Only one
    should be active at a time, thus, this class should not be
    instantiated directly. Instead, obtain a reference to the manager
    using the module-level Manager() method.
    """

    def __init__(self):

        # first, initialize the alerts
        alerts.init_alerts(self)

        # the order here matters; profileManager requires config
        self._pathman = _paths.PathManager(self)
        self._configman = _config.ConfigManager(self)

        self._profileman = _profiles.ProfileManager(self._configman.paths.dir_profiles, self)

        # set up db, but do not load info until requested
        self._dbman = _database.DBManager(self)
        self._db_initialized = False

        # install manager; instantiated when needed
        # self._iman = None # type: _install.InstallManager

        # used when the installer needs to query mod state
        self._enabledmods = None

        # set of issues that arise during operation
        self.alerts = set() # type: Set [Alert]

        # add a test alert
        self.alerts.add(alerts.test_alert)
        #     Alert(level='NORMAL', label='Test Alert',
        #           desc="This is a Test alert",
        #           fix="You cannot fix this. Ever.",
        #           check=lambda: True)
        # )


    ## Sub-manager access properties ##

    @property
    def Paths(self):
        return self._pathman

    @property
    def Config(self):
        """Access the ConfigManager instance for the current session"""
        return self._configman

    @property
    def Profiler(self):
        """Access the Profile Manager for the current session"""
        return self._profileman

    @property
    def DB(self):
        """Access the Database Manager for the current session"""
        return self._dbman

    ## Various things what need easy access ##

    @property
    def profile(self):
        """
        :return: the currently active profile, or None if one has not
            yet been set.
        """
        return self._profileman.active_profile

    @property
    def file_conflicts(self):
        return self._dbman.file_conflicts

    @property
    def mods_with_conflicting_files(self):
        return self._dbman.mods_with_conflicting_files

    def getdbcursor(self):
        """
        Using this, a component can request a cursor object for
        interacting with the database

        :return: sqlite3.Cursor
        """
        return self._dbman.conn.cursor()
    
    ##=============================================
    ## Alerts
    ##=============================================

    @property
    def has_alerts(self):
        return len(self.alerts) > 0

    def add_alert(self, alert):
        """
        Add an ``Alert`` object to the list of registered alerts

        :param Alert alert:
        """
        self.alerts.add(alert)

    def remove_alert(self, alert):
        """
        Remove the given Alert object from the list of alerts.
        :param Alert alert:
        :return:
        """
        try:
            self.alerts.remove(alert)
        except ValueError as e:
            self.LOGGER << "Attempted to remove non-existent alert: "
            self.LOGGER.exception(e)

    def check_alerts(self):
        """
        If there are active alerts, check if they have been resolved
        and remove those which have.
        """
        # TODO: figure out the best times to do this. Like...after a new profile is loaded? After the preferences are applied/dialog is closed? When a tab is changed?? When the moon is blue???????

        to_remove = set()
        for a in self.alerts: # type: Alert
            if not a.is_active:
                to_remove.add(a)

        # remove resolved alerts
        self.alerts -= to_remove

    ##=============================================
    ## Profile Management Interface
    ##=============================================

    def activate_profile(self, profile):
        """
        Set the active profile to the profile given by `profile_name`
        :param profile:
        """

        # TODO: would it be possible...to make a context manager for profiles? I.e., the entire time a profile is active, we'd be within the "with" statement of a context manager? And when it closes we make sure to write all changed data? Or, it that's not feasible, maybe just the switch mechanics below could be wrapped in one for better error handling.

        # save this in case of a rollback
        old_profile = self.profile.name if self.profile else None

        try:
            # make sure we're dealing with just the name
            if isinstance(profile, _profiles.Profile):
                profile = profile.name
            assert isinstance(profile, str)

            self._set_profile(profile)

        except Exception as e:
            # if ANY errors occur, rollback the profile-switch
            self.LOGGER.exception(e)
            self.LOGGER << "Error while activating profile. Rolling back."

            if old_profile:
                # we can't be sure quite how far the activation process
                # made it before failing, so just do a fresh assignment
                # of the old_profile
                self._set_profile(old_profile)
            else:
                # if we came from no profile, make sure we're back there
                self._profileman.set_active_profile(None)

            return False

        # if we successfully made it here, update the config value
        # for the last-loaded profile and return True
        self._configman.last_profile = profile

        return True

    def _set_profile(self, profile_name):
        ## internal handler

        self._profileman.set_active_profile(profile_name)

        # have to reinitialize the database
        if self._db_initialized:
            self._dbman.reinit()
        else:
            self._db_initialized= True
            # well, it will be in just a second

        self._load_active_profile_data()

    def new_profile(self, name, copy_from=None):
        """
        Create and return a new Profile object with the specified name,
        optionally copying config files from the `copy_from` Profile

        :param str name:
        :param skymodman.types.Profile copy_from:
        :return: new Profile object
        """
        return self._profileman.new_profile(name, copy_from)

    def delete_profile(self, profile):
        self._profileman.delete_profile(profile)

    def rename_profile(self, new_name, profile=None):
        """
            Change the name of profile `current` to `new_name`. If `current` is
            passed as None, rename the active profile. This renames the
            profile's directory on disk.

            :param new_name:
            :param profile: the name or Profile object of the profile to
                rename; if None, rename the active profile
            """
        # get the current Profile object
        if profile is None:
            profile = self.profile
        elif isinstance(profile, str):
            profile = self._profileman[profile]

        self.LOGGER << "Renaming profile: {}->{}".format(profile.name,
                                                     new_name)
        self._profileman.rename_profile(profile, new_name)

        if profile is self.profile:
            self._configman.update_genvalue(ks_ini.LASTPROFILE,
                                            profile.name)
            # self._configman.update_config(ks_ini.LASTPROFILE,
            #                               ks_sec.GENERAL,
            #                               profile.name)

    def get_profiles(self, names_only=True):
        """
        Generator that iterates over all existing profiles.

        :param names_only: if True, only yield the profile names. If false,
            yield tuples of (name, Profile) pairs"""
        if names_only:
            yield from (n for n in self._profileman.profile_names)
        else:
            yield from self._profileman.profiles_by_name()

    def get_profile_setting(self, name, section, default=None):
        """

        :param str section: Config file section the setting belongs to
        :param str name: Name of the setting
        :param default: value to return when there is no active profile
        :return: current value of the setting
        """
        if self.profile is not None:
            return self.profile.Config[section][name]
        return default

    def set_profile_setting(self, name, section, value):
        """
        :param str section: Config file section the setting belongs to
        :param str name: Name of the setting
        :param value: the new value of the setting
        """
        if self.profile is not None:
            self.profile.save_setting(section, name, value)

    ##=================================
    ## Internal profile mgmt
    ##---------------------------------

    def _load_active_profile_data(self):
        """
        Asks the Database Manager to load the information stored
        on disk for the given profile into an in-memory database
        that will be used to provide data to the rest of the app.
        """
        self.LOGGER << "loading data for active profile: {}".format(
                       self.profile.name)

        # try to read modinfo file
        if self._dbman.load_mod_info(self.profile.modinfo):
            # if successful, validate modinfo

            self.LOGGER << "validating installed mods"
            self.validate_mod_installs()

        else:
            # if it fails, re-read mod data from disk
            self.LOGGER << "Could not load mod info; reading " \
                       "from configured mods directory."

            self._dbman.get_mod_data_from_directory(
                self.get_directory(ks_dir.MODS))

            # and [re]create the cache file
            self.save_mod_list()

        # clear the "list of enabled mods" cache (used by installer)
        self._enabledmods = None

        # FIXME: avoid doing this on profile change
        # _logger << "Loading list of all Mod Files on disk"

        # make sure we use the profile override if there is one
        self._dbman.load_all_mod_files(
            self.get_directory(ks_dir.MODS))

        # let's also add the files from the base
        # Skyrim Data folder to the db

        sky_dir = self.get_directory(ks_dir.SKYRIM)

        # first check that we found the Skyrim directory
        if not sky_dir:
            ## TODO: store common alerts as constants externally
            self.add_alert(alerts.dnf_skyrim)
            #     Alert(level='HIGH', label="Skyrim not found",
            #           desc="The main Skyrim installation folder could not be found or is not defined.",
            #           fix="Choose an existing folder in the Preferences dialog.",
            #           check=lambda: self.get_directory(ks_dir.SKYRIM) is None)
            # )
            self.LOGGER.warning("The main Skyrim folder could not be "
                           "found. That's going to be a problem.")
        else:
            for f in Path(sky_dir).iterdir():
                if f.name.lower() == "data":
                    self._dbman.add_files_from_dir('Skyrim', str(f))
                    break

        # [print(*r) for r in _dataman._con.execute("select *
        # from modfiles where directory='Skyrim'")]

        # _logger << "Finished loading list of all Mod Files on disk"

        # detect which mods contain files with the same name
        self._dbman.detect_file_conflicts()

        # load set of files hidden by user
        self._dbman.load_hidden_files(self.profile.hidden_files)

    ##=============================================
    ## Mod Information
    ##=============================================

    def get_mod_errors(self):
        """

        :rtype: dict[str, int]
        :return: a dictionary of mod-directory:error-type for every
            mod in the database
        """

        return {r['directory']: r['error'] for r in
                self._dbman.select("mods", "directory", "error")}

    def allmodinfo(self):
        """
        Obtain an iterator over all the rows in the database which yields
        _all_ the info for a mod as a dict, intended for feeding to
        ModEntry(**d) or using directly.

        :rtype: __generator[dict[str, sqlite3.Row], Any, None]
        """
        for row in self._dbman.get_mod_info():
            yield dict(zip(row.keys(), row))

    def enabled_mods(self):
        """
        yields the names of enabled mods for the currently active profile
        """
        yield from self._dbman.enabled_mods(True)

    def disabled_mods(self):
        yield from self._dbman.disabled_mods(True)

    def validate_mod_installs(self):
        """
        Queries the disk and the database to see if the respective
        lists of mods are in sync. If not, any issues encountered
        are recorded on the active profile object.

        :return: True if no errors encountered, False otherwise
        """
        return self._dbman.validate_mods_list(
            self.get_directory(ks_dir.MODS))


    ##=============================================
    ## Data Persistence
    ##=============================================

    def save_user_edits(self, changes):
        """
        :param collections.abc.Iterable[ModEntry] changes: an iterable of ModEntry objects
        """

        rows_to_delete = [(m.ordinal,) for m in changes]

        # a generator that creates tuples of values by sorting the
        # values of the modentry according the order defined in
        # constants._db_fields
        dbrowgen = (
            tuple([getattr(mod, field)
                   for field in sorted(mod._fields,
                                       key=lambda f: _db_fields.index(
                                           f))
                   ])
            for mod in changes)

        # using the context manager may allow deferrable foreign
        # to go unsatisfied for a moment

        with self._dbman.conn:
            # delete the row with the given ordinal
            self._dbman.delete("mods", "ordinal=?", rows_to_delete, True)

            # and reinsert

            self._dbman.insert(len(_db_fields), "mods", *_db_fields,
                               params=dbrowgen)

        # And finally save changes to disk
        self.save_mod_list()

    def save_mod_list(self):
        """Request that database manager save modinfo to disk"""
        self._dbman.save_mod_info(self.profile.modinfo)
        # reset so that next install will reflect the new state
        self._enabledmods = None

    def save_hidden_files(self):
        self._dbman.save_hidden_files(self.profile.hidden_files)

    ##=============================================
    ## Configuration Management Interface
    ##=============================================

    def get_config_value(self, name, section=ks_sec.NONE,
                         default=None, use_profile_override=True):

        """
        Get the current value of one of the main config values

        :param name: the key for which to retrieve the value
        :param section: "General" or "Directories" or "" (enum values
            are preferred)
        :param default: value to return if the section/key is not found
        :param use_profile_override:

        :return:
        """
        # ap = self.profile

        # IF there is an active profile, AND we happen to be asking for
        # a directory, AND use_profile_override is True, AND the active
        # profile actually contains an override for this directory AND
        # that override is currently enabled............:
        #   return that override

        if section == ks_sec.DIRECTORIES:
            val = self._pathman.path(name, use_profile_override)

        # if ap and section == ks_sec.DIRECTORIES \
        #         and use_profile_override \
        #         and ap.override_enabled(name) \
        #         and ap.diroverride(name):
        #     val = ap.diroverride(name)
        else:
            # in all other situations, just
            # return the stored config value
            val = self._configman[name]

        # if the value stored in config was None (or some other
        # False-like value), return the `default` parameter instead
        return val if val else default

        # assume section is "NONE", meaning this is not a value
        # from the main config file (but is still tracked by
        # config manager...TODO: there's probably a better way to do this)
        # val = conf[name]


    def set_config_value(self, name, section, value, set_profile_override=True):
        """
        Update the value for the setting with the given name under the given
        section.

        :param name:
        :param section:
        :param value: the new value to save
        :param set_profile_override: if the key to be updated is a directory,
            then, if this parameter is True, the updated value will be set
            as a directory override in the local settings of the active
            profile (if any). If this parameter is False, then the default
            value for the path will be updated instead, and the profile
            overrides left untouched.
        """
        if section == ks_sec.DIRECTORIES:
            # if a profile is active, set an override
            self.set_directory(name, value,
                                    set_profile_override and
                                    self.profile is not None)

        elif section == ks_sec.GENERAL:
            self._configman.update_genvalue(name, value)
            # self._configman.update_config(name, section, value)


    # def _change_configured_path(self, directory, new_path, p_override):
    #
    #     self._pathman.set_path(directory, new_path, p_override)

        # if p_override:
        #     self.set_profile_setting(directory,
        #                              ks_sec.OVERRIDES,
        #                              new_path)
        # else:
        #     self._pathman[directory] = new_path
            # self._configman.update_config(directory,
            #                               ks_sec.DIRECTORIES,
            #                               new_path)

    def set_directory(self, key, path, profile_override=False):
        """
        Update the configured value of the directory indicated by `key`
        (from constants.keystrings.Dirs) to the new value given in `path`

        :param key:
        :param str path:
        :param profile_override:
        """
        self._pathman.set_path(key, path, profile_override)

        # self.set_config_value(key, ks_sec.DIRECTORIES,
        #                       path, profile_override)

    def get_directory(self, key, use_profile_override=True):
        """
        Get the stored path for the app directory referenced by `key`.
        If use_profile_override is True and an override is set in the
        currently active profile for this directory, that override will
        be returned. In all other cases, the value from the default
        config will be returned.

        :param key: constants.ks_dir.WHATEVER
        :param use_profile_override: Return the path-override from the
            currently active profile, if one is set.
        :return:
        """

        p = self._pathman.path(key, use_profile_override)
        return str(p) if p else ""
        # return str(self._pathman.path(key, use_profile_override))

        # return self.get_config_value(
        #     key, ks_sec.DIRECTORIES,
        #     use_profile_override=use_profile_override)

    ##=============================================
    ## Installation
    ## --------------------------------------------
    ## Methods below are asynchronous
    ##=============================================

    async def get_installer(self, archive, extract_dir=None):
        """
        Generate and return an InstallManager instance for the given
        mod archive.

        :param archive:
        :param extract_dir: if provided, the installer will search
            for a "fomod" directo5ry within the archive and extract
            its contents to the given directory. If ``None`` or omitted,
            the archive is not examined before returning
        :return: the prepared installer
        """

        from skymodman.managers import installer as _install

        # instantiate a new install manager
        installer = _install.InstallManager(archive, self)


        if extract_dir is not None: # we're expecting a fomod

            # find the fomod folder, if there is one
            fomodpath = await installer.get_fomod_path()

            self.LOGGER << "fomodpath: {}".format(fomodpath)

            if fomodpath is not None:

                # if we found a fomod folder, extract (only) that
                # that folder and its contents to a temporary directory
                await installer.extract(extract_dir, [fomodpath])
                # modconf = os.path.join(extract_dir, fomodpath,
                #                        "ModuleConfig.xml")

                # path to extracted fomod folder
                fdirpath = Path(extract_dir, fomodpath)
                for fpath in fdirpath.iterdir():

                    # make sure we have actually have a fomod config script
                    if fpath.name.lower() == 'moduleconfig.xml':

                        # if so, get it ready for the installer
                        await installer.prepare_fomod(str(fpath),
                                                       extract_dir)
                        break

                        # if os.path.exists(modconf):
                        #     await installman.prepare_fomod(modconf, extract_dir)
                        # elif os.path.exists(modconf.lower()):
                        #     await installman.prepare_fomod(modconf.lower(), extract_dir)

        del _install
        return installer
        # save a reference
        # self._iman = installer
        # return installer object
        # return self._iman

    # async def get_mod_archive_structure(self, archive=None):
    #     """
    #
    #     :param archive:
    #     :rtype: skymodman.utils.archivefs.ArchiveFS
    #     :return: the internal folder structure of the mod `archive`
    #         represented by a Tree structure
    #     """
    #     if not archive and not self._iman:
    #         raise TypeError(
    #             "If no InstallManager is active, "
    #             "an archive file must be provided.")
    #
    #     if archive and (
    #         not self._iman or self._iman.archive != archive):
    #         self._iman = _install.InstallManager(archive)
    #
    #     # modstruct = await installman.mod_structure_tree()
    #     # return modstruct
    #
    #     modfs = await self._iman.mkarchivefs()
    #     return modfs

    ##=============================================
    ## Installation Helpers
    ##---------------------------------------------
    ## These are used to query dependencies for the
    ## fomod installer
    ##=============================================


    def checkFileState(self, file, state):
        """
        Query the database of known mod files for the given filename and
        return whether it is in the given Activation State

        M = "Missing"
        I = "Inactive"
        A = "Active"

        :param file:
        :param state:
        :return: bool
        """

        matches = list(r['directory'] for r in
                       self._dbman.select("modfiles",
                                         "directory",
                                          where="filepath = ?",
                                          params=(file.lower(), )
                                          ))

        if matches:
            if any(m == 'Skyrim'
                   or self.mod_is_enabled(m)
                   for m in matches):
                # at least one mod containing the matched file is
                # enabled (or base skyrim), so return true iff desired
                # state is 'active'
                return state == FileState.A

            # otherwise, every matched mod was disabled ,
            # so return True iff desired state was 'inactive'
            return state == FileState.I

        # if no matches found, return true iff
        # state being checked is 'missing'
        return state == FileState.M

    def mod_is_enabled(self, mod_directory):
        """
        :param mod_directory:
        :return: True if mod is marked as enabled for the current profile
        """
        if not self._enabledmods:
            # self._enabledmods is uninitialized
            self._enabledmods = list(self.enabled_mods())

        return mod_directory in self._enabledmods
