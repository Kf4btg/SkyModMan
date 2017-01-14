from enum import Enum, IntEnum, Flag, IntFlag, auto

__all__=["Tab", "Column", "qModels", "qFilters", "ProfileLoadPolicy", "OverwriteMode", "EnvVars", "ModError"]

##=============================================
## Metaclasses
##=============================================

# class Iternum(type):
#     """
#     Using this as a metaclass, one can iterate over the public class-level fields
#     of a non-instantiated subclass (ie the type object itself). See INI below for
#     an example
#     """
#     def __iter__(cls):
#         yield from (v for k,v in cls.__dict__.items() if not k.startswith('_'))

##=============================================
## IntEnums
##=============================================

# using IntEnums here because they are interacting with code I can't change (Qt)
# which sends ints around quite a bit. Rather than having to look up the enum
# value each time, I think it's better just to have them comparable to ints.
class Tab(IntEnum):
    MODTABLE, FILETREE, INSTALLER = range(3)

class Column(IntEnum):
    """These values are going to be compared with
    the column() property of QModelIndexes...Indices...
    Indixes--whatever--which is an int."""
    ENABLED, ORDER, NAME, DIRECTORY, MODID, VERSION, ERRORS = range(7)

class FileTreeColumn(IntEnum):
    # same here
    NAME, PATH, CONFLICTS = range(3)

##=============================================
## "Plain" enum subclasses
##=============================================

class qModels(Enum):
    mod_table = auto()
    profile_list = auto()
    file_viewer = auto()
    # mod_table, profile_list, file_viewer = range(3)
    mod_list = mod_table

class qFilters(Enum):
    mod_table = auto()
    mod_list = auto()
    file_viewer = auto()
    # mod_list, file_viewer, mod_table = range(3)

class ProfileLoadPolicy(Enum):
    none, last, default = range(3)

##=============================================
## Str-enums
##=============================================

class EnvVars(str, Enum):
    MOD_DIR = "SMM_MODDIR"
    PROFILE = "SMM_PROFILE"
    USE_QT  = "SMM_QTGUI"
    VFS_MOUNT = "SMM_VFS"
    SKYDIR = "SMM_SKYRIMDIR"

##=============================================
## Flags
##=============================================

class ModError(IntFlag):
    """
    Flags for types of errors encountered during mod-loading.

    Note: IntFlag (rather than regular flag) because its values are
    going to be passed around via Qt's signal/slot mechanism, and it's
    just easier to use primitive types there.
    """
    NONE = 0
    DIR_NOT_FOUND = auto()
    MOD_NOT_LISTED = auto()
    MISSING_FILES = auto()

class OverwriteMode(Flag):
    """
    Used for name-conflicts when rearranging files in the
    pseudo-file-system view of the manual install dialog.

    PROMPT essentially means allow the error to be raised.
    It can then be caught and handled by the caller.
    """
    PROMPT = 0
    IGNORE = auto()
    REPLACE = auto()
    MERGE = auto()

    MERGE_IGNORE_EXISTING_FILES = MERGE|IGNORE
    MERGE_REPLACE_EXISTING_FILES = MERGE|REPLACE