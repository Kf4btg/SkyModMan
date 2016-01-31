from skymodman import ModEntry, skylog #exceptions,
# from skymodman.utils import classprop
from skymodman.managers import config as _config, database as _database
from skymodman.managers.profiles import Profile, ProfileManager
from skymodman.constants import db_fields #SyncError,


# from skymodman.utils import humanizer
# @humanizer.humanize
# noinspection PyMethodParameters
# @with_logger
# class ModManager:
#     """
#     Manages all the backend interaction; this includes access to the Configuration,
#     profile manager, database manager, etc. This is a singleton class: only one
#     instance will be created during any run of the application.
#     """
    #
    # _instance = None
    # def __new__(*args, **kwargs):
    #     """Override __new__ to allow only one instance of this class to exist, even
    #     if it is called multiple times.  Makes this class a singleton"""
    #     if _instance is not None:
    #         return _instance
    #     self = object.__new__(*args)
    #     _instance = self
    #     return self


    # def __init__(self):
    #     self._config_manager = config.ConfigManager(self)
    #
    #     # must be created after config manager
    #     self._profile_manager = profiles.ProfileManager(self, self._config_manager.paths.dir_profiles)
    #     # set the most-recently loaded profile as active.
    #     self._profile_manager.setActiveProfile(self._config_manager.lastprofile)
    #
    #     # Prepare the database, but do not load any information
    #     # until it is requested.
    #     self._db_manager = database.DBManager(self)
    #
    #     self._conflicting_files = None
    #     """:type: collections.defaultdict[list]"""
    #     self._mods_with_conflicts = None
    #     """:type: collections.defaultdict[list]"""

_configman = None
_dataman = None
_profileman = None
_installman = None

#shortcuts
conf = _configman
db = _dataman
profiles=_profileman

file_conflicts = None
mods_with_conflicting_files = None

_logger = None

def init():
    global _logger, _dataman, _profileman, _installman, _configman
    global conf, profiles, db
    _logger = skylog.newLogger(__name__)
    _configman = conf = _config.ConfigManager()

    # must be created after config manager
    _profileman = profiles = ProfileManager(_configman.paths.dir_profiles)
    # set the most-recently loaded profile as active.
    _profileman.setActiveProfile(_configman.lastprofile)

    # Prepare the database, but do not load any information
    # until it is requested.
    _dataman = db = _database.DBManager()



# @property
# def file_conflicts(self):
#     return self._conflicting_files
#
# @file_conflicts.setter
# def file_conflicts(self, ddictlist):
#     """
#
#     :param collections.defaultdict[list] ddictlist:
#     """
#     self._conflicting_files = ddictlist

# @property
# def mods_with_conflicting_files(self):
#     return self._mods_with_conflicts
#
# @mods_with_conflicting_files.setter
# def mods_with_conflicting_files(self, ddictlist):
#     """
#
#     :param collections.defaultdict[list] ddictlist:
#     """
#     self._mods_with_conflicts = ddictlist

def get_cursor():
    """
    Using this, a component can request a cursor object for interacting with the database
    :return: sqlite3.Cursor
    """
    return _dataman.conn.cursor()

def active_profile() -> Profile:
    """
    Retrieves the presently loaded Profile from the
    Profile Manager.
    :return: The active Profile object
    """
    return _profileman.active_profile

def set_active_profile(profile):
    """
    To be called by external interfaces.
    Set `profile` as currently loaded. Updates saved config file to mark this profile as the last-loaded profile, and loads the data for the newly-activated profile

    :param profile:
    """
    # make sure we're dealing with just the name
    if isinstance(profile, Profile):
        profile = profile.name
    assert isinstance(profile, str)
    _profileman.setActiveProfile(profile)
    _configman.updateConfig(profile, "lastprofile")

    # have to reinitialize the database
    _dataman.reinit()
    load_active_profile_data()

def get_profiles(names_only = True):
    """
    Generator that iterates over all existing profiles.

    :param names_only: if True, only yield the profile names. If false, yield tuples of (name, Profile) pairs"""
    if names_only:
        yield from (n for n in _profileman.profile_names)
    else:
        yield from _profileman.profilesByName()

def new_profile(name, copy_from = None):
    """
    Create and return a new Profile object with the specified name, optionally
    copying config files from the `copy_from` Profile
    :param str name:
    :param profiles.Profile copy_from:
    :return:
    """
    return _profileman.newProfile(name, copy_from)

def delete_profile(profile):
    _profileman.deleteProfile(profile, True)

