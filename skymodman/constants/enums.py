from enum import Enum, IntEnum

__all__=["Tab", "Column", "qModels", "qFilters", "ProfileLoadPolicy", "OverwriteMode", "EnvVars", "ModError"]

##=============================================
## Metaclasses
##=============================================

class Iternum(type):
    """
    Using this as a metaclass, one can iterate over the public class-level fields
    of a non-instantiated subclass (ie the type object itself). See INI below for
    an example
    """
    def __iter__(cls):
        yield from (v for k,v in cls.__dict__.items() if not k.startswith('_'))

##=============================================
## IntEnums
##=============================================

# using IntEnums here because they are interacting with code I can't change (Qt)
# which sends ints around quite a bit. Rather than having to look up the enum
# value each time, I think it's better just to have them comparable to ints.
class Tab(IntEnum):
    MODTABLE, FILETREE, INSTALLER = range(3)

class Column(IntEnum):
    ENABLED, ORDER, NAME, DIRECTORY, MODID, VERSION, ERRORS = range(7)

##=============================================
## "Plain" enum subclasses
##=============================================

class qModels(Enum):
    mod_table, profile_list, file_viewer = range(3)
    mod_list = mod_table

class qFilters(Enum):
    mod_list, file_viewer, mod_table = range(3)

class ProfileLoadPolicy(Enum):
    none, last, default = range(3)

class OverwriteMode(Enum):
    """
    Used for name-conflicts when rearranging files in the
    pseudo-file-system view of the manual install dialog.

    Binary ops & and | have been implemented for this type,
    as well as the __bool__ function so that PROMPT (with int
    value 0) will indicate False while the other values are True

    PROMPT essentially means allow the error to be raised.
    It can then be caught and handled by the caller.
    """
    PROMPT = 0
    IGNORE = 1
    REPLACE = 2
    MERGE = 4

    MERGE_IGNORE_EXISTING_FILES = MERGE|IGNORE
    MERGE_REPLACE_EXISTING_FILES = MERGE|REPLACE

    def __and__(self, other):
        try:
            return OverwriteMode(self.value & other.value)
        except ValueError:
            return OverwriteMode.PROMPT
        except AttributeError:
            return NotImplemented

    def __or__(self, other):
        try:
            return OverwriteMode(self.value | other.value)
        except ValueError:
            return OverwriteMode.PROMPT
        except AttributeError:
            return NotImplemented

    def __bool__(self):
        return self.value != 0


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
## "Fake" enums
##=============================================

class ModError:
    """
    Didn't bother subclassing this one from enum...its meant to be
    used as a bitmask, and this is just easier that something like what
    I did with OverwriteMode.
    """
    NONE = 0
    DIR_NOT_FOUND = 1
    MOD_NOT_LISTED = 2
    MISSING_FILES = 4