from enum import Enum, IntEnum


# using IntEnums here because they are interacting with code I can't change (Qt)
# which sends ints around quite a bit. Rather than having to look up the enum
# value each time, I think it's better just to have them comparable to ints.
class Tab(IntEnum):
    MODTABLE, FILETREE, INSTALLER = range(3)

class Column(IntEnum):
    ENABLED, ORDER, NAME, DIRECTORY, MODID, VERSION, ERRORS = range(7)

# VISIBLE_COLS = [Column.ENABLED, Column.NAME, Column.MODID, Column.VERSION]

# DBLCLICK_COLS = [Column.MODID, Column.VERSION]

class qModels(Enum):
    mod_table, profile_list, file_viewer = range(3)
    mod_list = mod_table

class qFilters(Enum):
    mod_list, file_viewer, mod_table = range(3)

class SyncError(Enum):
    NOTFOUND, NOTLISTED = range(2)

class EnvVars(str, Enum):
    MOD_DIR = "SMM_MODDIR"
    PROFILE = "SMM_PROFILE"
    USE_QT  = "SMM_QTGUI"
    VFS_MOUNT = "SMM_VFS"
    SKYDIR = "SMM_SKYRIMDIR"

# labels for the sections and settings in the main INI config file.
# making these strEnums because I tire of typing .value over and over...
class INISection(str, Enum):
    """Only one section at the moment"""
    DEFAULT = "General"
    GENERAL = DEFAULT

class INIKey(str, Enum):
    SKYRIMDIR   = "skyriminstalldir"    # location of base skyrim install
    LASTPROFILE = "lastprofile"         # name of last loaded profile
    MODDIR      = "modsdirectory"       # location of mod storage
    VFSMOUNT    = "virtualfsmountpoint" # mount point for "virtual" skyrim install




# defines the names and order of fields in the database
db_fields = ["ordinal", "directory", "name", "modid", "version", "enabled"]

# a tuple of the db fields without the ordinal field;
# simply for convenience. As it constructed from a set, it
# Should only be used where the order of the fields doesn't matter
noordinal_dbfields = tuple(set(db_fields) ^ {"ordinal"})

## After about two months of working on this, this was my first time diving into the ModOrganizer code to search for the answer to a question I couldn't otherwise figure out. Specifically: "What constitutes 'proper' mod structure?" As I expected, the answer was pretty specific.

TopLevelDirs = {"distantlod", "facegen", "fonts", "interface",
                "menus", "meshes", "music", "scripts", "shaders",
                "sound", "strings", "textures", "trees", "video",
                "skse", "obse", "nvse", "fose", "asi", "skyproc patchers"
                }

TopLevelDirs_Bain = TopLevelDirs | {"docs", "ini tweaks"}

TopLevelSuffixes = {"esp", "esm", "bsa"}

## PS: It was also the first time I realized that MO was already written in Qt...
