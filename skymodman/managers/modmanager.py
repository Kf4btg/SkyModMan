# import os
from pathlib import Path

from skymodman import ModEntry
from skymodman.managers import (config as _config,
                                database as _database,
                                profiles as _profiles,
                                installer as _install
                                )
# from skymodman import managers
# from skymodman.managers.profiles import ProfileManager
from skymodman.constants import (KeyStr, db_fields as _db_fields)
from skymodman.installer.common import FileState
from skymodman.utils import withlogger


# _configman  = None # type: _config.ConfigManager
# _dataman    = None # type: _database.DBManager
# _profileman = None # type: ProfileManager
# # _installman = None
#
# #shortcuts
# conf     = _configman   # type: _config.ConfigManager
# db       = _dataman     # type: _database.DBManager
# profiles = _profileman  # type: ProfileManager

# file_conflicts = None               # type collections.defaultdict[list]
# mods_with_conflicting_files = None  # type collections.defaultdict[list]
#
# _logger = None
# __enabled_mods = None
#
# _database_initialized=False
#
# def init():
#     # global _logger, _dataman, _profileman, _configman #_installman,
#     # global conf, profiles, db
#
#     # _logger = skylog.newLogger(__name__)
#
#     _configman = conf = _config.ConfigManager()
#
#     # must be created after config manager
#     _profileman = profiles = ProfileManager(
#         _configman.paths.dir_profiles)
#     # set the most-recently loaded profile as active.
#     # _profileman.set_active_profile(_configman.last_profile)
#
#     # Prepare the database, but do not load any information
#     # until it is requested.
#     _dataman = db = _database.DBManager()
#
#
# def get_cursor():
#     """
#     Using this, a component can request a cursor object for
#     interacting with the database
#     :return: sqlite3.Cursor
#     """
#     return _dataman.conn.cursor()
#
# ##=============================================
# ## Profile Management
# ##=============================================
#
# #<editor-fold desc="profiles">
#
# # def active_profile() -> Profile:
# #     """
# #     Retrieves the presently loaded Profile from the Profile Manager.
# #     :return: The active Profile object
# #     """
# #     return _profileman.active_profile
#
# def set_active_profile(profile):
#     """
#     To be called by external interfaces.
#     Set `profile` as currently loaded. Updates saved config file to mark
#     this profile as the last-loaded profile, and loads the data for the
#     newly-activated profile
#
#     :param profile:
#     :return: True if the profile is successfully loaded. False if not.
#     """
#     # save this in case of a rollback
#
#     # TODO: would it be possible...to make a context manager for profiles? I.e., the entire time a profile is active, we'd be within the "with" statement of a context manager? And when it closes we make sure to write all changed data? Or, it that's not feasible, maybe just the switch mechanics below could be wrapped in one for better error handling.
#
#     old_profile = active_profile().name if active_profile() else None
#
#     try:
#         # make sure we're dealing with just the name
#         if isinstance(profile, Profile):
#             profile = profile.name
#         assert isinstance(profile, str)
#
#         _set_profile(profile)
#         # _profileman.set_active_profile(profile)
#         #
#         # _configman.last_profile = profile
#         #
#         # global _database_initialized
#         #
#         # # have to reinitialize the database
#         # if _database_initialized:
#         #     _dataman.reinit()
#         # else:
#         #     _database_initialized=True
#         #     # well, it will be in just a second
#         #
#         # load_active_profile_data()
#
#     except Exception as e:
#         # if ANY errors occur, rollback the profile-switch
#         _logger.error(e)
#         _logger << "Error while activating profile. Rolling back."
#
#         if old_profile:
#             _set_profile(old_profile)
#         return False
#
#     return True
#
# def _set_profile(profile_name):
#     ## internal handler
#     _profileman.set_active_profile(profile_name)
#
#     _configman.last_profile = profile_name
#
#     global _database_initialized
#
#     # have to reinitialize the database
#     if _database_initialized:
#         _dataman.reinit()
#     else:
#         _database_initialized = True
#         # well, it will be in just a second
#
#     load_active_profile_data()
#
# def get_profiles(names_only = True):
#     """
#     Generator that iterates over all existing profiles.
#
#     :param names_only: if True, only yield the profile names. If false,
#         yield tuples of (name, Profile) pairs"""
#     if names_only:
#         yield from (n for n in _profileman.profile_names)
#     else:
#         yield from _profileman.profiles_by_name()
#
# def new_profile(name, copy_from = None):
#     """
#     Create and return a new Profile object with the specified name,
#     optionally copying config files from the `copy_from` Profile
#
#     :param str name:
#     :param profiles.Profile copy_from:
#     :return: new Profile object
#     """
#     return _profileman.new_profile(name, copy_from)
#
# def rename_profile(new_name, current=None):
#     """
#     Change the name of profile `current` to `new_name`. If `current` is
#     passed as None, rename the active profile. This renames the
#     profile's directory on disk.
#
#     :param new_name:
#     :param current:
#     """
#     # get the current Profile object
#     if current is None:
#         current = active_profile()
#     elif isinstance(current, str):
#         current = _profileman[current]
#
#     _logger << "Renaming profile: {}->{}".format(current.name, new_name)
#     _profileman.rename_profile(current, new_name)
#
#     if current is active_profile():
#         _configman.update_config(KeyStr.INI.LASTPROFILE,
#                                  KeyStr.Section.GENERAL, current.name)
#
#
# def delete_profile(profile):
#     _profileman.delete_profile(profile, True)
#
# def load_active_profile_data():
#     """
#     Asks the Database Manager to load the information stored
#     on disk for the given profile into an in-memory database
#     that will be used to provide data to the rest of the app.
#     """
#     _logger << "loading data for active profile: " + active_profile().name
#     # try to read modinfo file
#     if _dataman.load_mod_info(active_profile().modinfo):
#         _logger << "validating installed mods"
#         # if successful, validate modinfo
#         validate_mod_installs()
#
#     else:
#         _logger << "Could not load mod info, reading " \
#                    "from configured mods directory: " \
#                    + _configman['dir_mods']
#         # if it fails, re-read mod data from disk
#         _dataman.get_mod_data_from_directory(_configman.paths.dir_mods)
#         # and [re]create the cache file
#         save_mod_list()
#
#     # FIXME: avoid doing this on profile change
#     # _logger << "Loading list of all Mod Files on disk"
#
#     _dataman.load_all_mod_files(_configman.paths.dir_mods)
#     # let's also add the files from the base Skyrim Data folder to the db
#
#     sky_dir = _configman.paths.dir_skyrim
#
#     if sky_dir is None:
#         _logger << "The main Skyrim folder could not be found. " \
#                    "That's going to be a problem."
#     else:
#         for f in sky_dir.iterdir():
#             if f.name.lower() == "data":
#                 _dataman.add_files_from_dir('Skyrim', str(f))
#                 break
#
#     # [print(*r) for r in _dataman._con.execute("select *
#     # from modfiles where directory='Skyrim'")]
#
#
#
#     # _logger << "Finished loading list of all Mod Files on disk"
#     _logger.info("Detecting file conflicts")
#
#     _dataman.detect_file_conflicts()
#
#     _logger.info("Analyzing hidden files")
#     _dataman.load_hidden_files(active_profile().hidden_files)
#
# def hidden_files(for_mod=None):
#     """
#
#     :param str for_mod: If specified, must be the directory name of an
#         installed mod; will yield only the files marked as hidden for
#         that particular mod.
#     :return: a generator over the Rows (basically a dict with keys
#         'directory' and 'filepath') of hiddenfiles; if 'for_mod' was
#         given, will instead return a generator over just the hidden
#         filepaths (generator of strings)
#     """
#     if for_mod is None:
#         yield from _dataman.execute_("Select * from hiddenfiles")
#     else:
#         yield from (t[0] for t in _dataman.execute_(
#             "Select filepath from hiddenfiles where directory=?",
#             (for_mod, )))
#
# # def get_errors(error_type):
# #     """
# #     Yields any recorded errors of the specified type from the active
# #     profile. 'Not Found' means that a mod was in the profile's list of
# #     installed mods, but could not be found on disk. 'Not Listed' means
# #     that a mod was found on disk that was not previously in the list of
# #     installed mods.
# #
# #     :param error_type: constants.SyncError
# #     :yieldtype: str
# #     :yield: names of mods that encountered the specified error_type
# #         during load
# #     """
# #
# #     q = """SELECT mod, ordinal from (
# #         SELECT moderrors.mod as mod,
# #             moderrors.errortype as etype,
# #             mods.ordinal as ordinal
# #         FROM moderrors INNER JOIN mods
# #         ON mod = mods.directory
# #         WHERE etype = ?)
# #         ORDER BY ordinal
# #     """
# #
# #     yield from (r['mod'] for r in
# #                 _dataman.execute_(q, (error_type.value,)))
#
# def get_errors():
#     """
#
#     :rtype: dict[str, int]
#     :return: a dictionary of mod-directory:error-type for every mod in
#         the database
#     """
#
#     return {r['directory']:r['error'] for r in
#                 _dataman.execute_("SELECT directory, error FROM mods")}
#
# #</editor-fold>
#
# ##=============================================
# ## Mod Information
# ##=============================================
#
# #<editor-fold desc="modinfo">
#
# def validate_mod_installs():
#     """
#     Queries the disk and the database to see if the respective
#     lists of mods are in sync. If not, any issues encountered
#     are recorded on the active profile object.
#
#     :return: True if no errors encountered, False otherwise
#     """
#     return _dataman.validate_mods_list(_configman.list_mod_folders())
#
# def basic_mod_info():
#     """
#     Obtain an iterator over all the rows in the database which yields
#     _all_ the info for a mod as a dict, intended for feeding to
#     ModEntry(**d) or using directly.
#
#     :rtype: __generator[dict[str, sqlite3.Row], Any, None]
#     """
#     #TODO: rename this.
#     for row in _dataman.get_mod_info():
#         yield dict(zip(row.keys(), row))
#
# def enabled_mods():
#     """
#     yields the names of enabled mods for the currently active profile
#     """
#     yield from _dataman.enabled_mods(True)
#
# def disabled_mods():
#     yield from _dataman.disabled_mods(True)
#
# #</editor-fold>
#
# ##=============================================
# ## Saving changes
# ##=============================================
#
# #<editor-fold desc="saving">
#
# def save_user_edits(changes):
#     """
#     :param collections.abc.Iterable[ModEntry] changes: an iterable of ModEntry objects
#     """
#
#     rows_to_delete = [(m.ordinal, ) for m in changes]
#
#     # a generator that creates tuples of values by sorting the values of the
#     # modentry according the order defined in constants._db_fields
#     dbrowgen = (
#         tuple([getattr(mod, field)
#                for field in sorted(mod._fields,
#                                    key=lambda f: _db_fields.index(f))
#              ])
#         for mod in changes)
#
#     # using the context manager may allow deferrable foreign
#     # to go unsatisfied for a moment
#     with db.conn:
#         # db.conn.set_trace_callback(print)
#
#         # delete the row with the given ordinal
#         db.conn.executemany("DELETE FROM mods WHERE ordinal=?", rows_to_delete)
#
#         # and reinsert
#         query = "INSERT INTO mods(" + ", ".join(_db_fields) + ") VALUES ("
#         query += ", ".join("?" * len(_db_fields)) + ")"
#
#         db.conn.executemany(query, dbrowgen)
#         # db.conn.set_trace_callback(None)
#
#     # And finally save changes to disk
#     save_mod_list()
#
# def save_mod_list():
#     """Request that database manager save modinfo to disk"""
#     _dataman.save_mod_info(active_profile().modinfo)
#     global __enabled_mods
#     # reset so that next install will reflect the new state
#     __enabled_mods = None
#
# def save_hidden_files():
#     _dataman.save_hidden_files(active_profile().hidden_files)
#
#
# #</editor-fold>
#
# ##=============================================
# ## Configuration querying, updating
# ##=============================================
#
# #<editor-fold desc="config">
#
# def get_config_value(name, section=KeyStr.Section.NONE,
#                      default=None, use_profile_override = True):
#     """
#     Get the current value of one of the main config values
#
#     :param name: the key for which to retrieve the value
#     :param section: "General" or "Directories" or "" (enum values
#         are preferred)
#     :param default: value to return if the section/key is not found
#     :param use_profile_override:
#
#     :return:
#     """
#     ap = active_profile()
#
#     # IF there is an active profile, AND we happen to be asking for a
#     # directory, AND use_profile_override is True, AND the active
#     # profile actually contains an override for this directory: return
#     # that override
#     if ap and section == KeyStr.Section.DIRECTORIES \
#             and use_profile_override \
#             and ap.Config[KeyStr.Section.OVERRIDES][name]:
#         val = ap.Config[KeyStr.Section.OVERRIDES][name]
#     else:
#         # in all other situations, just return the stored config value
#         val = conf[name]
#
#     # if the value stored in config was None (or some other False-like
#     # value), return the `default` parameter instead
#     return val if val else default
#
#         # assume section is "NONE", meaning this is not a value
#         # from the main config file (but is still tracked by
#         # config manager...TODO: there's probably a better way to do this)
#         # val = conf[name]
#
#
# def set_config_value(name, section, value, set_profile_override=True):
#     """
#     Update the value for the setting with the given name under the given
#     section.
#
#     :param name:
#     :param section:
#     :param value: the new value to save
#     :param set_profile_override: if the key to be updated is a directory,
#         then, if this parameter is True, the updated value will be set
#         as a directory override in the local settings of the active
#         profile (if any). If this parameter is False, then the default
#         value for the path will be updated instead, and the profile
#         overrides left untouched.
#     """
#     if section == KeyStr.Section.DIRECTORIES:
#         # if a profile is active, set an override
#         _change_configured_path(name, value,
#                                 set_profile_override and
#                                 active_profile() is not None)
#
#     elif section == KeyStr.Section.GENERAL:
#         conf.update_config(name, section, value)
#
#
# def _change_configured_path(directory, new_path, profile_override):
#
#     if profile_override:
#         set_profile_setting(directory, KeyStr.Section.OVERRIDES, new_path)
#     else:
#         conf.update_config(directory, KeyStr.Section.DIRECTORIES, new_path)
#
#
# def set_directory(key, path, profile_override=True):
#     """
#     Update the configured value of the directory indicated by `key`
#     (from constants.KeyStr.Dirs) to the new value given in `path`
#
#     :param key:
#     :param str path:
#     :param profile_override:
#     """
#     set_config_value(key, KeyStr.Section.DIRECTORIES, path,
#                      profile_override)
#
# def get_directory(key, use_profile_override=True):
#     """
#     Get the stored path for the app directory referenced by `key`.
#     If use_profile_override is True and an override is set in the
#     currently active profile for this directory, that override will be
#     returned. In all other cases, the value from the default config
#     will be returned.
#
#     :param key: constants.KeyStr.Dirs.WHATEVER
#     :param use_profile_override: Return the path-override from the
#         currently active profile, if one is set.
#     :return:
#     """
#     return get_config_value(key,
#                             KeyStr.Section.DIRECTORIES,
#                             use_profile_override=use_profile_override)
#
# def get_profile_setting(name, section, default=None):
#     """
#
#     :param str section: Config file section the setting belongs to
#     :param str name: Name of the setting
#     :param default: value to return when there is no active profile
#     :return: current value of the setting
#     """
#     ap = active_profile()
#     if ap is not None:
#         return ap.Config[section][name]
#     return default
#
# def set_profile_setting(name, section, value):
#     """
#     :param str section: Config file section the setting belongs to
#     :param str name: Name of the setting
#     :param value: the new value of the setting
#     """
#     active_profile().save_setting(section, name, value)
#
# #</editor-fold>
#
# ##===============================================
# ## Mod [Un]Installation
# ##===============================================
#
#
# # installman=None # type: # _install.InstallManager
# async def get_installer(archive, extract_dir):
#     # global installman
#     # installman = _install.InstallManager(archive)
#
#     fomodpath = await installman.get_fomod_path()
#
#     _logger << "fomodpath: {}".format(fomodpath)
#
#     if fomodpath is not None:
#
#         await installman.extract(extract_dir, [fomodpath])
#         # modconf = os.path.join(extract_dir, fomodpath,
#         #                        "ModuleConfig.xml")
#
#         fdirpath = Path(extract_dir, fomodpath)
#         for fpath in fdirpath.iterdir():
#             if fpath.name.lower() == 'moduleconfig.xml':
#                 await installman.prepare_fomod(str(fpath), extract_dir)
#                 break
#
#         # if os.path.exists(modconf):
#         #     await installman.prepare_fomod(modconf, extract_dir)
#         # elif os.path.exists(modconf.lower()):
#         #     await installman.prepare_fomod(modconf.lower(), extract_dir)
#
#     return installman
#
# async def get_mod_archive_structure(archive=None):
#     """
#
#     :param archive:
#     :return: the internal folder structure of the mod `archive`
#         represented by a Tree structure
#     """
#     # global installman
#
#     if not archive and not installman:
#         raise TypeError(
#             "If no InstallManager is active, "
#             "the `archive` element cannot be None.")
#
#     if archive and (not installman or installman.archive != archive):
#         installman = _install.InstallManager(archive)
#
#     # modstruct = await installman.mod_structure_tree()
#     # return modstruct
#
#     modfs = await installman.mkarchivefs()
#     return modfs
#
# def install_mod_from_dir(directory):
#     print("installing mod from", directory)
#
#
# ##===============================================
# ## Installation Helpers
# ##-----------------------------------------------
# ## These are used to query dependencies for the
# ## fomod installer
# ##===============================================
#
# def checkFileState(file, state):
#     """
#     Query the database of known mod files for the given filename and
#     return whether it is in the given Activation State
#
#     M = "Missing"
#     I = "Inactive"
#     A = "Active"
#
#     :param file:
#     :param state:
#     :return: bool
#     """
#
#     matches = list(r['directory'] for r in _dataman.execute_(
#         "SELECT directory FROM modfiles WHERE filepath=?",
#         (file.lower(), )))
#
#     if matches:
#         if any(m=='Skyrim' or mod_is_enabled(m) for m in matches):
#             # at least one mod containing the matched file is enabled
#             # (or base skyrim), so return true iff desired state is 'active'
#             return state == FileState.A
#         # otherwise, every matched mod was disabled ,
#         # so return True iff desired state was 'inactive'
#         return state == FileState.I
#
#     # if no matches found, return true iff state being checked is 'missing'
#     return state == FileState.M
#
#
# def mod_is_enabled(mod_directory):
#     global __enabled_mods
#     try:
#         return mod_directory in __enabled_mods
#     except TypeError:
#         # __enabled_mods is uninitialized
#         __enabled_mods = list(enabled_mods())
#         return mod_directory in __enabled_mods


