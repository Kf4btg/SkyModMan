
TABS = (TAB_MODLIST, TAB_FILETREE, TAB_INSTALLER) = list(range(3))

# COLUMNS = (COL_NUMBER, COL_ENABLED, COL_MODID, COL_VERSION, COL_NAME) = list(range(4))

COLUMNS = (COL_ENABLED, COL_NAME, COL_MODID, COL_VERSION, COL_DIRECTORY, COL_ORDER) = list(range(6))

VISIBLE_COLS = [COL_ENABLED, COL_NAME, COL_MODID, COL_VERSION]

DBLCLICK_COLS = [COL_MODID, COL_VERSION]

# defines the names and order of fields in the database
db_fields = ["ordinal", "directory", "name", "modid", "version", "enabled"]






