from enum import Enum
from collections import namedtuple
from itertools import chain, repeat

# from skymodman.thirdparty.humanizer import  humanize


from skymodman import exceptions

__all__ = ['ModName', 'ModImage', 'File', 'Folder', 'Flag', 'FileDep',
           'FlagDep', 'Dependencies', 'Pattern', 'InstallStep',
           'Group', 'Plugin',

           'GroupType', 'PluginType', 'FileState', 'Order', 'Position',
           'Operator', 'FomodError', 'DEFAULTS'
           ]

##===============================================
## Constants
##===============================================

class GroupType(Enum):
    ALO = "SelectAtLeastOne"
    AMO = "SelectAtMostOne"
    EXO = "SelectExactlyOne"
    ALL = "SelectAll"
    ANY = "SelectAny"

class PluginType(Enum):
    REQ = "Required"
    OPT = "Optional"
    REC = "Recommended"
    NOT = "NotUsable"
    COU = "CouldBeUsable"

class FileState(Enum):
    M = "Missing"
    I = "Inactive"
    A = "Active"

class Order(Enum):
    EXP = "Explicit"
    DES = "Descending"
    ASC = "Ascending"

class Position(Enum):
    L = "Left"
    R = "Right"
    ROI = "RightOfImage"

class Operator(Enum):
    AND = "And"
    OR = "Or"

##===============================================
## Fomod Element Representations
##===============================================

ModName = namedtuple("modname", "name position colour")
ModImage = namedtuple("modimage", "path showImage showFade height")

File = namedtuple("file", "source destination priority alwaysInstall installIfUsable")
Folder = namedtuple("folder", File._fields)

Flag = namedtuple("flag", "name value")

FileDep = namedtuple("filedep", "file state")
FlagDep = namedtuple("flagdep", "flag value")

# @humanize
class Dependencies:
    __slots__ = "operator", "fileDependency", "flagDependency", "gameDependency", "fommDependency"

    def __init__(self, operator=Operator.AND, fileDependency=None, flagDependency=None, gameDependency=None, fommDependency=None):
        self.operator = operator
        self.fileDependency = [] if fileDependency is None else fileDependency
        self.flagDependency = [] if flagDependency is None else flagDependency
        self.gameDependency = gameDependency
        self.fommDependency = fommDependency

    def __iter__(self):
        """
        Yields 2-tuples where the first element is a string describing
        the type of the dependency and the second is the value (or
        value object) of the dependency.

        :yields: tuple[str, FileDep|FlagDep|str]
        """
        yield from chain(zip(repeat("fileDependency"), self.fileDependency),
                         zip(repeat("flagDependency"), self.flagDependency))
        if self.gameDependency: yield ("gameDependency", self.gameDependency)
        if self.fommDependency: yield ("fommDependency", self.fommDependency)

    def __len__(self):
        return len(self.fileDependency) + len(self.flagDependency) + bool(self.gameDependency) + bool(self.fommDependency)

# @humanize
class Pattern:
    __slots__ = "type", "dependencies", "files"

    def __init__(self, type_ = None, depends = None, files = None):
        self.type = type_
        self.dependencies = depends
        self.files = [] if not files else files

# @humanize
class InstallStep:
    __slots__ = "name", "visible", "optionalFileGroups"

    def __init__(self, name):
        self.name = name
        self.visible = None
        self.optionalFileGroups = []

# @humanize
class Group:
    __slots__ = "name", "type", "plugins", "plugin_order"

    def __init__(self, name, group_type):
        self.name = name
        self.type = group_type
        self.plugin_order = Order.ASC
        self.plugins = []

# @humanize
class Plugin:
    __slots__ = "name", "description", "image", "conditionFlags", "files", "type", "patterns"

    def __init__(self, name, description=None, image=None):
        self.name = name
        self.description = "" if not description else description
        self.image = image
        self.conditionFlags = []
        self.files = []
        self.type = None
        self.patterns = []


##===============================================
## Default Values
##===============================================
DEFAULTS={
    "moduleName": {
        "position": "RightOfImage",
        "colour": "000000"
    },
    "moduleImage": {
        "path": "screenshot",
        "showImage": "True",
        "showFade": "True",
        "height": "-1",
    },
    "installSteps": {
        "order": "Ascending"
    },
    "file": {
        "destination": "", # same as source
        "alwaysInstall": "False",
        "installIfUsable": "False",
        "priority": "0"
    },
    "dependencies": {
        "operator": "And"
    }
}
DEFAULTS["plugins"] = DEFAULTS["installSteps"]
DEFAULTS["folder"] = DEFAULTS["file"]


##===============================================
## Exceptions
##===============================================


class FomodError(exceptions.Error):
    pass


class NoSuchElement(FomodError):
    """
    Indicates to the consumer that the element they requested does not exist.
    """
    pass