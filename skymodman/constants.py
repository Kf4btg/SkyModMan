from enum import Enum, IntEnum

class BitEnum(Enum):
    """
    A type of enum that supports certain binary operations between its
    instances, namely & (bitwise-and) and | (bitwise-or). It also
    defines a bool-conversion where the member with value 0 will
    evaluate False, while all other values evaluate True.

    For this to work properly, the underlying type of the members
    should be int, and the subclass MUST define a "None"-like member
    with value 0.

    If a bitwise operation returns a result that is a valid member
    of the Enum (perhaps a combination you wanted to use often and
    thus defined within the enum itself), that enum member will be
    returned. If the result is not a valid member of this enum, then
    the int result of the operation will be returned instead. This
    allows saving arbitrary combinations for use as flags.

    These aspects allow for simple, useful statements like:

        >>> if some_combined_MyBitEnum_value & MyBitEnum.memberA:
        >>>     ...

    to see if 'MyBitEnum.memberA' is present in the bitwise combination
    'some_combined_MyBitEnum_value'
    """


    def __and__(self, other):
        try:
            try:
                val = other.value
            except AttributeError:
                # then see if its an int(able)
                val = int(other)
            res = self.value & val
        except (ValueError, TypeError):
            return NotImplemented

        try:
            return type(self)(res)
        except ValueError:
            return res

    def __or__(self, other):
        try:
            try:
                val = other.value
            except AttributeError:
                # then see if its an int(able)
                val = int(other)
            res = self.value | val
        except (ValueError, TypeError):
            return NotImplemented

        try:
            return type(self)(res)
        except ValueError:
            return res
        # try:
        #     return type(self)(self.value | other.value)
        # except ValueError:
        #     return type(self)(0)
        # except AttributeError:
        #     return NotImplemented

    def __bool__(self):
        return self.value != 0

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
    NONE, NOTFOUND, NOTLISTED = range(2)

class ModError:
    NONE = 0
    DIR_NOT_FOUND = 1
    MOD_NOT_LISTED = 2
    MISSING_FILES = 4


class EnvVars(str, Enum):
    MOD_DIR = "SMM_MODDIR"
    PROFILE = "SMM_PROFILE"
    USE_QT  = "SMM_QTGUI"
    VFS_MOUNT = "SMM_VFS"
    SKYDIR = "SMM_SKYRIMDIR"

# labels for the sections and settings in the main INI config file.
# making these strEnums because I tire of typing .value over and over...
class INISection(str, Enum):
    """
    Configuration Headings in the various INI files.

    DEFAULT and GENERAL are the same thing.

    OVERRIDES is actually in the individual profile config files,
    and contains values that override the default directory settings
    """
    NONE = ""

    # main INI
    DEFAULT = "General"
    GENERAL = DEFAULT
    DIRECTORIES = "Directories"

    # profile INIs
    OVERRIDES = "Directory Overrides"
    FILEVIEWER = "File Viewer"

class Iternum(type):
    """
    Using this as a metaclass, one can iterate over the public class-level fields
    of a non-instantiated subclass (ie the type object itself). See INI below for
    an example
    """
    def __iter__(cls):
        yield from (v for k,v in cls.__dict__.items() if not k.startswith('_'))

class KeyStr:
    __slots__ = ()

    class Section(metaclass=Iternum):
        __slots__=()
        NONE = ""

        # main INI
        DEFAULT = "General"
        GENERAL = DEFAULT
        DIRECTORIES = "Directories"

        # profile INIs
        OVERRIDES = "Directory Overrides"
        FILEVIEWER = "File Viewer"


    class INI(metaclass=Iternum):
        """
        Thanks to the Strenum metaclass, the public fields in this class
        can be iterated over without having to instantiate the class,
        simply by doing something like:

            >>> for f in INI:
            >>>     print(f)
        """
        __slots__=()
        ## main INI
        LASTPROFILE = "lastprofile"  # name of last loaded profile
        DEFAULT_PROFILE = "defaultprofile"

        ## profiles only
        ACTIVEONLY = "activeonly"

    class Dirs(metaclass=Iternum):
        __slots__=()
        PROFILES = "dir_profiles" # storage location for user profiles
        SKYRIM = "dir_skyrim"  # location of base skyrim install
        MODS = "dir_mods"  # location of mod storage
        VFS = "dir_vfs"  # mount point for "virtual" skyrim install

    class UI(metaclass=Iternum):
        __slots__=()
        RESTORE_WINSIZE = "restore_window_size"
        RESTORE_WINPOS = "restore_window_pos"

        PROFILE_LOAD_POLICY = "load_profile_on_start"

        LOAD_LAST_PROFILE = "load_last_profile"
        LOAD_DEFAULT_PROFILE = "load_default_profile"
        LOAD_NO_PROFILE = "load_no_profile"

# For things that are going to presented to the user as
# customizable preferences, we also need a user-friendly
# display name to plug into labels and messages
DisplayNames = {
    KeyStr.INI.ACTIVEONLY: "Only Show Active Mods",
    KeyStr.INI.DEFAULT_PROFILE: "Default Profile",
    KeyStr.INI.LASTPROFILE: "Last Loaded Profile",

    KeyStr.Dirs.PROFILES: "Profiles Directory",
    KeyStr.Dirs.SKYRIM: "Skyrim Installation",
    KeyStr.Dirs.MODS: "Mods Directory",
    KeyStr.Dirs.VFS: "Virtual FS Mount Point",

    KeyStr.UI.RESTORE_WINSIZE: "Restore Window Size",
    KeyStr.UI.RESTORE_WINPOS: "Restore Window Position",
}

class ProfileLoadPolicy(Enum):
    last, default, none = range(3)


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

# this profile must exist. If it doesn't, we must create it.
FALLBACK_PROFILE = "default"

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

