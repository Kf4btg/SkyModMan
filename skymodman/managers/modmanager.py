from pathlib import Path

from skymodman import exceptions
from skymodman.types import ModEntry, Alert
from skymodman.managers import (config as _config,
                                database as _database,
                                profiles as _profiles,
                                paths as _paths
                                )
from skymodman.constants import overrideable_dirs, db_fields as _db_fields, db_field_order as _field_order
from skymodman.constants.keystrings import (Dirs as ks_dir,
                                            Section as ks_sec,
                                            INI as ks_ini)
from skymodman.installer.common import FileState
from skymodman.log import withlogger

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
        self._diralerts={}
        self._init_diralerts()

        # the order here matters; profileManager requires config,
        # config requires Paths...
        self._pathman = _paths.PathManager(mcp=self)
        self._configman = _config.ConfigManager(mcp=self)

        self._profileman = _profiles.ProfileManager(
            self._pathman.dir_profiles, mcp=self)

        # set up db, but do not load info until requested
        self._dbman = _database.DBManager(mcp=self)

        # used when the installer needs to query mod state
        self._enabledmods = None

        # cached list of mods in mod directory
        self._installed_mods = []
        # flag that tells us to re-read the list from disk
        self._modlist_needs_refresh = True

        # set of issues that arise during operation
        self.alerts = set() # type: Set [Alert]

        # make sure we have a valid profiles directory
        self.check_dir(ks_dir.PROFILES)

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

    @property
    def installed_mods(self):
        if self._modlist_needs_refresh:
            try:
                self._installed_mods = self._pathman.list_mod_folders()
            except exceptions.InvalidAppDirectoryError:
                self._installed_mods = []
            finally:
                self._modlist_needs_refresh = False

        return self._installed_mods

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
        # discard(), unlike remove(), does not throw a KeyError for
        # missing values
        self.alerts.discard(alert)

    def check_alerts(self):
        """
        If there are active alerts, check if they have been resolved
        and remove those which have.
        """
        to_remove = set()
        for a in self.alerts: # type: Alert
            if not a.is_active:
                to_remove.add(a)

        # remove resolved alerts
        self.alerts -= to_remove

    def _init_diralerts(self):
        """Create pre-constructed Alerts to use when necessary. Using
        preconstructed instances prevents duplication of alerts when
        stored by their hash-value, such as in a set or dict."""

        self._diralerts={
            ks_dir.SKYRIM: Alert(
                level=Alert.HIGH,
                label="Skyrim not found",
                desc="The main Skyrim installation folder could not be found or is not defined.",
                fix="Choose an existing folder in the Preferences dialog.",
                check=lambda: not self.get_directory(ks_dir.SKYRIM, nofail=True)),

            ks_dir.MODS: Alert(
                level=Alert.HIGH,
                label="Mods Directory not found",
                desc="The mod installation directory could not be found or is not defined.",
                fix="Choose an existing folder in the Preferences dialog.",
                check=lambda: not self.get_directory(ks_dir.MODS, nofail=True)
            ),

            ks_dir.VFS: Alert(
                level=Alert.HIGH,
                label="Virtual Filesystem mount not found",
                desc="The mount point for the virtual filesystem could not be found or is not defined.",
                fix="Choose an existing folder in the Preferences dialog.",
                check=lambda: not self.get_directory(ks_dir.VFS, nofail=True)
            ),
            ks_dir.PROFILES: Alert(
                level=Alert.HIGH,
                label="Profiles directory not found",
                desc="Profiles directory must be present for proper operation.",
                fix="Choose an existing folder in the Preferences dialog.",
                check=lambda: not self.get_directory(ks_dir.PROFILES, nofail=True)
            )
        }

    def check_dir(self, key):
        """Check that the specified app directory is valid. Add
        appropriate alert if not."""

        if self._pathman.is_valid(key, self.profile is not None):
            # if we get a valid value back,
            # remove the alert if it was present
            self.remove_alert(self._diralerts[key])
            return True
        else:
            # otherwise, add the alert

            self.add_alert(self._diralerts[key])
            return False


    def check_dirs(self):
        """
        See if all the necessary directories are defined/present. Add
        appropriate alerts if not.
        """

        for key in ks_dir:
            self.check_dir(key)

    def refresh_modlist(self):
        """Regenerate the list of installed mods"""

    ##=============================================
    ## Profile Management Interface
    ##=============================================

    def activate_profile(self, profile):
        """
        Set the active profile to given profile object
        :param profile:
        """

        # TODO: would it be possible...to make a context manager for
        # profiles? I.e., the entire time a profile is active, we'd be
        # within the "with" statement of a context manager? And when it
        # closes we make sure to write all changed data? Or, it that's
        # not feasible, maybe just the switch mechanics below could be
        # wrapped in one for better error handling.

        # save this in case of a rollback
        # old_profile = self.profile.name if self.profile else None
        old_profile = self.profile

        try:
            self._load_profile(profile)

        except Exception as e:
            # if ANY errors occur, rollback the profile-switch
            self.LOGGER.exception(e)
            self.LOGGER << "Error while activating profile. Rolling back."

            if old_profile:
                # we can't be sure quite how far the activation process
                # made it before failing, so just do a fresh assignment
                # of the old_profile
                self._load_profile(old_profile)
            else:
                # if we came from no profile, make sure we're back there
                self._profileman.set_active_profile(None)

            return False

        # if we successfully made it here, update the config value
        # for the last-loaded profile and return True
        self._configman.last_profile = profile.name

        return True

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
        """
        Remove profile folder and all contained files from disk.

        :param profile:
        """
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
            self._configman.update_genvalue(ks_ini.LAST_PROFILE,
                                            profile.name)

    def get_profiles(self, names=True, objects=True):
        """
        Generator that iterates over all existing profiles.

        results depend on options passed. If `names` and `options` are
        both True, yield tuples of (name, Profile) pairs.  If `names` is
        True and `options` is False, yield only the profile names.
        Likewise, if `names` is False and `objects` is True, yield only
        the Profile objects. If both are False...why did you call this
        in the first place?

        :param names: include names in output
        :param objects: include Profile objects in output
        """
        if names and objects:
            yield from self._profileman.profiles_by_name()
        elif names:
            yield from (n for n in self._profileman.profile_names)
        elif objects:
            yield from self._profileman.iter_profiles()

    def get_profile_setting(self, name, section, default=None):
        """

        :param str section: Config file section the setting belongs to
        :param str name: Name of the setting
        :param default: value to return when there is no active profile
        :return: current value of the setting
        """
        if self.profile:
            return self.profile.get_setting(section, name)
        return default

    def set_profile_setting(self, name, section, value):
        """
        :param str section: Config file section the setting belongs to
        :param str name: Name of the setting
        :param value: the new value of the setting
        """
        if self.profile:
            self.profile.save_setting(section, name, value)

    ##=================================
    ## Internal profile mgmt
    ##---------------------------------

    def _load_profile(self, profile):
        """internal handler for assigning new profile"""
        self.LOGGER << "<==Method called"

        # if isinstance(profile_name, Profile):
        profile_name = profile.name

        # if we have no active profile, treat this as a 'first run'
        if not self.profile:
            self._load_first_profile(profile_name)
        else:
            self._change_profile(profile_name)

    def _load_first_profile(self, profile_name):
        """Called when the first profile is selected (and any time we
        go from (no profile)->(some profile))"""

        ## **Notes on this stuff can be found under _change_profile()

        self.LOGGER << "Loading initial profile: {}".format(profile_name)

        self._profileman.set_active_profile(profile_name)

        self.check_dirs()

        if self._update_modinfo(True):
            self.find_all_mod_files(True, True)
            self._dbman.detect_file_conflicts()

        self._dbman.load_hidden_files(self.profile.hidden_files)

        self._enabledmods = None

    def _change_profile(self, profile_name):
        """
        Called to change from one profile to another (as opposed to
        starting with no profile)

        :param profile_name:
        """

        self.LOGGER << "loading data for profile: {}".format(
            profile_name)
        # keep references to currently (soon to be previously)
        # configured directories
        prev_dirs = {d: self.get_directory(d, nofail=True)
                     for d in overrideable_dirs}

        self._profileman.set_active_profile(profile_name)

        # ...only the MODS dir is ever checked; is there actually a
        # need (other than setting alerts) to track them all here?
        # Or is setting alerts a good-enough reason?

        # see if configured dirs changed:
        dir_changed = {}
        for d in overrideable_dirs:
            try:
                dir_changed[d] = self.get_directory(d) != prev_dirs[d]
            except exceptions.InvalidAppDirectoryError:
                # add alert on invalid new dir
                self.add_alert(self._diralerts[d])
                # dir has changed only if previous was valid
                dir_changed[d] = bool(prev_dirs[d])
            else:
                # remove any alerts if dir is valid
                self.remove_alert(self._diralerts[d])

        moddir_changed = self._modlist_needs_refresh = dir_changed[
                ks_dir.MODS]
        skydir_changed = dir_changed[ks_dir.SKYRIM]

        # load/generate modinfo and mod table, as needed
        if self._update_modinfo(moddir_changed) and (
                    moddir_changed or skydir_changed):
            # if we successfully managed to load/generate mod info,
            # find all mod-related files on disk (if required) and
            # analyze for conflicts
            self.find_all_mod_files(moddir_changed, skydir_changed)
            # with all discovered files loaded into the database,
            # detect which mods contain files with the same name
            self._dbman.detect_file_conflicts()


        # always need to re-check hidden files
        # todo: clear out saved hidden files for mods that have been uninstalled.
        self._dbman.load_hidden_files(self.profile.hidden_files)

        # finally, clear the "list of enabled mods" cache (used by installer)
        self._enabledmods = None

    def _update_modinfo(self, moddir_changed):
        """
        When a new (or the first) profile is loaded, rebuild the mods
        table from that profile's modinfo file. Compare the information
        in the modinfo file to the list of mods actually present in the
        installation directory and mark any missing/extra entries.

        If the modinfo file cannot be found or read, regenerate it in
        a default state using the directories found on disk. No
        validation is done in this case as the modinfo and the actual
        state of installed mods are guaranteed to be initially the same.

        :param bool moddir_changed: if False, do not reinitialize the db
            table which contains the file listings for each installed
            mod. As generating that info is an expensive operation, we
            should only do when necessary (i.e. when the user has set
            a new default/override for the Mods directory).
        :return: True if we managed to successfully read or generate the
            modinfo file. False if an error occurred
        """
        # first, reinitialize the db tables
        self._dbman.reinit(files=moddir_changed)

        # try to read modinfo file (populates "mods" table)
        if self._dbman.load_mod_info(self.profile.modinfo):
            # if successful, validate modinfo (i.e. synchronize the list
            # of mods from the modinfo file with mod folders actually
            # present in Mods directory)
            self.validate_mod_installs()
            return True
        else:
            # if it fails, (re-)read mod data from disk and create
            # a new mod_info file
            self.LOGGER << "Unable to load cached mod info; " \
                           "constructing cache from Mods directory"

            return self._gen_modinfo()

    def _gen_modinfo(self):
        """
        Generate the modinfo file for the current profile by reading
        the folders present in the mods directory

        :return: True if the modinfo file was successfully created,
            False if not.
        """
        self.LOGGER << "<==Method called"

        try:
            # populate the mods table from the main mods directory
            self._dbman.get_mod_data_from_directory()
        except exceptions.InvalidAppDirectoryError as e:
            # unless the mod directory is somehow invalid, then
            # return False
            self.LOGGER.error(e)
            return False
        else:
            # and (re)generate the modinfo file using default values
            self.save_mod_info()
            # return success
            return True

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
        self.LOGGER << "Validating installed mods"

        try:
            return self._dbman.validate_mods_list(self.installed_mods)
        except exceptions.InvalidAppDirectoryError as e:
            self.LOGGER.error(e)
            return False

    def find_all_mod_files(self, modfiles=True, skyfiles=True):
        """
        This is a relatively hefty operation that gets a list of ALL the
        individual files within each mod folder found in the main Mods
        directory. A database table is created and kept for these, along
        with a reference to which mod the file belongs. This table
        can then be analyzed to detect duplicate files and overwrites
        between mods.

        """
        self.LOGGER << "Finding mod files on disk"

        # if required, examine the disk for files.
        if modfiles:
            try:
                self._dbman.load_all_mod_files()
            except exceptions.InvalidAppDirectoryError as e:
                # don't fail-out in this case; continue w/ attempt
                # to add files from skyrim dir
                self.LOGGER.error(e)

        # let's also add the files from the base
        # Skyrim Data folder to the db
        if skyfiles:
            try:
                self._dbman.load_skyfiles(
                    self.get_directory(ks_dir.SKYRIM,
                                       aspath=True))
            except exceptions.InvalidAppDirectoryError as e:
                self.LOGGER.warning(e)

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
                                       key=_field_order.get)
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
        self.save_mod_info()

    def save_mod_info(self):
        """Have database manager save modinfo to disk"""
        self.LOGGER << "<==Method called"

        self._dbman.save_mod_info(self.profile.modinfo)
        # reset so that next install will reflect the new state
        self._enabledmods = None

    def save_hidden_files(self):
        """
        Write the collection of hidden files (stored on the profile
        object) to disk.
        """
        self.LOGGER << "<==Method called"

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
        if section == ks_sec.DIRECTORIES:
            val = self.get_directory(name, use_profile_override)

        else:
            # in all other situations, just
            # return the stored config value
            val = self._configman.get_genvalue(name)
            # val = self._configman[name]

        # if the value stored in config was None (or some other
        # False-like value), return the `default` parameter instead
        return val if val else default

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

    def set_directory(self, key, path, profile_override=False):
        """
        Update the configured value of the directory indicated by `key`
        (from constants.keystrings.Dirs) to the new value given in `path`

        :param key:
        :param str path:
        :param profile_override:
        """
        self._pathman.set_path(key, path, profile_override)

        # check if dirs valid
        self.check_dir(key)

    def get_directory(self, key, use_profile_override=True, *,
                      aspath=False, nofail=False):
        """
        Get the stored path for the app directory referenced by `key`.
        If use_profile_override is True and an override is set in the
        currently active profile for this directory, that override will
        be returned. In all other cases, the value from the default
        config will be returned.

        :param key: constants.ks_dir.WHATEVER
        :param use_profile_override: Return the path-override from the
            currently active profile, if one is set.
        :param aspath: set ``True`` to return the value as a Path object
        :param nofail: If set to ``True``, suppress an invalidDirectory
            exception and return an empty string instead (or ``None``
            if `aspath`==``True``)
        :return:
        """
        try:
            p = self._pathman.path(key, use_profile_override)
            return p if aspath else str(p)
        except exceptions.InvalidAppDirectoryError:
            if nofail:
                return None if aspath else ""
            raise

    ##=============================================
    ## Installation
    ## --------------------------------------------
    ## Some methods below are asynchronous
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
        installer = _install.InstallManager(archive, mcp=self)


        if extract_dir is not None: # we're expecting a fomod

            # find the fomod folder, if there is one
            fomodpath = await installer.get_fomod_path()

            self.LOGGER << "fomodpath: {}".format(fomodpath)

            if fomodpath is not None:

                # if we found a fomod folder, extract (only) that
                # that folder and its contents to a temporary directory
                await installer.extract(extract_dir, (fomodpath, ))
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

        del _install
        return installer

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
