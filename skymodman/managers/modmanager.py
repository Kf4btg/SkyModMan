from pathlib import Path, PurePath
from functools import lru_cache

from skymodman.utils import tree as _tree

# from skymodman import exceptions
from skymodman.types import ModEntry, ModCollection, Alert, AppFolder
from skymodman.managers import (config as _config,
                                database as _database,
                                profiles as _profiles,
                                disk as _disk,
                                collection as _collection
                                # , paths as _paths
                                )
from skymodman.constants import APPNAME, MAIN_CONFIG #overrideable_dirs,
from skymodman.constants.keystrings import (Dirs as ks_dir,
                                            Section as ks_sec,
                                            INI as ks_ini)
from skymodman.installer.common import FileState
from skymodman.log import withlogger

## appfolder defaults
appfolder_defaults = {
    # name is dict key
    ks_dir.SKYRIM: {
        'display_name': "Skyrim Installation",
        'default_path': "",
    },
    ks_dir.MODS: {
        'display_name': "Mods Directory",
        'default_path': "%APPDATADIR%/mods",
    },
    ks_dir.VFS: {
        'display_name': "Virtual FS Mount Point",
        'default_path': "%APPDATADIR%/skyrimfs",
    },
    ks_dir.PROFILES: {
        'display_name': "Profiles Directory",
        'default_path': "%APPCONFIGDIR%/profiles",
    }
}


