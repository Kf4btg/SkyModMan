from itertools import chain

from skymodman import Manager
from skymodman.installer.common import *
from skymodman.installer.element import Element
from skymodman.thirdparty.untangle import untangle
from skymodman.types.color import Color


dep_checks = {
    # key is dependency type
    # s=self, d=dependency item
    "fileDependency": lambda s, d: s.check_file(d.file,
                                                d.state),
    "flagDependency": lambda s, d: s.check_flag(d.flag,
                                                d.value),
    "gameDependency": lambda s, d: s.check_game_version(d),
    "fommDependency": lambda s, d: s.check_fomm_version(d),
}
"""determine which check method to invoke based on dep. type"""

# map operators to python functors
operator_func = {
    Operator.OR:  any,  # true if any item is true
    Operator.AND: all  # true iff all items are true
}

class Fomod:

    def __init__(self, config_xml):
        self.fomod_config = untangle.parse(config_xml)

        self.all_images = []


        self.modname = None
        self.modimage = None
        self.moddeps = None
        self.reqfiles = []
        self.installsteps = []
        self.condinstalls = []

        # used during run
        self.files_to_install = []
        self.flags = {}

        self.analyze()

    ##=============================================
    ## XML-parsing and script setup
    ## --------------------------------------------
    ## should only ever be called once (during
    ## __init__) for each Fomod instance
    ##=============================================
    # <editor-fold desc="setup">

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

        self.modimage = ModImage(_pathfix(mimg["path"]) or defs["path"],

                                 _tobool(mimg["showImage"]
                                         or defs["showImage"]),

                                 _tobool(mimg["showFade"]
                                         or defs["showFade"]),

                                 int(mimg["height"]
                                     or defs["height"])
                                 )
        if self.modimage.path and self.modimage.path != "screenshot.png":
            self.all_images.append(self.modimage.path)

        ## mod dependencies
        self.moddeps = self._getdeps(root.moduleDependencies)

        ## required install files
        self.reqfiles = self._getfiles(root.requiredInstallFiles)

        # go ahead and add these to install list
        if self.reqfiles:
            self.files_to_install.extend(self.reqfiles)

        ## conditional file installs
        self.condinstalls = self._getpatterns(root.conditionalFileInstalls)

        ## install steps
        self.installsteps = self._getinstallsteps(root.installSteps)

    @staticmethod
    def _getdeps(element):
        if not element:
            return None

        dparent = element.dependencies
        deps = Dependencies()

        if dparent:
            deps.operator = Operator(dparent["operator"] or "And")
        else:
            dparent = element

        if not len(dparent):
            return None

        deps.fileDependency = [FileDep(_pathfix(d["file"]),
                                       FileState(d["state"]))
                               for d in dparent.fileDependency]

        deps.flagDependency = [FlagDep(d["flag"], d["value"])
                               for d in dparent.flagDependency]

        deps.gameDependency = dparent.gameDependency[
            "version"] if dparent.gameDependency else None

        deps.fommDependency = dparent.fommDependency[
            "version"] if dparent.fommDependency else None

        return  deps

    @staticmethod
    def _getfiles(element, defs = DEFAULTS["file"]):
        if not element:
            return None

        fparent = element.files or element

        files = []
        for f in chain(fparent.file, fparent.folder):
            # ftype = File if f._name == "file" else Folder

            # File(type, source, destination,
            #      priority, alwaysInstall, installIfUsable)

            files.append(File(

                # type (either 'file' or 'folder')
                f._name.lower(),

                # source
                _pathfix(f["source"]),

                # destination
                "" if f["destination"]==""
                   else _pathfix(f["destination"] or f["source"]),

                # priority
                int(f["priority"] or defs["priority"]),

                # alwaysInstall
                _tobool(f["alwaysInstall"] or defs["alwaysInstall"]),

                # installIfUsable
                _tobool(f["installIfUsable"] or defs["installIfUsable"])
              ))
        return files

    def _getpatterns(self, element):
        if not element:
            return None

        pats=[]
        parent = element.patterns
        if not parent:
            parent = element

        for pat in parent.pattern:
            p = Pattern()

            if pat.type:
                p.type = PluginType(pat.type["name"])
            p.dependencies = self._getdeps(pat)
            p.files = self._getfiles(pat)
            pats.append(p)

        return pats

    def _getinstallsteps(self, element):
        if not element:
            return None

        steps = []

        for step in element.installStep:
            s = InstallStep(step["name"])
            s.visible = self._getdeps(step.visible)
            s.optionalFileGroups = self._getgroups(step.optionalFileGroups)

            steps.append(s)
        return steps

    def _getgroups(self, element):
        if not element:
            return None

        groups = []

        for group in element.group:
            g = Group(group["name"], GroupType(group["type"]))
            g.plugin_order = group.plugins["order"]
            g.plugins = self._getplugins(group.plugins)

            groups.append(g)

        return groups


    def _getplugins(self, element):
        if not element:
            return None

        plugs = []

        for plugin in element.plugin:
            p = Plugin(plugin["name"])
            p.description = plugin.description.cdata

            if plugin.image:
                p.image = _pathfix(plugin.image["path"])
                if p.image:
                    self.all_images.append(p.image)

            if plugin.conditionFlags:
                p.conditionFlags = [Flag(f["name"], f.cdata)
                                    for f in plugin.conditionFlags.flag]

            p.files = self._getfiles(plugin)

            tipe = plugin.typeDescriptor
            if tipe.type: #simple type
                p.type = PluginType(tipe.type["name"])
            else: # dependency type
                dt = tipe.dependencyType
                p.type = PluginType(dt.defaultType["name"])
                p.patterns = self._getpatterns(dt.patterns)

            plugs.append(p)

        return plugs

    # </editor-fold>

    ##=============================================
    ## Called by script-runner during installation
    ##=============================================

    def add_conditional_install_files(self):
        """
        Called after all the install steps have run; Adds any files
        that meet a conditional-install check to the list of files to
        install
        """

        if self.condinstalls:
            for pattern in self.condinstalls:
                if self.check_dependencies_pattern(
                        pattern.dependencies):
                    self.files_to_install.extend(pattern.files)


    def mark_file_for_install(self, file, install=True):
        """

        :param common.File file:
        :param install: if true, mark the file for install; if False,
            remove it from the list of files to install
        """
        if install:
            self.files_to_install.append(file)
        else:
            try:
                self.files_to_install.remove(file)
            except ValueError:
                # file may not have been in list to begin with, which is ok
                print("ValueError: {}".format(file))
                pass

    #=================================
    # dependency checks
    #---------------------------------

    def check_dependencies_pattern(self, dependencies):
        """

        :param common.Dependencies dependencies: A ``Dependencies``
            object extracted from the fomod config.
        :return: boolean indicating whether the dependencies were
            satisfied.
        """
        # print(self.check_file.cache_info())

        # condition will be one of the builtin 'any' or 'all' functions
        condition = operator_func[dependencies.operator]

        return condition(
            dep_checks[dtype](self, dep)
            for dtype, dep in dependencies)

    def check_file(self, file, state):
        # Manager caches the results of the most recent checks
        return Manager().checkFileState(file, state)

    def check_flag(self, flag, value):
        return flag in self.flags \
               and self.flags[flag] == value

    ### The game and fomm version checks are specified in the FOMOD
    # spec file, but don't ever really apply to us, so we just return
    # True

    # noinspection PyUnusedLocal
    def check_game_version(self, version):
        return True

    # noinspection PyUnusedLocal
    def check_fomm_version(self, version):
        return True

    ##=============================================
    ## Other
    ##=============================================

    def set_flag(self, flag, value):
        self.flags[flag] = value

    def unset_flag(self, flag):
        try:
            del self.flags[flag]
        except KeyError:
            pass




# <editor-fold desc="helpers">
def _pathfix(path:str):

    return path.replace('\\', '/')

def _tobool(val):
    v = val.lower()
    if v in ("true", "t", "yes", "y", "1"):
        return True
    if v in ("false", "f", "no", "n", "0"):
        return False

    # fallback
    return bool(val)

# </editor-fold>

# I don't know if this is the right way to do this...
# but it was the only way I could figure out (short of
# duplicating most of its code) to get untangle
# to use my Element subclass above

setattr(untangle, "_Element", untangle.Element)
setattr(untangle, "Element", Element)

#
# if __name__ == '__main__':
#     import sys
#     f = Fomod(sys.argv[1])
#
#     print("\n----Mod Name----")
#     print(f.modname)
#     print("\n----Mod Image----")
#     print(f.modimage)
#     print("\n----Required Installs----")
#     print(f.reqfiles)
#     print("\n----Conditional Installs----")
#     print(f.condinstalls)
#     print("\n----Install Steps----")
#     print(f.installsteps)
