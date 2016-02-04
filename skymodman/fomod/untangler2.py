from collections import deque, namedtuple
from enum import Enum
from itertools import chain, repeat

from functools import partial

from skymodman.thirdparty.untangle import untangle
from skymodman.utils.color import Color
# from skymodman.managers import modmanager as Manager
from skymodman import exceptions

class Element(untangle.Element):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # part of a hack to prevent empty lines from filling up all
        # the 'cdata' attributes
        self.prev2=""
        self.prev1=""

    @property
    def attributes_(self)->dict:
        return self._attributes

    def get_attribute(self, key, default=None):
        value = super().get_attribute(key)

        return default if value is None else value

    def __getattr__(self, key):
        try:
            return super().__getattr__(key)
        except AttributeError:
            return []

    def iter_all(self):
        """
        Recursively iterate over this element and all its children

        """
        yield self
        if len(self):
            for c in self.children:
                yield from c.iter_all()

    def add_cdata(self, cdata):
        """
        Squeezes blank lines together
        :param cdata:
        """
        if cdata.isspace():
            if self.prev1=="": return
            if self.prev1=="\n" \
                    and self.prev2 in ["","\n"]: return
            cdata='\n' # reduce all blank lines to a bare newline

        super().add_cdata(cdata)

        self.prev2=self.prev1
        self.prev1=cdata.strip(" \r")

    def attribute_pairs(self):
        """

        :yields: the attributes of the element as (key, value) tuples
        """
        yield from ((k,v) for k,v in self._attributes.items())



class fomodcommon:

    commands = r"/.#@|!&~"
    suffixes = r"?*|$"

    # <editor-fold desc="command documentation">
    # each command is a command-char followed by an element or attribute name
    cmd_doc = {
        "Selectors": {
            # these will throw exceptions of the target does not exist
            '/': "select (move to) child element w/ given name under root."
                 " note that here, 'root' refers to element that was current"
                 " at the time the script was entered; if the client is running"
                 " a sub-script (through the ! command), the root is likely to"
                 " be different from the main root, which makes it easier to focus"
                 " on a 'sub-tree' of elements.",
            '.': "select child w/ given name under current element",
            '~': "move to sibling (child of current element's parent); this"
                 " is also the 'default' command, and so can usually be omitted:"
                 " '~sibling' == 'sibling'",
            '|': "mutually-exclusive sibling selector. See '|' under Suffixes.",

            ## Data Request Commands
            '#': "this is a combination command that could have a different"
                 " meaning depending on how it is used. If given bare (with"
                 " no name), it means 'request the cdata/text from the"
                 " current element. If a name is provided that is the name"
                 " of one of the children of the current element, then it"
                 " indicates 'move to the [first] child with the given name"
                 " AND request the value of its cdata/text attribute.'",
            '@': "request value of named attribute from current element",

            ## Control Commands (these commands not sent to server)
            '!': "run script (series of commands) w/ given name",
            '&': "query the controller for a reponse about the most recent"
                 " command of this name that was marked w/ the '$' suffix;"
                 " if the controller returns a True response, then continue"
                 " with the script; otherwise, move up a script level (even"
                 " out of the script altogether if this occurs in the 'main'"
                 " script.",},

        "Suffixes": {  # (add after name, eg '.elname?')

            # for navigation (will not throw exceptions)
            '?': "move to `target` if exists(`target`); if the target does"
                 " not exist, script execution will continue at the next"
                 " movement command (i.e. any data/script commands that"
                 " come after this command and the next movement cmd will be"
                 " skipped.",
            '*': "foreach `target` w/ given name: ...",
            '|': "the mutually-exclusive sibling marker can be used as both a"
                 " suffix and command (prefix). As a prefix, it can be thought"
                 " of as being similar to '?': select the target if it exists."
                 " If the target did in fact exist, its sub-commands will be"
                 " executed, and then any consecutive commands using '|' as "
                 " a selector will be skipped, without selection being attempted."
                 " However, if the target does not exist and the next selector"
                 " command is '|', attempt to select that element instead. If"
                 " a chain of '|' selectors are used, then the first target that"
                 " exists will be selected and the rest skipped. This is very"
                 " similar to a 'if: elif: ...' construct. The target elements"
                 " in the chain must be siblings. Of special note is that if a"
                 " command starts with '|' but was preceded by a command that"
                 " neither had a '|' suffix nor was a skipped member of a chain,"
                 " the '|' will be ignored and sibling selection will proceed"
                 " as if the command actually started with '~'.",

            # Example:
            #   .chain1|
            #       ...
            #   |chain2|
            #       ...
            #   |chain3
            #       ...
            #   not_in_chain

            # other
            '$': "marks a command as a fork point requiring special handling:"
                 " the client's controller should be queried after such a marked"
                 " command to decide what to do next (see the '&' command above)",
        }
    }
    # </editor-fold>

    class FomodError(exceptions.Error):
        pass

    class NoSuchElement(FomodError):
        """
        Indicates to the consumer that the element they requested does not exist.
        """
        pass

    class BadCommand(FomodError):
        """
        Indicates an unrecognized command was received
        """
        pass

