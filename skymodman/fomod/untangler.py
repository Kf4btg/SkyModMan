from skymodman.thirdparty.untangle import untangle
# from skymodman.managers import modmanager as Manager

class Element(untangle.Element):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # part of a hack to prevent empty lines from filling up all
        # the 'cdata' attributes
        self.prev2=""
        self.prev1=""

    def get_attribute(self, key, default=None):
        value = super().get_attribute(key)

        return default if value is None else value

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


class Fomodder:
    def __init__(self, config_xml):
        self.fomod_config = untangle.parse(config_xml)
        print(type(self.fomod_config.config))

    @property
    def root(self):
        return self.fomod_config.config

    def steps(self):
        """
        This is the workhorse of the class. It is a generator that yields the values from the fomod config xml in order, allowing the handler to deal with the value as needed before moving on to the next step.
        :return:
        """

        ## Step1: ModName
        yield from _next(self.root.moduleName, cdata=True, **DEFAULTS["moduleName"])

        ## step 2: modimage
        for el in self.root.get_elements("moduleImage"):
            yield from _next(el, **DEFAULTS["moduleImage"])
            break
        else:
            # fake it up
            yield "moduleImage"
            yield from (DEFAULTS["moduleImage"][a]
                        for a in ["path", "showImage",
                                  "showFade", "height"])

        ## step3: module Dependencies
        for el in self.root.get_elements("moduleDependencies"):
            yield from _moduledependencies(el)
            break

        ## step4: requiredInstallFiles
        for el in self.root.get_elements("requiredInstallFiles"):
            if len(el): yield from _files(el)
            break

        ## step5: installSteps
        for el in self.root.get_elements("installSteps"):
            if len(el): _installsteps(el)
            break

        ## step6: conditionalFileInstalls
        for el in self.root.get_elements("conditionalFileInstalls"):
            if len(el):
                yield from _patterns(el.patterns)





def _next(element, *attrs, cdata=False, **attr_default_pairs):
    """

    :param element: the element
    :param attrs_using_DEFAULTS: anything listed here will first be queried in the element, then in the DEFAULTS dict if not found
    :param attrs: should just be a plain iterable of attribute names to be looked up in the element. Will return ``None`` if not found.
    :param cdata: Whether to return the cdata for this element
    :param attr_default_pairs: any kwargs other than `attrs` and `cdata` will be taken as an attribute to look up in the element, and if not found the value given in the kwarg will be used as the default return value.
    :return:
    """
    yield element.name

    if cdata: yield element.cdata

    yield from (element.get_attribute(a) for a in attrs)

    yield from (element.get_attribute(a,d) for a,d in attr_default_pairs.items())



def _moduledependencies(moddeps):
    # Need to check whether:
    #  A) modDeps ele has a 'dependencies' subelement, or
    #  B) the dependencies are placed directly below it
    #      (this seems to happen sometimes, though usually it's if there's only 1 dependency)

    for el in moddeps.get_elements("dependencies"):
        yield moddeps._name
        yield from _dependencies(el)
        break
    else:
        # yield directly from this element
        yield from _dependencies(moddeps)

def _dependencies(element):
    # yields the element name (e.g."dependencies", our 'announcement')
    # and the value/default-value for the operator
    yield from _next(element, **DEFAULTS["dependencies"])

    # dict {type:[deps-of-type...], ...}
    # if there are no deps of that type, its list will be empty
    dependencies = {dt:element.get_elements(dt) for dt in dep_types}

    for dt in dep_types:
        yield from (_next(dep, attrs=attrs_for_deps[dt])
                    for dep in dependencies[dt])

def _files(element):
    yield element._name # the container

    for fstype in ["file", "folder"]:
        yield from (
            _next(f, "source", **DEFAULTS[fstype])
            for f in element.get_elements(fstype))

def _installsteps(steps_element):
    yield from _next(steps_element, **DEFAULTS["installSteps"])

    for step in steps_element.get_elements("installStep"):
        yield from _next(step, "name")

        ## check visible dep group
        for vis in step.get_elements("visible"):
            for deps in vis.get_elements("dependencies"):
                yield vis._name
                yield from _dependencies(deps)
                break
            else:
                yield from _dependencies(vis)

            # signals that we need a decision from controller;
            # controller needs to have analyzed the dependencies and
            # determined whether they were satisfied; if so, we will
            # continue to process this step. If not, we move to the next.
            # Controller must send() the result to the generator
            do_step = yield None
            break
        else:
            # always run step if there is no visible check
            do_step = True

        if do_step:
            for group in step.optionalFileGroups.group:
                _group(group)

def _group(group):
    yield from _next(group, "name", "type")

    yield from _next(group.plugins, **DEFAULTS["plugins"])

    for plugin in group.plugins.plugin:
        yield from _next(plugin, "name")

        yield from _next(plugin.description, cdata=True)

        for el in plugin.get_elements("image"):
            yield from _next(el, "path")

        for el in plugin.get_elements("conditionFlags"):
            yield el._name
            yield from (_next(flag, "name", cdata=True)
                        for flag in el.get_elements("flag"))

        for el in plugin.get_elements("files"):
            yield from _files(el)

        yield from _typedescriptor(plugin.typeDescriptor)


def _typedescriptor(descriptor):
    yield descriptor._name

    for simpletype in descriptor.get_elements("type"):
        yield from _next(simpletype, "name")
        break
    else:
        for dtype in descriptor.get_elements("dependencyType"):
            yield dtype._name

            yield from _next(dtype.defaultType, "name")

            yield from _patterns(dtype.patterns)


def _patterns(patterns):
    yield patterns._name

    for pattern in patterns.get_elements("pattern"):
        yield pattern._name
        yield from _next(pattern.type, "name")

        # there should never be any "loose" dependencies in here
        yield from _dependencies(pattern.dependencies)

        for f in pattern.get_elements("files"):
            yield from _files(f)
            break


# default values for various attributes
DEFAULTS={
    "moduleName": {
        "position": "RightOfImage",
        "colour": "000000"
    },
    "moduleImage": {
        "path": "screenshot",
        "showImage": True,
        "showFade": True,
        "height": -1,
    },
    "installSteps": {
        "order": "Ascending"
    },
    "file": {
        "destination": "", # same as source
        "alwaysInstall": False,
        "installIfUsable": False,
        "priority": 0
    },
    "dependencies": {
        "operator": "And"
    }
}

# some extra things that are duplicates
DEFAULTS["plugins"] = DEFAULTS["installSteps"]
DEFAULTS["folder"] = DEFAULTS["file"]

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