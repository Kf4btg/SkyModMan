
TABS = (TAB_MODLIST, TAB_FILETREE, TAB_INSTALLER) = list(range(3))

# COLUMNS = (COL_NUMBER, COL_ENABLED, COL_MODID, COL_VERSION, COL_NAME) = list(range(4))

COLUMNS = (COL_ENABLED, COL_NAME, COL_MODID, COL_VERSION, COL_DIRECTORY, COL_ORDER) = list(range(6))

VISIBLE_COLS = [COL_ENABLED, COL_NAME, COL_MODID, COL_VERSION]

DBLCLICK_COLS = [COL_MODID, COL_VERSION]

# defines the names and order of fields in the database
db_fields = ["ordinal", "directory", "name", "modid", "version", "enabled"]

# a tuple of the db fields without the ordinal field;
# simply for convenience. As it constructed from a set, it
# Should only be used where the order of the fields doesn't matter
noordinal_dbfields = tuple(set(db_fields) ^ {"ordinal"})


from enum import Enum

class EnvVars(Enum):
    MOD_DIR = "SMM_MODDIR"
    PROFILE = "SMM_PROFILE"
    USE_QT  = "SMM_QTGUI"
    VFS_MOUNT = "SMM_VFS"