@withlogger
class ModManager:
    """
    The primary interface to all the management backends. Only one
    should be active at a time, thus, this class should not be
    instantiated directly. Instead, obtain a reference to the manager
    using the module-level Manager() method.
    """

    def __init__(self):

        # first, initialize the alerts
        self._diralerts={}
        # set of issues that arise during operation
        self.alerts = set() # type: Set [Alert]

        # init attributes for submanagers
        self._configman = None
        """:type: skymodman.managers.config.ConfigManager"""
        self._profileman = None
        """:type: skymodman.managers.profiles.ProfileManager"""
        self._dbman = None
        """:type: skymodman.managers.database.DBManager"""
        self._ioman = None
        """:type: skymodman.managers.disk.IOManager"""
        self._collman = None
        """:type: skymodman.managers.collection.ModCollectionManager"""

        ## these (probably) don't really
        ## need a separate manager; they
        ## should pretty much manage themselves.
        self._folders = {} # type: dict [str, AppFolder]

        # used when the installer needs to query mod state
        self._enabledmods = None

        # cached list of mods in mod directory
        self._managed_mods = []

        # mod collection instance
        self._modcollection = ModCollection()
        # set as collection for all ModEntry objects
        ModEntry.collection = self._modcollection

        # track when we're switching profiles
        self.in_profile_switch=False

    ##=============================================
    ## Setup
    ##=============================================

    def setup(self):
        """Initialize the subcomponents and load all required data."""
        # use appdirs to get base paths
        import appdirs
        _appdata = appdirs.user_data_dir(APPNAME)
        _appconf = appdirs.user_config_dir(APPNAME)

        self._init_diralerts()
        self._setup_folders(_appdata, _appconf)

        ## sub-managers ##
        # the order here matters; profileManager requires config,

        self._configman = _config.ConfigManager(config_dir=_appconf,
                                                data_dir=_appdata,
                                                config_file_name=MAIN_CONFIG,
                                                mcp=self)

        self._profileman = _profiles.ProfileManager(mcp=self)

        # set up db, but do not load info until requested
        self._dbman = _database.DBManager(mcp=self)

        self._ioman = _disk.IOManager(mcp=self)

        self._collman = _collection.ModCollectionManager(mcp=self)

        # make sure we have a valid profiles directory
        # self.check_dir(ks_dir.PROFILES)
        # self.check_dirs()

        del appdirs


    def _setup_folders(self, appdata, appconf):
        for name, info in appfolder_defaults.items():
            self._folders[name] = AppFolder(
                name,
                info['display_name'],
                # fill in placeholders
                default_path=info['default_path']
                    .replace('%APPDATADIR%', appdata)
                    .replace('%APPCONFIGDIR%', appconf)
            )

        # listen for changes to folder paths
        for f in ('mods', 'skyrim', 'profiles', 'vfs'):
            self._folders[f].register_change_listener(self.on_dir_change)

        self._folders['mods'].register_change_listener(
            self.refresh_modlist)

    @property
    def Folders(self):
        """return the mapping of keys to AppFolder instances."""
        return self._folders

    ##=============================================
    ## Sub-manager access properties
    ##=============================================

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

    @property
    def Collector(self):
        """Access the Mod Collection Manager for the current session"""
        return self._collman

    @property
    def IO(self):
        """Access the IOManager (disk read/write) for the current session """
        return self._ioman

    ## Various things what need easy access ##

    @property
    def modcollection(self):
        """Return the ModCollection sequence containing the currently
        loaded ModEntries"""
        return self._collman.collection

    @property
    def profile(self):
        """
        Return the currently active profile, or ``None`` if one has not
        yet been set.
        """
        return self._profileman.active_profile

    @property
    def default_profile(self):
        """Name of the profile configured to be 'default'"""
        return self.get_config_value(ks_ini.DEFAULT_PROFILE)

    @property
    def last_profile(self):
        """Name of the most recently loaded profile"""
        return self.get_config_value(ks_ini.LAST_PROFILE)

    @property
    def managed_mod_folders(self):
        """
        Return a list of every mod directory located in the configured
        'Mods' storage folder. This may not be every 'installed' mod,
        as it does not take into account unmanaged mods in the skyrim
        data folder
        """
        return self._managed_mods

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
        :return: True if the alert was added, False if it was already
            present
        """
        if alert in self.alerts:
            return False

        self.alerts.add(alert)
        return True

    def remove_alert(self, alert):
        """
        Remove the given Alert object from the list of alerts.

        :param Alert alert:
        :return: True if the alert was removed, False if it was not
            present in the set
        """
        if alert in self.alerts:
            self.alerts.remove(alert)
            return True
        return False

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

        ## TODO: remove 'check' attribute (or find a real use for it)
        self._diralerts={
            ks_dir.SKYRIM: Alert(
                level=Alert.HIGH,
                label="Skyrim not found",
                desc="The main Skyrim installation folder could not be found or is not defined.",
                fix="Choose an existing folder in the Preferences dialog.",
                check=lambda: None
                # check=lambda: not self.get_directory(ks_dir.SKYRIM, nofail=True)),
            ),
            ks_dir.MODS: Alert(
                level=Alert.HIGH,
                label="Mods Directory not found",
                desc="The mod installation directory could not be found or is not defined.",
                fix="Choose an existing folder in the Preferences dialog.",
                check=lambda: None
                # check=lambda: not self.get_directory(ks_dir.MODS, nofail=True)
            ),
            ks_dir.VFS: Alert(
                level=Alert.HIGH,
                label="Virtual Filesystem mount not found",
                desc="The mount point for the virtual filesystem could not be found or is not defined.",
                fix="Choose an existing folder in the Preferences dialog.",
                check=lambda: None
                # check=lambda: not self.get_directory(ks_dir.VFS, nofail=True)
            ),
            ks_dir.PROFILES: Alert(
                level=Alert.HIGH,
                label="Profiles directory not found",
                desc="Profiles directory must be present for proper operation.",
                fix="Choose an existing folder in the Preferences dialog.",
                check=lambda: None
                # check=lambda: not self.get_directory(ks_dir.PROFILES, nofail=True)
            )
        }

    def check_dir(self, key):
        """Check that the specified app directory is valid. Add
        appropriate alert if not."""

        if self._folders[key].is_valid:
            self.remove_alert(self._diralerts[key])
            return True
        else:
            self.add_alert(self._diralerts[key])
            return False

    def check_dirs(self):
        """
        See if all the necessary directories are defined/present. Add
        appropriate alerts if not.
        """

        for key in ks_dir:
            self.check_dir(key)

    def refresh_modlist(self, modfolder: AppFolder):
        """Regenerate the cached list of installed mods"""
        self.LOGGER << "Refreshing mods list"
        # this actually reads the disk
        self._managed_mods = list(iter(modfolder))
        # self._managed_mods = [n for n in modfolder]

    # def on_dir_change(self, folder, previous, current):
    def on_dir_change(self, folder):
        """
        handler for directory-change events

        :param AppFolder folder:
        """

        # an appfolder instance is "False" if the path is unset or invalid
        if not folder:
            self.add_alert(self._diralerts[folder.name])
        else:
            self.remove_alert(self._diralerts[folder.name])

        if not self.in_profile_switch and not folder.is_overriden:
            try:
                self._configman.update_folderpath(folder)
            except AttributeError:
                # config manager not initialized yet
                pass

        # if self._configman and not self.in_profile_switch and not folder.is_overriden:
        #     self._configman.update_folderpath(folder)
        #     self.set_config_value(folder.name, folder.path, ks_sec.DIRECTORIES)

    ##=============================================
    ## Profile Management Interface
    ##=============================================

    def activate_profile(self, profile):
        """
        Set the active profile to the profile with the given name

        :param str profile:
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

        # flag that tells us we're in the middle of switching profiles;
        # this is mainly so that a dir-changed notification from an
        # AppFolder does not incorrectly update the config file
        self.in_profile_switch = True

        success = True
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
                self._load_profile(old_profile.name)
            else:
                # if we came from no profile, make sure we're back there
                self._profileman.set_active_profile(None)


            success = False
        else:
            # if we successfully made it here, update the config value
            # for the last-loaded profile and return True
            self.set_config_value(ks_ini.LAST_PROFILE, profile)
        finally:
            self.in_profile_switch = False

        return success

    def new_profile(self, name, copy_from=None):
        """
        Create and return a new Profile object with the specified name,
        optionally copying config files from the `copy_from` Profile

        :param str name:
        :param str copy_from:
        :return: new Profile object
        """
        return self._profileman.new_profile(name, copy_from)

    def delete_profile(self, profile):
        """
        Remove profile folder and all contained files from disk.

        :param str profile:
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

    def get_profiles(self, names=True, objects=False):
        """
        Generator that iterates over all existing profiles.

        results depend on options passed. If `names` and `objects` are
        both True, yield tuples of (name, Profile) pairs.  If `names` is
        True and `objects` is False, yield only the profile names.
        Likewise, if `names` is False and `objects` is True, yield only
        the Profile objects. If both are False...why did you call this
        in the first place?

        :param names: include names in output
        :param objects: include Profile objects in output
        """
        if names and objects:
            yield from self._profileman.profiles_by_name()
        elif names:
            yield from self._profileman.profile_names
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

    def set_default_profile(self, profile_name):
        """
        Set the profile with the given name as the default profile
        for the application

        :param profile_name:
        """

        if profile_name in self._profileman.profile_names:
            self.set_config_value(ks_ini.DEFAULT_PROFILE, profile_name)

    ##=================================
    ## Internal profile mgmt
    ##---------------------------------

    def _load_profile(self, profile:str):
        """internal handler for assigning new profile"""
        self.LOGGER << "<==Method called"

        # if we have no active profile, treat this as a 'first run'
        if not self.profile:
            self._load_first_profile(profile)
        else:
            self._change_profile(profile)

    def _load_first_profile(self, profile_name):
        """Called when the first profile is selected (and any time we
        go from (no profile)->(some profile))"""

        ## **Notes on this stuff can be found under _change_profile()

        self.LOGGER << "Loading initial profile: {}".format(profile_name)

        # this will enable any profile overrides there may be
        self._profileman.set_active_profile(profile_name)

        # self.check_dirs()

        if self._update_modinfo(True, True):
            self.find_all_mod_files(True, True)
            self._dbman.detect_file_conflicts()

        self.load_hidden_files()
        # self._dbman.load_hidden_files(self.profile.hidden_files)

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
        prev_dirs = {d: self._folders[d].path for d in ks_dir}

        # this will enable any profile overrides there may be
        self._profileman.set_active_profile(profile_name)

        # ...only the MODS dir is ever checked; is there actually a
        # need  to track them all here?

        moddir_changed = prev_dirs['mods']   != self._folders['mods']
        skydir_changed = prev_dirs['skyrim'] != self._folders['skyrim']

        # load/generate modinfo and mod table, as needed
        if self._update_modinfo(moddir_changed, skydir_changed) and (
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
        self.load_hidden_files()
        # self._dbman.load_hidden_files(self.profile.hidden_files)

        # finally, clear the "list of enabled mods" cache (used by installer)
        self._enabledmods = None

    def _update_modinfo(self, moddir_changed, skydir_changed):
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

        self.LOGGER << "<==Method called"

        # first, reinitialize the db tables
        # self._dbman.reinit(files=moddir_changed, sky=skydir_changed)
        self._dbman.reinit(files=moddir_changed)

        # and the mod collection
        self._collman.reset()

        # try to read modinfo file (creates the mod collection)
        if self._ioman.load_saved_modlist(self.profile.modinfo,
                                          self._collman.collection):
            # print(self._collman.collection.verbose_str())

            # populate the db
            # self._dbman.populate_mods_table(self._collman.collection)
            self._dbman.populate_mods_table(
                tuple(entry) for entry in
                self._collman.collection
            )

        # if self._dbman.load_mod_info(self.profile.modinfo):
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

        if self._ioman.load_raw_mod_info(self._collman.collection):
            # populate db from collection
            self._dbman.populate_mods_table(self._collman.collection)
            # save info (to generate file since it likely doesn't exist)
            self.save_mod_info()
            return True


        # if self._folders['mods']:
            # populate the mods table from the main mods directory
            # self._dbman.get_mod_data_from_directory(self._folders['mods'].path)
            # self._dbman.load_mod_info_from_disk(self._folders['mods'].path)
            # and (re)generate the modinfo file using default values
            # self.save_mod_info()
            # return success
            # return True
        else:
            self.LOGGER.error("Mods Folder is unset or could not be found")
            return False

    ##=============================================
    ## Mod Information
    ##=============================================

    def get_mod_errors(self):
        """

        :rtype: dict[str, int]
        :return: a dictionary of mod-directory:error-type for every
            mod in the database
        """
        return self._collman.errors


        # return {r['directory']: r['error'] for r in
        #         self._dbman.select("mods", "directory", "error")}

    # def allmodinfo(self):
    #     """
    #     Obtain an iterator over all the rows in the database which yields
    #     _all_ the info for a mod as a dict, intended for feeding to
    #     ModEntry(**d) or using directly.
    #
    #     This ignores the fake 'Skyrim' mod, though it is still
    #     accessible in the database table
    #
    #     :rtype: __generator[dict[str, sqlite3.Row], Any, None]
    #     """
    #     for row in self._dbman.get_mod_info():
    #         yield dict(zip(row.keys(), row))

    def enabled_mods(self):
        """
        yields the names of enabled mods for the currently active profile
        """
        # yield from self._dbman.enabled_mods(True)
        yield from (m.name for m in self._collman.enabled_mods())

    def disabled_mods(self):
        yield from (m.name for m in self._collman.disabled_mods())

        # yield from self._dbman.disabled_mods(True)

    def validate_mod_installs(self):
        """
        Queries the disk and the database to see if the respective
        lists of mods are in sync. If not, any issues encountered
        are recorded on the active profile object.

        :return: True if no errors encountered, False otherwise
        """
        self.LOGGER << "Validating installed mods"
        return self._collman.validate_mods(self.managed_mod_folders)

        # try:
        # return self._dbman.validate_mods_list(self.managed_mod_folders)
        # except exceptions.InvalidAppDirectoryError as e:
        #     self.LOGGER.error(e)
        #     return False

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

        # add the files from the base
        # Skyrim Data folder to the db
        if skyfiles:
            if self._folders['skyrim']:

                for mod, file_list, missing_files in \
                        self._ioman.load_unmanaged_files():
                    if file_list:
                        self._dbman.add_files('mod', mod, file_list)
                    if missing_files:
                        self._dbman.add_files('missing', mod, missing_files)

            else:
                self.LOGGER.warning("Skyrim directory is unset")

        # if required, examine the disk for files.
        if modfiles:
            if self._folders['mods']:
                # iterate over returned pairs (name, list) from iomanager
                for mod, file_list in self._ioman.load_all_mod_files():
                    # insert into db
                    self._dbman.add_files('mod', mod, file_list)
                    # self._dbman.add_to_modfiles_table(mod, file_list)


            # try:
            #     self._dbman.load_all_mod_files(self._folders['mods'].path)
            else:
            # except exceptions.InvalidAppDirectoryError as e:
                self.LOGGER.error("Mods directory is unset or could not be found")


    def load_hidden_files(self):
        """
        Read profile's list of files hidden by user (if any) and record
        in database
        """
        # get info on hidden files from io-manager
        for mod_key, hidden_list in self._ioman.load_hidden_files(
                self.profile.hidden_files):
            # add to database
            self._dbman.add_files('hidden', mod_key, hidden_list)
            # self._dbman.add_to_hidden_files_table(mod_key, hidden_list)

    ##=============================================
    ## Data Persistence
    ##=============================================

    # def save_user_edits(self, changes):
    #     """
    #     :param collections.abc.Iterable[ModEntry] changes: an iterable of ModEntry objects
    #     """
    #
    #     rows_to_delete = [(m.ordinal,) for m in changes]
    #
    #     # a generator that creates tuples of values by sorting the
    #     # values of the modentry according the order defined in
    #     # constants._db_fields
    #     dbrowgen = (
    #         tuple([getattr(mod, field)
    #                for field in sorted(mod._fields,
    #                                    key=_field_order.get)
    #                ])
    #         for mod in changes)
    #
    #     # using the context manager may allow deferrable foreign
    #     # to go unsatisfied for a moment
    #
    #     with self._dbman.conn:
    #         # delete the row with the given ordinal
    #         self._dbman.delete("mods", "ordinal=?", rows_to_delete, True)
    #
    #         # and reinsert
    #
    #         self._dbman.insert(len(_db_fields), "mods", *_db_fields,
    #                            params=dbrowgen)
    #
    #     # And finally save changes to disk
    #     self.save_mod_info()

    def save_mod_info(self):
        """Have database manager save modinfo to disk"""
        self.LOGGER << "<==Method called"

        self._ioman.save_mod_info(self.profile.modinfo,
                                  self._collman.collection)

        # self._dbman.save_mod_info(self.profile.modinfo)
        # reset so that next install will reflect the new state
        self._enabledmods = None

    def save_hidden_files(self):
        """
        Write the collection of hidden files (stored on the profile
        object) to disk.
        """
        self.LOGGER << "<==Method called"

        # utils.tree.Tree uses json internally to stringify itself, so
        # we just need to write the string to disk

        with self.profile.hidden_files.open('w') as f:
            f.write(str(self._dbman.get_hidden_file_tree()))

        # use static json-serializing method
        # _disk.IOManager.json_write(self.profile.hidden_files,
        #                            self._dbman.get_hidden_file_tree())

        # self._dbman.save_hidden_files_to(self.profile.hidden_files)

    ##=============================================
    ## Configuration Management Interface
    ##=============================================

    def get_config_value(self, name, section=ks_sec.GENERAL,
                         default=None):
        """
        Get the current value of one of the main config values. Do NOT
        use this for getting directory paths; use get_directory()
        instead

        :param str name: the key for which to retrieve the value
        :param section: "General" is the only one for now
        :param default: value to return if the val is not set

        :return: value or default
        """
        # in all other situations, just
        # return the stored config value

        # if section == ks_sec.GENERAL:

        val = self._configman.get_value(section, name)

        # if the value stored in config was None (or some other
        # False-like value), return the `default` parameter instead
        if not val: return default
        return val


    def set_config_value(self, name, value, section=ks_sec.GENERAL):
        """
        Update the value for the setting with the given name under the given
        section. Use set_directory() instead of this to change the saved
        path of a directory.

        :param str name:
        :param section:
        :param value: the new value to save
        """
        self._configman.update_value(section, name, value)

        # if section == ks_sec.GENERAL:
        #     self._configman.update_genvalue(name, value)
        # else:
        #     raise exceptions.InvalidConfigSectionError(section)

    # cache the results of the ... most recent queries
    # TODO: evaluate the effectiveness of this
    @lru_cache(12)
    def get_mod_file_list(self, mod_ident):
        """
        Get the list of files contained in the given mod

        :param str mod_ident: the unique identifier of the mod (the
            mod's directory name, for managed mods)
        """
        return list(self.iter_mod_files(mod_ident))

    @lru_cache(12)
    def get_mod_file_tree(self, mod_ident):

        ftree = _tree.Tree()
        for f in  self.iter_mod_files(mod_ident):
            # convert to path
            fpath = PurePath(f) # XXX: should we add mod root?
            pathparts = fpath.parts[:-1]

            ftree.insert(pathparts, fpath.name)

        return ftree

    def iter_mod_files(self, mod_ident):
        """
        Iterate over the files contained by the given mod as stored
        in the database

        :param str mod_ident: the unique identifier of the mod (the
            mod's directory name, for managed mods)
        """

        yield from (r[0] for r in self._dbman.select('modfiles', 'filepath',
                           where="directory = ?",
                           params=(mod_ident, )))




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





