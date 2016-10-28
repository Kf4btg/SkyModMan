# from .enums import Tab, Column, qModels, qFilters, ModError, EnvVars, KeyStr, OverwriteMode, ProfileLoadPolicy
from .enums import *
from . import keystrings as _keystr

from collections import namedtuple as _namedtuple


# what to show in the title-bar of the main window and some dialog
APPTITLE = "SkyModMan"

## configuration-related strings
APPNAME = "skymodman" # mainly for use w/ appdirs
MAIN_CONFIG = "{}.ini".format(APPNAME)
PROFILES_DIRNAME = "profiles"

# this profile must exist. If it doesn't, we must create it.
FALLBACK_PROFILE = "default"

# For things that are going to presented to the user as
# customizable preferences, we also need a user-friendly
# display name to plug into labels and messages
DisplayNames = {
    _keystr.INI.ACTIVE_ONLY:     "Only Show Active Mods",
    _keystr.INI.DEFAULT_PROFILE: "Default Profile",
    _keystr.INI.LAST_PROFILE: "Last Loaded Profile",

    _keystr.Dirs.PROFILES: "Profiles Directory",
    _keystr.Dirs.SKYRIM: "Skyrim Installation",
    _keystr.Dirs.MODS: "Mods Directory",
    _keystr.Dirs.VFS: "Virtual FS Mount Point",

    _keystr.UI.RESTORE_WINSIZE: "Restore Window Size",
    _keystr.UI.RESTORE_WINPOS: "Restore Window Position",
}

overrideable_dirs = (_keystr.Dirs.SKYRIM, _keystr.Dirs.MODS, _keystr.Dirs.VFS)

## definitions of database fields and order, including a version w/o
## the "Error" field
_dbflds_noerr = _namedtuple("_dbflds_noerr", "FLD_ORD FLD_DIR FLD_NAME FLD_MODID FLD_VER FLD_ENAB FLD_MNGD")

_dbflds = _namedtuple("_dbflds", _dbflds_noerr._fields + ("FLD_ERR",))


## Definitions for actual string values of database field names
db_fields_noerror = _dbflds_noerr("ordinal", "directory", "name", "modid", "version", "enabled", "managed")
db_fields = _dbflds(*(db_fields_noerror + ("error",)))

## And a reverse-lookup to find the correct in-order index of a given field
db_field_order = {fld:db_fields.index(fld) for fld in db_fields}

# db_fields = _dbflds("ordinal", "directory", "name", "modid", "version", "enabled", "error")

# a tuple of the db fields without the ordinal or error field;
# simply for convenience. As it is constructed from a set, it
# Should only be used where the order of the fields doesn't matter
# noordinal_dbfields = tuple(set(db_fields) ^ {"ordinal", "error"})

class SkyrimGameInfo:
    """Contains information specific to Skyrim (filenames, ids, etc)
    that we may need to know"""

    steam_appid = 72850
    nexus_id = 110

    exe_name = "TESV.exe"
    game_name = "Skyrim"

    all_dlc = ("Dawnguard", "HearthFires", "Dragonborn",
                "HighResTexturePack01",
                "HighResTexturePack02",
                "HighResTexturePack03")

    # possible locations of "local appdata" folder within windows
    # user folder
    local_appdata = ("AppData/Local", "Local Settings")
    # files created by TESV.exe within local appdata
    appdata_files = ("Skyrim/plugins.txt", "Skyrim/loadorder.txt")

    ini_files = ("skyrim.ini", "skyrimprefs.ini")

    masters = ("skyrim.esm", "update.esm")

    dlc_masters = ("Dawnguard.esm", "HearthFires.esm", "Dragonborn.esm")

    HR_texpacks = ("HighResTexturePack01.esp",
                   "HighResTexturePack02.esp",
                   "HighResTexturePack03.esp")

    skyrim_archives = ("Skyrim - Misc.bsa",
                        "Skyrim - Shaders.bsa",
                        "Skyrim - Textures.bsa",
                        "Skyrim - Interface.bsa",
                        "Skyrim - Animations.bsa",
                        "Skyrim - Meshes.bsa",
                        "Skyrim - Sounds.bsa",
                        "Skyrim - Voices.bsa",
                        "Skyrim - VoicesExtra.bsa",
                        "update.bsa")

    dlc_archives = ("Dawnguard.bsa", "HearthFires.bsa", "Dragonborn.bsa")

    HR_texarchives = ("HighResTexturePack01.bsa",
                        "HighResTexturePack02.bsa",
                        "HighResTexturePack03.bsa")

    vanilla_archives = skyrim_archives + dlc_archives + HR_texarchives

    ## After about two months of working on this, this was my first time
    # diving into the ModOrganizer code to search for the answer to a
    # question I couldn't otherwise figure out. Specifically:
    # "What constitutes 'proper' mod structure?" As I expected, the
    # answer was pretty specific.

    TopLevelDirs = {"distantlod", "facegen", "fonts", "interface",
                    "menus", "meshes", "music", "scripts", "shaders",
                    "sound", "strings", "textures", "trees", "video",
                    "skse", "obse", "nvse", "fose", "asi", "skyproc patchers"
                    }

    TopLevelDirs_Bain = TopLevelDirs | {"docs", "ini tweaks"}

    TopLevelSuffixes = {"esp", "esm", "bsa"}