modname = namedtuple("modname", "name position colour")
modimage = namedtuple("modimage", "path showImage showFade height")
file = namedtuple("file", "source destination priority alwaysInstall installIfUsable")
folder = namedtuple("folder", *file._fields)
flag = namedtuple("flag", "name value")

filedep = namedtuple("filedep", "file state")
flagdep = namedtuple("flagdep", "flag value")

class Dependencies:
    __slots__ = "operator", "fileDependency", "flagDependency", "gameDependency", "fommDependency"

    def __init__(self, operator=Operator.AND, fileDependency=None, flagDependency=None, gameDependency=None, fommDependency=None):
        self.operator = operator
        self.fileDependency = [] if fileDependency is None else fileDependency
        self.flagDependency = [] if flagDependency is None else flagDependency
        self.gameDependency = gameDependency
        self.fommDependency = fommDependency

    def __iter__(self):
        yield from chain(zip(repeat("fileDependency"), self.fileDependency),
                         zip(repeat("flagDependency"), self.flagDependency))
        if self.gameDependency: yield ("gameDependency", self.gameDependency)
        if self.fommDependency: yield ("fommDependency", self.fommDependency)

    def __len__(self):
        return len(self.fileDependency) + len(self.flagDependency) + bool(self.gameDependency) + bool(self.fommDependency)

class Pattern:
    __slots__ = "type", "dependencies", "files"

    def __init__(self, type_ = None, depends = None, files = None):
        self.type = type_
        self.dependencies = depends
        self.files = [] if not files else files

class InstallStep:
    __slots__ = "name", "visible", "optionalFileGroups"

    def __init__(self, name):
        self.name = name
        self.visible = None
        self.optionalFileGroups = []

class Group:
    __slots__ = "name", "type", "plugins", "plugin_order"

    def __init__(self, name, group_type):
        self.name = name
        self.type = group_type
        self.plugin_order = Order.ASC
        self.plugins = []

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





