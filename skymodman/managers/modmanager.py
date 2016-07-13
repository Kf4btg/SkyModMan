# import os
from pathlib import Path

from skymodman import ModEntry, skylog
from skymodman.managers import (config as _config,
                                database as _database,
                                installer as _install)
from skymodman.managers.profiles import Profile, ProfileManager
from skymodman.constants import (KeyStr, db_fields as _db_fields)


_configman  = None # type: _config.ConfigManager
_dataman    = None # type: _database.DBManager
_profileman = None # type: ProfileManager
# _installman = None

#shortcuts
conf     = _configman   # type: _config.ConfigManager
db       = _dataman     # type: _database.DBManager
profiles = _profileman  # type: ProfileManager

file_conflicts = None               # type collections.defaultdict[list]
mods_with_conflicting_files = None  # type collections.defaultdict[list]

_logger = None
__enabled_mods = None

_database_initialized=False

def init():
    global _logger, _dataman, _profileman, _configman #_installman,
    global conf, profiles, db

    _logger = skylog.newLogger(__name__)

    _configman = conf = _config.ConfigManager()

    # must be created after config manager
    _profileman = profiles = ProfileManager(
        _configman.paths.dir_profiles)
    # set the most-recently loaded profile as active.
    # _profileman.setActiveProfile(_configman.lastprofile)

    # Prepare the database, but do not load any information
    # until it is requested.
    _dataman = db = _database.DBManager()


def get_cursor():
    """
    Using this, a component can request a cursor object for
    interacting with the database
    :return: sqlite3.Cursor
    """
    return _dataman.conn.cursor()

##=============================================
## Profile Management
##=============================================

#<editor-fold desc="profiles">

def active_profile() -> Profile:
    """
    Retrieves the presently loaded Profile from the Profile Manager.
    :return: The active Profile object
    """
    return _profileman.active_profile

def set_active_profile(profile):
    """
    To be called by external interfaces.
    Set `profile` as currently loaded. Updates saved config file to mark
    this profile as the last-loaded profile, and loads the data for the
    newly-activated profile

    :param profile:
    """
    # make sure we're dealing with just the name
    if isinstance(profile, Profile):
        profile = profile.name
    assert isinstance(profile, str)
    _profileman.setActiveProfile(profile)

    _configman.lastprofile = profile

    global _database_initialized

    # have to reinitialize the database
    if _database_initialized:
        _dataman.reinit()
    else:
        _database_initialized=True
        # well, it will be in just a second

    load_active_profile_data()

def get_profiles(names_only = True):
    """
    Generator that iterates over all existing profiles.

    :param names_only: if True, only yield the profile names. If false,
        yield tuples of (name, Profile) pairs"""
    if names_only:
        yield from (n for n in _profileman.profile_names)
    else:
        yield from _profileman.profilesByName()

def new_profile(name, copy_from = None):
    """
    Create and return a new Profile object with the specified name,
    optionally copying config files from the `copy_from` Profile

    :param str name:
    :param profiles.Profile copy_from:
    :return: new Profile object
    """
    return _profileman.newProfile(name, copy_from)

def rename_profile(new_name, current=None):
    """
    Change the name of profile `current` to `new_name`. If `current` is
    passed as None, rename the active profile. This renames the
    profile's directory on disk.

    :param new_name:
    :param current:
    """
    # get the current Profile object
    if current is None:
        current = active_profile()
    elif isinstance(current, str):
        current = _profileman[current]

    _logger << "Renaming profile: {}->{}".format(current.name, new_name)
    _profileman.rename_profile(current, new_name)

    if current is active_profile():
        _configman.updateConfig(KeyStr.INI.LASTPROFILE,
                                KeyStr.Section.GENERAL, current.name)


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
        _logger << "Could not load mod info, reading " \
                   "from configured mods directory: " \
                   + _configman['dir_mods']
        # if it fails, re-read mod data from disk
        _dataman.getModDataFromModDirectory(_configman.paths.dir_mods)
        # and [re]create the cache file
        save_mod_list()

    # FIXME: avoid doing this on profile change
    # _logger << "Loading list of all Mod Files on disk"
    _logger.info("Detecting file conflicts")

    _dataman.loadAllModFiles(_configman.paths.dir_mods)
    # let's also add the files from the base Skyrim Data folder to the db

    sky_dir = _configman.paths.dir_skyrim

    if sky_dir is None:
        _logger << "The main Skyrim folder could not be found. " \
                   "That's going to be a problem."
    else:
        for f in sky_dir.iterdir():
            if f.name.lower() == "data":
                _dataman.add_files_from_dir('Skyrim', str(f))
                break

    # [print(*r) for r in _dataman._con.execute("select *
    # from modfiles where directory='Skyrim'")]



    # _logger << "Finished loading list of all Mod Files on disk"

    _dataman.detectFileConflicts()

    _logger.info("Analyzing hidden files")
    _dataman.loadHiddenFiles(active_profile().hidden_files)