__manager = None

# singleton Manager
def Manager():
    global __manager
    if __manager is None:
        __manager = _ModManager()
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

        # the order here matters; profileManager requires config

        self._cman = _config.ConfigManager()

        self._pman = _profiles.ProfileManager(self._cman.paths.dir_profiles)

        # set up db, but do not load info until requested
        self._dman = _database.DBManager()
        self._db_initialized = False

        # install manager; instantiated when needed
        self._iman = None # type: _install.InstallManager

        # used when the installer needs to query mod state
        self._enabledmods = None

    @property
    def profile(self):
        """
        :return: the currently active profile, or None if one has not
            yet been set.
        """
        return self._pman.active_profile

    @property
    def Config(self):
        """Access the ConfigManager instance for the current session"""
        return self._cman

    @property
    def Profiler(self):
        """Access the Profile Manager for the current session"""
        return self._pman

    @property
    def DB(self):
        """Access the Database Manager for the current session"""
        return self._dman

    ##=============================================
    ## Profile Management Interface
    ##=============================================

    def activate_profile(self, profile):
        """
        Set the active profile to the profile given by `profile_name`
        :param profile:
        """
        # save this in case of a rollback

        # TODO: would it be possible...to make a context manager for profiles? I.e., the entire time a profile is active, we'd be within the "with" statement of a context manager? And when it closes we make sure to write all changed data? Or, it that's not feasible, maybe just the switch mechanics below could be wrapped in one for better error handling.

        old_profile = self.profile.name if self.profile else None

        try:
            # make sure we're dealing with just the name
            if isinstance(profile, _profiles.Profile):
                profile = profile.name
            assert isinstance(profile, str)

            self._set_profile(profile)
            # _profileman.set_active_profile(profile)
            #
            # _configman.last_profile = profile
            #
            # global _database_initialized
            #
            # # have to reinitialize the database
            # if _database_initialized:
            #     _dataman.reinit()
            # else:
            #     _database_initialized=True
            #     # well, it will be in just a second
            #
            # load_active_profile_data()

        except Exception as e:
            # if ANY errors occur, rollback the profile-switch
            self.LOGGER.error(e)
            self.LOGGER << "Error while activating profile. Rolling back."

            if old_profile:
                self._set_profile(old_profile)
            return False

        return True

    def _set_profile(self, profile_name):
        ## internal handler

        self._pman.set_active_profile(profile_name)

        self._cman.last_profile = profile_name

        # have to reinitialize the database
        if self._db_initialized:
            self._dman.reinit()
        else:
            self._db_initialized= True
            # well, it will be in just a second

        self._load_active_profile_data()

    def new_profile(self, name, copy_from=None):
        """
        Create and return a new Profile object with the specified name,
        optionally copying config files from the `copy_from` Profile

        :param str name:
        :param profiles.Profile copy_from:
        :return: new Profile object
        """
        return self._pman.new_profile(name, copy_from)

    def delete_profile(self, profile):
        self._pman.delete_profile(profile)

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
            profile = self._pman[profile]

        self.LOGGER << "Renaming profile: {}->{}".format(profile.name,
                                                     new_name)
        self._pman.rename_profile(profile, new_name)

        if profile is self.profile:
            self._cman.update_config(KeyStr.INI.LASTPROFILE,
                                     KeyStr.Section.GENERAL,
                                     profile.name)

    def get_profiles(self, names_only=True):
        """
        Generator that iterates over all existing profiles.

        :param names_only: if True, only yield the profile names. If false,
            yield tuples of (name, Profile) pairs"""
        if names_only:
            yield from (n for n in self._pman.profile_names)
        else:
            yield from self._pman.profiles_by_name()

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
        self.LOGGER << "loading data for active profile: " + self.profile.name
        # try to read modinfo file
        if self._dman.load_mod_info(self.profile.modinfo):
            self.LOGGER << "validating installed mods"
            # if successful, validate modinfo
            self.validate_mod_installs()

        else:
            self.LOGGER << "Could not load mod info, reading " \
                       "from configured mods directory: " \
                       + self._cman['dir_mods']
            # if it fails, re-read mod data from disk
            self._dman.get_mod_data_from_directory(
                self._cman.paths.dir_mods)
            # and [re]create the cache file
            self.save_mod_list()

        # FIXME: avoid doing this on profile change
        # _logger << "Loading list of all Mod Files on disk"

        self._dman.load_all_mod_files(self._cman.paths.dir_mods)
        # let's also add the files from the base Skyrim Data folder to the db

        sky_dir = self._cman.paths.dir_skyrim

        if sky_dir is None:
            self.LOGGER << "The main Skyrim folder could not be found. " \
                       "That's going to be a problem."
        else:
            for f in sky_dir.iterdir():
                if f.name.lower() == "data":
                    self._dman.add_files_from_dir('Skyrim', str(f))
                    break

        # [print(*r) for r in _dataman._con.execute("select *
        # from modfiles where directory='Skyrim'")]



        # _logger << "Finished loading list of all Mod Files on disk"
        self.LOGGER.info("Detecting file conflicts")

        self._dman.detect_file_conflicts()

        self.LOGGER.info("Analyzing hidden files")
        self._dman.load_hidden_files(self.profile.hidden_files)

    def hidden_files(self, for_mod=None):
        """

        :param str for_mod: If specified, must be the directory name of an
            installed mod; will yield only the files marked as hidden for
            that particular mod.
        :return: a generator over the Rows (basically a dict with keys
            'directory' and 'filepath') of hiddenfiles; if 'for_mod' was
            given, will instead return a generator over just the hidden
            filepaths (generator of strings)
        """
        if for_mod is None:
            yield from self._dman.execute_("Select * from hiddenfiles")
        else:
            yield from (t[0] for t in self._dman.execute_(
                "Select filepath from hiddenfiles where directory=?",
                (for_mod,)))

    ##=============================================
    ## Mod Information
    ##=============================================

    def get_mod_errors(self):
        """

        :rtype: dict[str, int]
        :return: a dictionary of mod-directory:error-type for every mod in
            the database
        """

        return {r['directory']: r['error'] for r in
                self._dman.execute_("SELECT directory, error FROM mods")}

    def allmodinfo(self):
        """
        Obtain an iterator over all the rows in the database which yields
        _all_ the info for a mod as a dict, intended for feeding to
        ModEntry(**d) or using directly.

        :rtype: __generator[dict[str, sqlite3.Row], Any, None]
        """
        for row in self._dman.get_mod_info():
            yield dict(zip(row.keys(), row))

    def enabled_mods(self):
        """
        yields the names of enabled mods for the currently active profile
        """
        yield from self._dman.enabled_mods(True)

    def disabled_mods(self):
        yield from self._dman.disabled_mods(True)

    def validate_mod_installs(self):
        """
        Queries the disk and the database to see if the respective
        lists of mods are in sync. If not, any issues encountered
        are recorded on the active profile object.

        :return: True if no errors encountered, False otherwise
        """
        return self._dman.validate_mods_list(self._cman.list_mod_folders())


    ##=============================================
    ## Data Persistence
    ##=============================================

    def save_user_edits(self, changes):
        """
        :param collections.abc.Iterable[ModEntry] changes: an iterable of ModEntry objects
        """

        rows_to_delete = [(m.ordinal,) for m in changes]

        # a generator that creates tuples of values by sorting the values of the
        # modentry according the order defined in constants._db_fields
        dbrowgen = (
            tuple([getattr(mod, field)
                   for field in sorted(mod._fields,
                                       key=lambda f: _db_fields.index(
                                           f))
                   ])
            for mod in changes)

        # using the context manager may allow deferrable foreign
        # to go unsatisfied for a moment

        con = self._dman.conn
        with con:
            # db.conn.set_trace_callback(print)

            # delete the row with the given ordinal
            con.executemany("DELETE FROM mods WHERE ordinal=?",
                                rows_to_delete)

            # and reinsert
            query = "INSERT INTO mods(" + ", ".join(
                _db_fields) + ") VALUES ("
            query += ", ".join("?" * len(_db_fields)) + ")"

            con.executemany(query, dbrowgen)
            # db.conn.set_trace_callback(None)

        # And finally save changes to disk
        self.save_mod_list()

    def save_mod_list(self):
        """Request that database manager save modinfo to disk"""
        self._dman.save_mod_info(self.profile.modinfo)
        # reset so that next install will reflect the new state
        self._enabledmods = None

    def save_hidden_files(self):
        self._dman.save_hidden_files(self.profile.hidden_files)

    ##=============================================
    ## Configuration Management Interface
    ##=============================================

    def get_config_value(self, name, section=KeyStr.Section.NONE,
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
        ap = self.profile

        # IF there is an active profile, AND we happen to be asking for a
        # directory, AND use_profile_override is True, AND the active
        # profile actually contains an override for this directory: return
        # that override
        if ap and section == KeyStr.Section.DIRECTORIES \
                and use_profile_override \
                and ap.Config[KeyStr.Section.OVERRIDES][name]:
            val = ap.Config[KeyStr.Section.OVERRIDES][name]
        else:
            # in all other situations, just return the stored config value
            val = self._cman[name]

        # if the value stored in config was None (or some other False-like
        # value), return the `default` parameter instead
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
        if section == KeyStr.Section.DIRECTORIES:
            # if a profile is active, set an override
            self._change_configured_path(name, value,
                                    set_profile_override and
                                    self.profile is not None)

        elif section == KeyStr.Section.GENERAL:
            self._cman.update_config(name, section, value)


    def _change_configured_path(self, directory, new_path, profile_override):
        if profile_override:
            self.set_profile_setting(directory, KeyStr.Section.OVERRIDES,
                                new_path)
        else:
            self._cman.update_config(directory, KeyStr.Section.DIRECTORIES,
                               new_path)


    def set_directory(self, key, path, profile_override=True):
        """
        Update the configured value of the directory indicated by `key`
        (from constants.KeyStr.Dirs) to the new value given in `path`

        :param key:
        :param str path:
        :param profile_override:
        """
        self.set_config_value(key, KeyStr.Section.DIRECTORIES, path,
                         profile_override)


    def get_directory(self, key, use_profile_override=True):
        """
        Get the stored path for the app directory referenced by `key`.
        If use_profile_override is True and an override is set in the
        currently active profile for this directory, that override will be
        returned. In all other cases, the value from the default config
        will be returned.

        :param key: constants.KeyStr.Dirs.WHATEVER
        :param use_profile_override: Return the path-override from the
            currently active profile, if one is set.
        :return:
        """
        return self.get_config_value(key,
                                KeyStr.Section.DIRECTORIES,
                                use_profile_override=use_profile_override)

    ##=============================================
    ## Installation
    ## --------------------------------------------
    ## Methods below are asynchronous
    ##=============================================

    async def get_installer(self, archive, extract_dir):
        """
        Generate and return an InstallManager instance for the given
        mod archive.

        :param archive:
        :param extract_dir:
        :return:
        """

        # instantiate a new install manager
        self._iman = _install.InstallManager(archive)

        fomodpath = await self._iman.get_fomod_path()

        self.LOGGER << "fomodpath: {}".format(fomodpath)

        if fomodpath is not None:

            await self._iman.extract(extract_dir, [fomodpath])
            # modconf = os.path.join(extract_dir, fomodpath,
            #                        "ModuleConfig.xml")

            fdirpath = Path(extract_dir, fomodpath)
            for fpath in fdirpath.iterdir():
                if fpath.name.lower() == 'moduleconfig.xml':
                    await self._iman.prepare_fomod(str(fpath),
                                                   extract_dir)
                    break

                    # if os.path.exists(modconf):
                    #     await installman.prepare_fomod(modconf, extract_dir)
                    # elif os.path.exists(modconf.lower()):
                    #     await installman.prepare_fomod(modconf.lower(), extract_dir)

        return self._iman

    async def get_mod_archive_structure(self, archive=None):
        """

        :param archive:
        :rtype: skymodman.utils.archivefs.ArchiveFS
        :return: the internal folder structure of the mod `archive`
            represented by a Tree structure
        """
        if not archive and not self._iman:
            raise TypeError(
                "If no InstallManager is active, "
                "an archive file must be provided.")

        if archive and (
            not self._iman or self._iman.archive != archive):
            self._iman = _install.InstallManager(archive)

        # modstruct = await installman.mod_structure_tree()
        # return modstruct

        modfs = await self._iman.mkarchivefs()
        return modfs

    ##=================================
    ## install helpers
    ##---------------------------------

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

        matches = list(r['directory'] for r in self._dman.execute_(
            "SELECT directory FROM modfiles WHERE filepath=?",
            (file.lower(),)))

        if matches:
            if any(m == 'Skyrim' or self.mod_is_enabled(m) for m in matches):
                # at least one mod containing the matched file is enabled
                # (or base skyrim), so return true iff desired state is 'active'
                return state == FileState.A
            # otherwise, every matched mod was disabled ,
            # so return True iff desired state was 'inactive'
            return state == FileState.I

        # if no matches found, return true iff state being checked is 'missing'
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

