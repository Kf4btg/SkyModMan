import asyncio

class DependencyError(Exception):
    pass

class IModInstaller:
    """
    Defines the interface that should be presented by any installation frontend
    """
    def __init__(self, mod, **kwargs):
        super(IModInstaller, self).__init__(**kwargs)
        self._mod = mod
        self._mod_name = mod.moduleName.text

        self._mod_folder = None
        self._step_order = None

        # state tracker for installation process
        self._current = {
            "step": None,
            "group": None
        }


    # general mod properties
    @property
    def mod(self):
        return self._mod

    @mod.setter
    def mod(self, value):
        self._mod = value

    @property
    def mod_name(self):
        return self._mod_name

    @mod_name.setter
    def mod_name(self, value):
        self._mod_name = value

    @property
    def step_order(self):
        return self._step_order

    @step_order.setter
    def step_order(self, value):
        self._step_order = value

    # properties for access to the state handler
    @property
    def step(self):
        return self._current["step"]

    @step.setter
    def step(self, value):
        self._current["step"]=value

    @property
    def group(self):
        return self._current["group"]

    @group.setter
    def group(self, value):
        self._current["group"]=value

    ##============================
    ## some stuff
    ##============================
    # quit the installation process
    # @staticmethod
    def quitInstaller(self):
        import sys
        sys.exit(0)

    ##============================
    ##  Virtual methods
    ##============================

    def checkVisiblePattern(self):
        """
        Returns a value indicating whether the dependencies for
          the <visible> element in the current install step
          have been met, and thus whether the install step
          should be run (made visible) or skipped (hidden).
        Should return an affirmative value if the <visible>
          element does not exist for the current step.
        :return:
        """
        raise NotImplementedError

    def checkDependencyPattern(self, dependencies_container):
        """
        Checks whether an arbitrary list of dependencies
        has been met, according to the operator (either
        "And" or "Or") of the list's containing element.
        If the containing element does not have an operator
        attribute, it defaults to "And".
        :param dependencies_container: The element directly
         containing the sequence of "fileDependency",
         "flagDependency", etc... elements. Often is an
         element called "dependencies", but may not be
         (usually in the case where there is only one
         dependency in the list)
        :return:
        """
        raise NotImplementedError

    def setFlag(self, flag_name, flag_value):
        """
        Stores a value for the given flag
        :param flag_name:
        :param flag_value:
        """
        raise NotImplementedError

    def checkFlag(self, flag_name, value):
        """
        Returns a value indicating whether the specified
        flag matches the value given. Should return a
        negative (False) value if the flag has not been set,
        rather than raising an exception.
        :param flag_name:
        :param value:
        :return:
        """
        raise NotImplementedError

    def checkFileState(self, file_name, state) -> bool:
        """
        Returns a value indication whether the installation
        state of the specified file matches the value given
        for `state`.

        :param file_name: Name of the file to check
        :param state: Installation state to check. Possible values are 'Active', 'Inactive', 'Missing'
        :return:
        """
        raise NotImplementedError

    def markFileForInstall(self, file, file_type):
        """
        Add the given file to a list of files that have
          met installation requirements during the install
          process. After all install steps have been run,
          the files from this list should be copied
          to the user's mod-installation directory.

        :param file: object describing the file to install
        :param file_type: either "file" or "folder"
        :return:
        """
        raise NotImplementedError

    def InstallMod(self):
        pass


    # other
    def selectAny(self, *kwds):
        pass

    def selectExactlyOne(self, *kwds):
        pass

    def selectAtMostOne(self, *kwds):
        pass

    def selectAll(self, *kwds):
        pass

    def installFiles(self):
        pass