def hidden_files(for_mod=None):
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
        yield from _dataman.execute_("Select * from hiddenfiles")
    else:
        yield from (t[0] for t in _dataman.execute_(
            "Select filepath from hiddenfiles where directory=?",
            (for_mod, )))

# def get_errors(error_type):
#     """
#     Yields any recorded errors of the specified type from the active
#     profile. 'Not Found' means that a mod was in the profile's list of
#     installed mods, but could not be found on disk. 'Not Listed' means
#     that a mod was found on disk that was not previously in the list of
#     installed mods.
#
#     :param error_type: constants.SyncError
#     :yieldtype: str
#     :yield: names of mods that encountered the specified error_type
#         during load
#     """
#
#     q = """SELECT mod, ordinal from (
#         SELECT moderrors.mod as mod,
#             moderrors.errortype as etype,
#             mods.ordinal as ordinal
#         FROM moderrors INNER JOIN mods
#         ON mod = mods.directory
#         WHERE etype = ?)
#         ORDER BY ordinal
#     """
#
#     yield from (r['mod'] for r in
#                 _dataman.execute_(q, (error_type.value,)))

def get_errors():
    """

    :rtype: dict[str, int]
    :return: a dictionary of mod-directory:error-type for every mod in
        the database
    """

    return {r['directory']:r['error'] for r in
                _dataman.execute_("SELECT directory, error FROM mods")}

#</editor-fold>

##=============================================
## Mod Information
##=============================================

#<editor-fold desc="modinfo">

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
    Obtain an iterator over all the rows in the database which yields
    _all_ the info for a mod as a dict, intended for feeding to
    ModEntry(**d) or using directly.

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

#</editor-fold>

##=============================================
## Saving changes
##=============================================

#<editor-fold desc="saving">

def save_user_edits(changes):
    """
    :param collections.abc.Iterable[ModEntry] changes: an iterable of ModEntry objects
    """

    rows_to_delete = [(m.ordinal, ) for m in changes]

    # a generator that creates tuples of values by sorting the values of the
    # modentry according the order defined in constants._db_fields
    dbrowgen = (tuple([getattr(m, f)
                       for f in sorted(m._fields,
                                       key=lambda fld: _db_fields.index(fld)
                                       ) ] )
                for m in changes)

    # using the context manager may allow deferrable foreign
    # to go unsatisfied for a moment

    with db.conn:
        # delete the row with the given ordinal
        db.conn.executemany("DELETE FROM mods WHERE ordinal=?", rows_to_delete)

        # and reinsert
        query = "INSERT INTO mods(" + ", ".join(_db_fields) + ") VALUES ("
        query += ", ".join("?" * len(_db_fields)) + ")"

        db.conn.executemany(query, dbrowgen)

    # And finally save changes to disk
    save_mod_list()

def save_mod_list():
    """Request that database manager save modinfo to disk"""
    _dataman.saveModDB(active_profile().modinfo)
    global __enabled_mods
    # reset so that next install will reflect the new state
    __enabled_mods = None

def save_hidden_files():
    _dataman.saveHiddenFiles(active_profile().hidden_files)


#</editor-fold>

##=============================================
## Configuration querying, updating
##=============================================

#<editor-fold desc="config">

def get_config_value(name, section=KeyStr.Section.NONE,
                     default=None, use_profile_override = True):
    """
    Get the current value of one of the main config values

    :param name: the key for which to retrieve the value
    :param section: "General" or "Directories" or "" (enum values
        are preferred)
    :param default: value to return if the section/key is not found
    :param use_profile_override:

    :return:
    """
    ap = active_profile()

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
        val = conf[name]

    # if the value stored in config was None (or some other False-like
    # value), return the `default` parameter instead
    return val if val else default

        # assume section is "NONE", meaning this is not a value
        # from the main config file (but is still tracked by
        # config manager...TODO: there's probably a better way to do this)
        # val = conf[name]


