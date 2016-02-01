from skymodman.thirdparty.untangle import untangle
from skymodman.managers import modmanager as Manager

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

        # Step1: ModName

        # yield from self._modname(self.root.moduleName)
        yield from _next(self.root.moduleName, "position", "colour",
                         cdata=True)

        # step 2: modimage
        els=self.root.get_elements("moduleImage")
        if els:
            yield from _next(els[0],
                             "path", "showImage",
                             "showFade", "height")
        else:
            # fake it up
            yield "moduleImage"
            yield from (DEFAULTS["moduleImage"][a]
                        for a in ["path", "showImage",
                                  "showFade", "height"])

        # step3: module Dependencies
        yield from _moduledependencies(self.root)

        # step4: requiredInstallFiles
        els = self.root.get_elements("requiredInstallFiles")
        if els and len(els[0]):
            rif = els[0] #only 1

            yield rif._name

            for fstype in ["file", "folder"]:
                yield from (
                    _next(f,
                          "source",
                          "priority",
                          "destination",
                          "alwaysInstall",
                          "installIfUsable")
                    for f in rif.get_elements(fstype))

        # step5: installSteps
        els = self.root.get_elements("installSteps")
        if els and len(els[0]):
            _installsteps(els[0])



        # step6: conditionalFileInstalls



def _next(element, *attrs_using_DEFAULTS, attrs=None, cdata=False, **attr_default_pairs):
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

    yield from (default_attr(element, a) for a in attrs_using_DEFAULTS)

    yield from (element.get_attribute(a,d) for a,d in attr_default_pairs.items())


def _modulename(element:Element):
    # first, yield element name
    yield element.name

    #then, yield the text (mod name)
    yield element.cdata

    # yield the attributes, if any, as (name, value) tuples
    for a in ["position", "colour"]:
        yield default_attr(element, a)

def _moduledependencies(config):
    # Need to check that:
    #  1) moduleDependencies element exists
    #  2) it has a dependencies subelement
    #  3) dependencies subelement is not empty
    if hasattr(config, "moduleDependencies") \
        and hasattr(config.moduleDependencies, "dependencies") \
        and len(config.moduleDependencies.dependencies):

        yield config.moduleDependencies._name

        yield from _dependencies(config.moduleDependencies.dependencies)

attrs_for_deps={"fileDependency":["file", "state"],
           "flagDependency":["flag", "value"],
           "gameDependency":["version"],
           "fommDependency":["version"]}
dep_types = attrs_for_deps.keys()
def _dependencies(element):
    # yields the element name "dependencies" (our 'announcement')
    # and the value/default-value for the operator
    yield from _next(element, "operator")

    # dict {type:[deps-of-type...], ...}
    # if there are no deps of that type, its list will be empty
    dependencies = {dt:element.get_elements(dt) for dt in dep_types}

    for dt in dep_types:
        yield from (_next(dep, attrs=attrs_for_deps[dt])
                    for dep in dependencies[dt])

def _installsteps(steps_element):
    yield from _next(steps_element, "order")

    for step in steps_element.get_elements("installStep"):
        yield "whoaaaaa"







def default_attr(element, attrname):
    return element.get_attribute(
        attrname,
        DEFAULTS[element._name][attrname])






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





# I don't know if this is the right way to do this...
# but it was the only way I could figure out (short of
# duplicating most of the code in untangle) to get untangle
# to use my Element subclass above

setattr(untangle, "_Element", untangle.Element)
setattr(untangle, "Element", Element)