class InstallerBase(IModInstaller):
    """
    A Base implementation of an IModInstaller
    """
    def __init__(self, mod, **kwargs):
        super(InstallerBase, self).__init__(mod, **kwargs)
        # basic properties
        # self.mod = mod
        # self.mod_name = mod.moduleName.text
        self.mod_folder = None
        self._step_order = None

        self.queue = asyncio.Queue()


        # track flags set so far
        self.flags = {}
        self.files_to_install = []
        self.file_states = {}

    # def nextStep(self):
        

    async def plugin_handler(self, selection_type, plugin_list):
        print (selection_type, plugin_list)
        if selection_type == "SelectAny":
            return await self.selectAny(plugin_list)
        if selection_type ==    "SelectExactlyOne":
            return await self.selectExactlyOne(plugin_list),
        if selection_type == "SelectAtMostOne":
            return await self.selectAtMostOne(plugin_list),
        if selection_type == "SelectAll":
            return await self.selectAll(plugin_list)

    def results_received(self, results: list):
        pass



    # installer-independent logic

    def checkVisiblePattern(self) -> bool:
        # If there's no <visible> pattern, the step is always shown
        if not self.step.visible: return True

        # if there's just one dependency, there may not be a "dependencies" containing element
        if "dependencies" in self.step.visible:
            return self.checkDependencyPattern(self.step.visible.dependencies)
        else:
            return self.checkDependencyPattern(self.step.visible)

    def checkDependencyPattern(self, dependencies):
        # default to and
        if not dependencies.operator or dependencies.operator == "And":
            for dep in dependencies.fileDependency:
                if not self.checkFileState(dep.file, dep.state): return False
            for dep in dependencies.flagDependency:
                if not self.checkFlag(dep.flag, dep.value): return False
            return True

        elif dependencies.operator=="Or":
            for dep in dependencies.fileDependency:
                if self.checkFileState(dep.file, dep.state): return True
            for dep in dependencies.flagDependency:
                if self.checkFlag(dep.flag, dep.value): return True
            return False

        else:
            raise AttributeError("Unknown operator for dependencies list: {op}".format(op=dependencies.operator))

        # TODO: is there really a need to check game/fomm versions?

    def setFlag(self, flag_name: str, value: str):
        self.flags[flag_name] = value

    def checkFlag(self, flag: str, value: str) -> bool:
        if flag in self.flags:
            return self.flags[flag]==value
        # just return false if it hasn't been set
        return False

    def markFileForInstall(self, file, file_type: str):
        file.type = file_type
        self.files_to_install.append(file)

    def checkFileState(self, file, state) -> bool:
        if file in self.file_states:
            return self.file_states[file] == state
        return False
        # todo: implement file lookup



    def shouldShowPlugin(self, plugin):
            """
            :param plugin:
            :return: a value in "NotUsable", "Optional", "Required", ... that determines whether to display the plugin and how to mark it.
            """
            return self.checkTypeDescriptor(plugin.typeDescriptor)

    def checkTypeDescriptor(self, typeDescriptor):
        if "patterns" in typeDescriptor:

            for pat in typeDescriptor.patterns.pattern:
                if self.checkDependencyPattern(pat.dependencies):
                    # patterns checks successfully
                    if pat.type.name == "NotUsable":
                        return False
                else: # pattern check unsuccessful
                    if pat.type.name == "Required":
                        return False

            return typeDescriptor.defaultType.name != "NotUsable"
            # todo: have separate logic for Optional, Recommended, CouldBeUsable
        else:
            return typeDescriptor.type.name != "NotUsable"


    @staticmethod
    def isYesNo(plugin_list):
        return len(plugin_list)==2 \
            and plugin_list[0].name in ["Yes", "No"] \
            and plugin_list[1].name in ["Yes", "No"] \
            and plugin_list[0].name != plugin_list[1].name

    # methods to be overidden by subclasses




    def yesNo(self, *kwds):
        raise NotImplementedError


    # called at end of installer
    def installFiles(self):
        from operator import attrgetter
        self.files_to_install[:] = sorted(self.files_to_install, key=attrgetter('priority', 'source'))

        for f in self.files_to_install:
            print(f) #todo: actually install these things



    def verifyModDependencies(self):
        """
        Verifies that the mod's dependencies are installed
        correctly, and raises an exception if they aren't
        :return:
        """
        if self.mod.moduleDependencies:
            if not self.checkDependencyPattern(self.mod.moduleDependencies.dependencies):
                raise DependencyError("Mod dependencies not satisfied")

    def markRequiredFiles(self):
        """
        Automatically adds any files in the <requiredInstallFiles>
        element to the list of files to be installed.
        :return:
        """
        if self.mod.requiredInstallFiles:
            [self.markFileForInstall(f, ftype) for ftype, flist in self.mod.requiredInstallFiles.items() for f in flist]


    async def processGroup(self, group):
        self.group = group

        plugin_list = group.plugins.plugin

        # should return a list of plugins that were selected,
        # or None if no plugins were selected
        # fixme: must be async/threaded
        self.plugin_handler(group.type, plugin_list)

        results = await self.queue.get()

        if results:
            for selected_plugin in results:
                # set necessary flags
                if selected_plugin.conditionFlags:
                    [self.setFlag(flag.name, flag.text) for flag in selected_plugin.conditionFlags.flag]

                # mark designated files for installation
                if selected_plugin.files:
                    [self.markFileForInstall(file, ftype) for ftype, flist in selected_plugin.files.items() for file in flist]


    async def runInstallSteps(self):
        for step in self.mod.installSteps.installStep:
            self.step = step
            if not self.checkVisiblePattern():
                continue

            for group in step.optionalFileGroups.group:
                await self.processGroup(group)

    def processConditionalInstalls(self, cfi):
        if "patterns" in cfi:
            for pat in cfi.patterns.pattern:
                if self.checkDependencyPattern(pat.dependencies):
                    [self.markFileForInstall(f, ftype) for ftype, flist in pat.files.items() for f in flist]

    async def InstallMod(self):
        """
        Entry point for the main installation loop.
        Will be first thing called after installer is chosen
        """

        ## Step 1 ##
        # todo: handle mod name

        ## Step 2 ##
        # todo: handle mod image


        ## Step 3 ##
        # mod dependencies
        try:
            self.verifyModDependencies()
        except DependencyError:
            pass
            # todo: handle showing a message box or something

        ## Step 4 ##
        # mark requiredInstallFiles for install
        self.markRequiredFiles()

        ## Step 5 ##
        # Process install steps
        if self.mod.installSteps:
            self.step_order = self.mod.installSteps.order
            await self.runInstallSteps()


        ## Step 6 ##
        # conditional file installs
        if self.mod.conditionalFileInstalls:
            self.processConditionalInstalls(self.mod.conditionalFileInstalls)

        ## Step 7 ##
        # Install finalized list of files
        self.installFiles()