def set_config_value(name, section, value, set_profile_override=True):
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
        _change_configured_path(name, value,
                                set_profile_override and
                                active_profile() is not None)

    elif section == KeyStr.Section.GENERAL:
        conf.updateConfig(name, section, value)


def _change_configured_path(directory, new_path, profile_override):

    if profile_override:
        set_profile_setting(directory, KeyStr.Section.OVERRIDES, new_path)
    else:
        conf.updateConfig(directory, KeyStr.Section.DIRECTORIES, new_path)


def set_directory(key, path, profile_override=True):
    """
    Update the configured value of the directory indicated by `key`
    (from constants.KeyStr.Dirs) to the new value given in `path`

    :param key:
    :param str path:
    :param profile_override:
    """
    set_config_value(key, KeyStr.Section.DIRECTORIES, path,
                     profile_override)

def get_directory(key, use_profile_override=True):
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
    return get_config_value(key,
                            KeyStr.Section.DIRECTORIES,
                            use_profile_override=use_profile_override)

def get_profile_setting(name, section, default=None):
    """

    :param str section: Config file section the setting belongs to
    :param str name: Name of the setting
    :param default: value to return when there is no active profile
    :return: current value of the setting
    """
    ap = active_profile()
    if ap is not None:
        return ap.Config[section][name]
    return default

def set_profile_setting(name, section, value):
    """
    :param str section: Config file section the setting belongs to
    :param str name: Name of the setting
    :param value: the new value of the setting
    """
    active_profile().save_setting(section, name, value)

#</editor-fold>

##===============================================
## Mod [Un]Installation
##===============================================


installman=None # type: _install.InstallManager
async def get_installer(archive, extract_dir):
    global installman
    installman = _install.InstallManager(archive)

    fomodpath = await installman.get_fomod_path()

    _logger << "fomodpath: {}".format(fomodpath)

    if fomodpath is not None:

        await installman.extract(extract_dir, [fomodpath])
        # modconf = os.path.join(extract_dir, fomodpath,
        #                        "ModuleConfig.xml")

        fdirpath = Path(extract_dir, fomodpath)
        for fpath in fdirpath.iterdir():
            if fpath.name.lower() == 'moduleconfig.xml':
                await installman.prepare_fomod(str(fpath), extract_dir)
                break

        # if os.path.exists(modconf):
        #     await installman.prepare_fomod(modconf, extract_dir)
        # elif os.path.exists(modconf.lower()):
        #     await installman.prepare_fomod(modconf.lower(), extract_dir)

    return installman

async def get_mod_archive_structure(archive=None):
    """

    :param archive:
    :return: the internal folder structure of the mod `archive`
        represented by a Tree structure
    """
    global installman

    if not archive and not installman:
        raise TypeError(
            "If no InstallManager is active, "
            "the `archive` element cannot be None.")

    if archive and (not installman or installman.archive != archive):
        installman = _install.InstallManager(archive)

    # modstruct = await installman.mod_structure_tree()
    # return modstruct

    modfs = await installman.mkarchivefs()
    return modfs

def install_mod_from_dir(directory):
    print("installing mod from", directory)


##===============================================
## Installation Helpers
##-----------------------------------------------
## These are used to query dependencies for the
## fomod installer
from skymodman.installer.common import FileState
##===============================================

def checkFileState(file, state):
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

    matches = list(r['directory'] for r in _dataman.execute_(
        "SELECT directory FROM modfiles WHERE filepath=?",
        (file.lower(), )))

    if matches:
        if any(m=='Skyrim' or mod_is_enabled(m) for m in matches):
            # at least one mod containing the matched file is enabled
            # (or base skyrim), so return true iff desired state is 'active'
            return state == FileState.A
        # otherwise, every matched mod was disabled ,
        # so return True iff desired state was 'inactive'
        return state == FileState.I

    # if no matches found, return true iff state being checked is 'missing'
    return state == FileState.M


def mod_is_enabled(mod_directory):
    global __enabled_mods
    try:
        return mod_directory in __enabled_mods
    except TypeError:
        # __enabled_mods is uninitialized
        __enabled_mods = list(enabled_mods())
        return mod_directory in __enabled_mods