class FomodServer:
    def __init__(self, config_xml):
        self.fomod_config = untangle.parse(config_xml)
        self.connected_client = None
        self.modname = None
        self.modimage = None
        self.moddeps = None # []
        self.reqfiles = []
        self.installsteps = []
        self.condinstalls = []


    def analyze(self):
        root = self.fomod_config.config # type: Element

        ## mod name
        self.modname = modname(root.moduleName.cdata,
                               Position(root.moduleName['position']
                                        or DEFAULTS["moduleName"]
                                        ["position"]),
                               Color.from_hexstr(
                                   root.moduleName.colour or
                                   DEFAULTS["moduleName"]["colour"]
                               ))
        ## mod image
        defs = DEFAULTS["moduleImage"]
        mimg = root.moduleImage or Element("moduleImage", defs)

        self.modimage = modimage(mimg["path"] or defs["path"],

                                 _tobool(mimg["showImage"]
                                         or defs["showImage"]),

                                 _tobool(mimg["showFade"]
                                         or defs["showFade"]),

                                 int(mimg["height"]
                                     or defs["height"])
                                 )

        ## mod dependencies
        self.moddeps = self._getdeps(root.moduleDependencies)

        ## required install files
        self.reqfiles = self._getfiles(root.requiredInstallFiles)

        ## conditional file installs
        self.condinstalls = self._getpatterns(root.conditionalFileInstalls)

        ## install steps
        self.installsteps = self._getinstallsteps(root.installSteps)

    @staticmethod
    def _getdeps(element):
        if not element: return None

        dparent = element.dependencies
        deps = Dependencies()

        if dparent:
            deps.operator = Operator(dparent["operator"] or "And")
        else:
            dparent = element

        if not len(dparent): return None

        deps.fileDependency = [filedep(d["file"],
                                       FileState(d["state"]))
                               for d in dparent.fileDependency]

        deps.flagDependency = [flagdep(d["flag"], d["value"]) for d in dparent.flagDependency]


        deps.gameDependency = dparent.gameDependency["version"] if dparent.gameDependency else None

        deps.fommDependency = dparent.fommDependency["version"] if dparent.fommDependency else None

        return  deps


    @staticmethod
    def _getfiles(element, defs = DEFAULTS["file"]):
        if not element: return None

        fparent = element.files or element

        files = []
        for f in chain(fparent.file, fparent.folder):
            ftype = file if f._name == "file" else folder

            files.append(
                ftype(f["source"],
                      f["destination"] or f["source"],

                      int(f["priority"]
                          or defs["priority"]),

                      _tobool(f["alwaysInstall"]
                              or defs["alwaysInstall"]),

                      _tobool(f["installIfUsable"]
                              or defs["installIfUsable"])
                      ))
        return files

    @classmethod
    def _getpatterns(cls, element):
        if not element: return None

        pats=[]
        parent = element.patterns
        if not parent:
            parent = element

        for pat in parent.pattern:
            p = Pattern(pat.type["name"])
            p.dependencies = cls._getdeps(pat)
            p.files = cls._getfiles(pat)
            pats.append(p)

        return pats

    @classmethod
    def _getinstallsteps(cls, element):
        if not element: return None

        steps = []

        for step in element.installStep:
            s = InstallStep(step["name"])
            s.visible = cls._getdeps(step.visible)
            s.optionalFileGroups = cls._getgroups(step.optionalFileGroups)

            steps.append(s)


        return steps

    @classmethod
    def _getgroups(cls, element):
        if not element: return None

        groups = []

        for group in element.group:
            g = Group(group["name"], GroupType(group["type"]))
            g.plugin_order = group.plugins["order"]
            g.plugins = cls._getplugins(group.plugins)

            groups.append(g)

        return groups

    @classmethod
    def _getplugins(cls, element):
        if not element: return None
        plugs = []

        for plugin in element.plugin:
            p = Plugin(plugin["name"])
            p.description = plugin.description.cdata

            if plugin.image:
                p.image = plugin.image["path"]

            if plugin.conditionFlags:
                p.conditionFlags = [flag(f["name"], f.cdata)
                                    for f in plugin.conditionFlags.flag]

            tipe = plugin.typeDescriptor
            if tipe.type: #simple type
                p.type = PluginType(tipe.type["name"])
            else: # dependency type
                dt = tipe.dependencyType
                p.type = PluginType(dt.defaultType["name"])
                p.patterns = cls._getpatterns(dt.patterns)

            plugs.append(p)

        return plugs



    def connect(self, consumer):
        if self.connected_client is None:
            self.connected_client=consumer
            try:
                self.serve(consumer)
            finally:
                consumer.close()
                self.connected_client = None
        else:
            consumer.send(None) # says "I'm busy"





    # noinspection PyNoneFunctionAssignment
    def serve(self, consumer):
        """

        :param __generator consumer: Should be a generator equipped to receive send() commands from the feed. The values yielded by the generator will control the actions of the feeder.
        :return:
        """
        ancestors = deque()

        root = self.fomod_config.config # type: Element


        # this tracks the element hierarchy from root to the
        # current element, allowing us to step back up
        ancestors.append(root)
        # mod name is always first
        current = root.moduleName # type: Element

        # value = current.cdata
        # cmd, suf, name = consumer.send(current.cdata)
        # cmd, suf, name = consumer.send(current.cdata)
        _do = lambda: consumer.send(current.cdata)
        while True:
            cmd, suf, name = _do()

            if cmd is None: # end
                break

            elif cmd == "@": # attributes
                _do = lambda: consumer.send(current[name])

            elif cmd == "#": # cdata/text
                if name:
                    for el in current.get_elements(name):
                        ancestors.append(current)
                        current = el
                        _do = lambda: consumer.send(current.cdata)
                        break
                    else:
                        _do = consumer.throw(fomodcommon.NoSuchElement)
                else:
                    _do = lambda: consumer.send(current.cdata)

            elif cmd == ".":
                if suf == "?":
                    for el in current.get_elements(name):
                        ancestors.append(current)
                        current = el
                        _do = lambda : next(consumer)
                        break
                    else:
                        _do = lambda : consumer.send(False)
                # elif suf == "*":
                #     for el in current.get_elements(name):


                for el in current.get_elements(name):
                    ancestors.append(current)
                    current = el
                    cmd, suf, name = next(consumer)
                    break
                else:
                    cmd, suf, name = consumer.throw(fomodcommon.NoSuchElement)


def _tobool(val):
    v = val.lower()
    if v in ("true", "t", "yes", "y", "1"):
        return True
    if v in ("false", "f", "no", "n", "0"):
        return False

    # fallback
    return bool(val)


# <editor-fold desc="defaults">
# default values for various attributes
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

# some extra things that are duplicates
DEFAULTS["plugins"] = DEFAULTS["installSteps"]
DEFAULTS["folder"] = DEFAULTS["file"]

# todo: add enums?
DEFAULTTYPES= {
    "moduleName":   {
        "colour":   Color.from_hexstr
    },
    "moduleImage":  {
        "showImage": bool,
        "showFade":  bool,
        "height":    int,
    },
    "file":         {
        "alwaysInstall":   bool,
        "installIfUsable": bool,
        "priority":        int
    },
}

DEFAULTTYPES["folder"] = DEFAULTTYPES["file"]


attrs_for_deps = {"fileDependency": ["file", "state"],
                  "flagDependency": ["flag", "value"],
                  "gameDependency": ["version"],
                  "fommDependency": ["version"]}
dep_types = attrs_for_deps.keys()



# I don't know if this is the right way to do this...
# but it was the only way I could figure out (short of
# duplicating most of the code in untangle) to get untangle
# to use my Element subclass above

setattr(untangle, "_Element", untangle.Element)
setattr(untangle, "Element", Element)
# </editor-fold>
