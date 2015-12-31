from enum import Enum
from .fallback_enum import FallbackEnum

class Position(FallbackEnum):
    """
    Valid values for ModName.position
    """
    LEFT  = "Left" # Default
    RIGHT = "Right"
    RIGHT_OF_IMAGE = "RightOfImage"

class Order(FallbackEnum):
    """
    valid values for Group.plugin_order

    ASC = "Ascending" (Default) : Indicates the items are to be ordered ascending alphabetically
    DESC = "Descending" : Indicates the items are to be ordered descending alphabetically
    EXPLICIT = "Explicit" : Indicates the items are to be ordered as listed in the configuration file.

    """
    ASC  = "Ascending" # Default
    DESC = "Descending"
    EXPLICIT = "Explicit"

class GroupType(Enum):
    """
    defines valid type values for groups of optional plugins

    SALO = "SelectAtLeastOne" : At least one plugin in the group must be selected.
    SAMO = "SelectAtMostOne" : At most one plugin in the group must be selected.
    SEO  = "SelectExactlyOne" : Exactly one plugin in the group must be selected.
    SALL = "SelectAll" : All plugins in the group must be selected.
    SANY = "SelectAny" : Any number of plugins in the group may be selected.

    """
    SALO = "SelectAtLeastOne"
    SAMO = "SelectAtMostOne"
    SEO  = "SelectExactlyOne"
    SALL = "SelectAll"
    SANY = "SelectAny"

class PluginType(Enum):
    """
    valid values for plugin type descriptors

    REQ = "Required" : Indicates the plugin must be installed.
    OPT = "Optional" : Indicates the plugin is optional.
    REC = "Recommended" : Indicates the plugin is recommended for stability.
    NU = "NotUsable" : Indicates that using the plugin could result in instability (i.e., a prerequisite plugin is missing).
    CBU = "CouldBeUsable" : Indicates that using the plugin could result in instability if loaded with the currently active plugins (i.e., a prerequisite plugin is missing), but that the prerequisite plugin is installed, just not activated.

    """
    REQ = "Required"
    OPT = "Optional"
    REC = "Recommended"
    NU  = "NotUsable"
    CBU = "CouldBeUsable"

class Operator(FallbackEnum):
    """
    possible options for dependency operator

    AND : Indicates all contained dependencies must be satisfied in order for this dependency to be satisfied.
    OR : Indicates at least one listed dependency must be satisfied in order for this dependency to be satisfied.
    """
    AND = "And" #Default
    OR  = "Or"

class FileState(Enum):
    """
    possible values for the "state" attribute on fileDependency objects

    MISSING = "Missing" : Indicates the mod file is not installed.
    INACTIVE = "Inactive" : Indicates the mod file is installed, but not active.
    ACTIVE = "Active" : Indicates the mod file is installed and active.
    """
    MISSING  = "Missing"
    INACTIVE = "Inactive"
    ACTIVE   = "Active"

