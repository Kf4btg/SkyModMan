"""
Contains classes that are containers for various strings used as keys
to refer to various information throughout the project. These
Key Strings should be used instead of raw strings in all instances in
order to maintain expandability and interoperability.
"""

__all__=["Section", "INI", "Dirs", "UI"]

##=============================================
## Metaclass
##=============================================

class Iternum(type):
    """
    Using this as a metaclass, one can iterate over the public class-level fields
    of a non-instantiated subclass (ie the type object itself). See INI below for
    an example
    """
    def __iter__(cls):
        yield from (v for k,v in cls.__dict__.items() if not k.startswith('_'))

    def __contains__(cls, val):
        return val in [v for k,v in cls.__dict__.items() if not k.startswith('_')]

##=============================================
## Implementations
##=============================================

class Section(metaclass=Iternum):
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
    """Directory Overrides (profile INIs only)"""

    OVR_ENABLED = "Enabled Overrides"
    """Enabled Overrides (profile INIs only)"""

    FILEVIEWER = "File Viewer"
    """Settings for the File Viewer tab"""


class INI(metaclass=Iternum):
    """
    Key Strings for referencing entries under an INI Section.

    Thanks to the Iternum metaclass, the public fields in this class
    can be iterated over without having to instantiate the class,
    simply by doing something like:

        >>> for f in INI:
        >>>     print(f)
    """
    ## main INI
    LAST_PROFILE = "last_profile"  # name of last loaded profile
    """name of last loaded profile"""

    DEFAULT_PROFILE = "default_profile"
    """name of default profile"""

    ## profiles only
    ACTIVE_ONLY = "active_only"
    """Boolean indicating whether all mods or just active mods should be shown in the mod-files list"""


class Dirs(metaclass=Iternum):
    """Key strings for referring to application directories"""
    PROFILES = "dir_profiles"  # storage location for user profiles
    """storage location for user profiles"""

    SKYRIM = "dir_skyrim"  # location of base skyrim install
    """location of base skyrim install"""

    MODS = "dir_mods"  # location of mod storage
    """Location of Mod Storage"""

    VFS = "dir_vfs"  # mount point for "virtual" skyrim install
    """mount point for "virtual" skyrim install"""


class UI(metaclass=Iternum):
    """These are specific to the QSettings part of the main UI"""
    RESTORE_WINSIZE = "restore_window_size"
    RESTORE_WINPOS = "restore_window_pos"

    PROFILE_LOAD_POLICY = "load_profile_on_start"

    LOAD_LAST_PROFILE = "load_last_profile"
    LOAD_DEFAULT_PROFILE = "load_default_profile"
    LOAD_NO_PROFILE = "load_no_profile"