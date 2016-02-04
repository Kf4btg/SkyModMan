from itertools import chain

from skymodman.thirdparty.untangle import untangle

from skymodman.utils.color import Color
from skymodman.fomod.common import *


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


class Fomod:
    def __init__(self, config_xml):
        self.fomod_config = untangle.parse(config_xml)


        self.modname = None
        self.modimage = None
        self.moddeps = None
        self.reqfiles = []
        self.installsteps = []
        self.condinstalls = []

        self.analyze()


    def analyze(self):
        root = self.fomod_config.config # type: Element

        ## mod name
        self.modname = ModName(root.moduleName.cdata,
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

        self.modimage = ModImage(mimg["path"] or defs["path"],

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

        deps.fileDependency = [FileDep(d["file"],
                                       FileState(d["state"]))
                               for d in dparent.fileDependency]

        deps.flagDependency = [FlagDep(d["flag"], d["value"]) for d in dparent.flagDependency]


        deps.gameDependency = dparent.gameDependency["version"] if dparent.gameDependency else None

        deps.fommDependency = dparent.fommDependency["version"] if dparent.fommDependency else None

        return  deps


    @staticmethod
    def _getfiles(element, defs = DEFAULTS["file"]):
        if not element: return None

        fparent = element.files or element

        files = []
        for f in chain(fparent.file, fparent.folder):
            ftype = File if f._name == "file" else Folder

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
                p.conditionFlags = [Flag(f["name"], f.cdata)
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






def _tobool(val):
    v = val.lower()
    if v in ("true", "t", "yes", "y", "1"):
        return True
    if v in ("false", "f", "no", "n", "0"):
        return False

    # fallback
    return bool(val)


# I don't know if this is the right way to do this...
# but it was the only way I could figure out (short of
# duplicating most of its code) to get untangle
# to use my Element subclass above

setattr(untangle, "_Element", untangle.Element)
setattr(untangle, "Element", Element)
