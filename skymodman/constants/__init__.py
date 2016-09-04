# from .enums import Tab, Column, qModels, qFilters, ModError, EnvVars, KeyStr, OverwriteMode, ProfileLoadPolicy
from .enums import *
from . import keystrings as _keystr


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
    _keystr.INI.ACTIVEONLY: "Only Show Active Mods",
    _keystr.INI.DEFAULT_PROFILE: "Default Profile",
    _keystr.INI.LASTPROFILE: "Last Loaded Profile",

    _keystr.Dirs.PROFILES: "Profiles Directory",
    _keystr.Dirs.SKYRIM: "Skyrim Installation",
    _keystr.Dirs.MODS: "Mods Directory",
    _keystr.Dirs.VFS: "Virtual FS Mount Point",

    _keystr.UI.RESTORE_WINSIZE: "Restore Window Size",
    _keystr.UI.RESTORE_WINPOS: "Restore Window Position",
}

# defines the names and order of fields in the database
db_fields = ("ordinal", "directory", "name", "modid", "version", "enabled", "error")

# a tuple of the db fields without the ordinal or error field;
# simply for convenience. As it is constructed from a set, it
# Should only be used where the order of the fields doesn't matter
noordinal_dbfields = tuple(set(db_fields) ^ {"ordinal", "error"})

class SkyrimGameInfo:
    """Contains information specific to Skyrim (filenames, ids, etc)
    that we may need to know"""

    steam_appid = 72850
    nexus_id = 110

    exe_name = "TESV.exe"
    game_name = "Skyrim"

    ini_files = ("skyrim.ini", "skyrimprefs.ini")

    masters = ("skyrim.esm", "update.esm")
    dlc_masters = ("Dawnguagd.esm", "HearthFires.esm", "Dragonborn.esm",
                   "HighResTexturePack01.esp",
                   "HighResTexturePack02.esp",
                   "HighResTexturePack03.esp")

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