def load_active_profile_data():
    """
    Asks the Database Manager to load the information stored
    on disk for the given profile into an in-memory database
    that will be used to provide data to the rest of the app.
    """
    _logger << "loading data for active profile: " + active_profile().name
    # try to read modinfo file
    if _dataman.loadModDB(active_profile().modinfo):
        _logger << "validating installed mods"
        # if successful, validate modinfo
        validate_mod_installs()

    else:
        _logger << "Could not load mod info, reading from configured mods directory: " + _configman['dir_mods']
        # if it fails, re-read mod data from disk
        _dataman.getModDataFromModDirectory(_configman.paths.dir_mods)
        # and [re]create the cache file
        save_mod_list()

    # FIXME: avoid doing this on profile change
    # _logger << "Loading list of all Mod Files on disk"
    _logger.info("Detecting file conflicts")
    _dataman.loadAllModFiles(_configman.paths.dir_mods)
    # _logger << "Finished loading list of all Mod Files on disk"

    _dataman.detectFileConflicts()

    _logger.info("Analyzing hidden files")
    _dataman.loadHiddenFiles(active_profile().hidden_files)

def validate_mod_installs():
    """
    Queries the disk and the database to see if the respective
    lists of mods are in sync. If not, any issues encountered
    are recorded on the active profile object.

    :return: True if no errors encountered, False otherwise
    """
    return _dataman.validateModsList(_configman.listModFolders())

def basic_mod_info():
    """
    Obtain an iterator over all the rows in the database which yields _all_ the info for a mod as a dict, intended for feeding to ModEntry(**d) or using directly.

    :rtype: __generator[dict[str, sqlite3.Row], Any, None]
    """
    #TODO: rename this.
    for row in _dataman.getModInfo():
        yield dict(zip(row.keys(), row))

def enabled_mods():
    """
    yields the names of enabled mods for the currently active profile
    """
    yield from _dataman.enabledMods(True)

def disabled_mods():
    yield from _dataman.disabledMods(True)

def save_user_edits(changes):
    """
    :param collections.abc.Iterable[ModEntry] changes: an iterable of ModEntry objects
    """

    rows_to_delete = [(m.ordinal, ) for m in changes]

    # a generator that creates tuples of values by sorting the values of the
    # modentry according the order defined in constants.db_fields
    dbrowgen = (tuple([getattr(m, f) for f in sorted(m._fields, key=lambda fld: db_fields.index(fld)) ] ) for m in changes)

    # using the context manager may allow deferrable foreign
    # to go unsatisfied for a moment

    with db.conn:
        # delete the row with the given ordinal
        db.conn.executemany("DELETE FROM mods WHERE ordinal=?", rows_to_delete)

        # and reinsert
        query = "INSERT INTO mods(" + ", ".join(db_fields) + ") VALUES ("
        query += ", ".join("?" * len(db_fields)) + ")"

        db.conn.executemany(query, dbrowgen)

    # And finally save changes to disk
    save_mod_list()

def save_mod_list():
    """Request that database manager save modinfo to disk"""
    _dataman.saveModDB(active_profile().modinfo)

def get_profile_setting(section, name):
    """

    :param str section: Config file section the setting belongs to
    :param str name: Name of the setting
    :return: current value of the setting
    """
    return active_profile().settings[section][name]

def set_profile_setting(section, name, value):
    """
    :param str section: Config file section the setting belongs to
    :param str name: Name of the setting
    :param value: the new value of the setting
    """
    active_profile().save_setting(section, name, value)

def save_hidden_files():
    _dataman.saveHiddenFiles(active_profile().hidden_files)

def hidden_files(for_mod=None):
    """

    :param str for_mod:
        If specified, must be the directory name of an installed mod; will yield only the files marked as hidden for that particular mod
    :return: a generator over the Rows (basically a dict with keys 'directory' and 'filepath') of hiddenfiles; if 'for_mod' was given, will instead return a generator over just the hidden filepaths (generator of strings)
    """
    if for_mod is None:
        yield from _dataman.execute_("Select * from hiddenfiles")
    else:
        yield from (t[0] for t in _dataman.execute_("Select filepath from hiddenfiles where directory=?", (for_mod, )))

def get_errors(error_type):
    """
    Returns any recorded errors of the specified type from the active profile.
    'Not Found' means that a mod was in the profile's list of installed mods, but could not be found on disk.
    'Not Listed' means that a mod was found on disk that was not previously in the list of installed mods.

    :param error_type: constants.SyncError
    """


    q="""SELECT mod, ordinal from (
        SELECT moderrors.mod as mod, moderrors.errortype as etype, mods.ordinal as ordinal
        FROM moderrors INNER JOIN mods
        ON mod = mods.directory
        WHERE etype = ?)
        ORDER BY ordinal
    """

    yield from (r['mod'] for r in _dataman.execute_(q, (error_type.value, )))
