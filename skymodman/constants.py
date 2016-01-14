from enum import Enum, IntEnum


# using IntEnums here because they are interacting with code I can't change (Qt)
# which sends ints around quite a bit. Rather than having to look up the enum
# value each time, I think it's better just to have them comparable to ints.
class Tab(IntEnum):
    MODLIST, FILETREE, INSTALLER = range(3)

class Column(IntEnum):
    ENABLED, NAME, MODID, VERSION, DIRECTORY, ORDER = range(6)

VISIBLE_COLS = [Column.ENABLED, Column.NAME, Column.MODID, Column.VERSION]

DBLCLICK_COLS = [Column.MODID, Column.VERSION]

class SyncError(Enum):
    NOTFOUND, NOTLISTED = range(2)

class EnvVars(str, Enum):
    MOD_DIR = "SMM_MODDIR"
    PROFILE = "SMM_PROFILE"
    USE_QT  = "SMM_QTGUI"
    VFS_MOUNT = "SMM_VFS"

# labels for the sections and settings in the main INI config file.
# making these strEnums because I tire of typing .value over and over...
class INISection(str, Enum):
    """Only one section at the moment"""
    DEFAULT = "General"
    GENERAL = DEFAULT

class INIKey(str, Enum):
    LASTPROFILE = "lastprofile"
    MODDIR = "modsdirectory"
    VFSMOUNT = "virtualfsmountpoint"




# defines the names and order of fields in the database
db_fields = ["ordinal", "directory", "name", "modid", "version", "enabled"]

# a tuple of the db fields without the ordinal field;
# simply for convenience. As it constructed from a set, it
# Should only be used where the order of the fields doesn't matter
noordinal_dbfields = tuple(set(db_fields) ^ {"ordinal"})