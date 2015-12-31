from lxml import objectify
from fomod import Fomod
from fomod.elements import ModName, DependencyList, DependencyType, FileList, InstallSteps, ModImage, Pattern, DTPattern, Group, Plugin
from fomod.enums import *


def lxmlParse(xml) -> Fomod:
    config = objectify.parse(xml).getroot()

    # initialize FOMOD instance
    fomod = Fomod()

    #==========================
    # ModuleName
    #==========================
    fomod.module_name = ModName(config.moduleName.text, Position(config.moduleName.get("position")), config.moduleName.get("colour") or "000000")

    #==========================
    # ModuleImage
    #==========================
    if config.find("moduleImage") is not None:
        el =  config.moduleImage
        mi_path = el.get("path") or "screenshot.png"

        # =True if absent
        mi_show_image = (el.get("showImage") is None) or el.get("showImage").pyvalue
        mi_show_fade = (el.get("showFade") is None) or el.get("showFade").pyvalue

        mi_height = -1 \
            if el.get("height") is None \
            else el.get("height").pyvalue

        fomod.module_image = ModImage(mi_path, mi_show_image, mi_show_fade, mi_height)

    #==========================
    # Required Install Files
    #==========================
    fomod.required_install_files = buildFileList(config.requiredInstallFiles)

    #==========================
    # Mod Dependencies
    #==========================
    fomod.module_dependencies = \
            DependencyList(config.moduleDependencies.dependencies) \
            if config.find("moduleDependencies/dependencies") \
            else None

    #==========================
    # Install Steps
    #==========================
    fomod.install_steps = buildInstallSteps(config.installSteps) \
        if config.find("installSteps/installStep") is not None \
        else None

    #==========================
    # Conditional File Installs
    #==========================
    fomod.conditional_file_installs = \
        [buildPattern(p) for p in config.conditionalFileInstalls.patterns.pattern] \
        if config.find("conditionalFileInstalls/patterns/pattern") is not None \
        else None

    return fomod

def buildFileList(files_element: objectify.ObjectifiedElement) -> FileList:
    """
    Parse a list of file or folder elements and return a FileList
    object containing each element as a FileSystemObject
    :param files_element:
    :return:
    """
    if files_element.countchildren() > 0:
        fl = FileList()

        for f in files_element.iterchildren():
            if f.tag in ["file", "folder"]:
                fl.add(f.tag, **dict(f.items()))
        return fl
    return None


def buildInstallSteps(steps_element: objectify.ObjectifiedElement) -> InstallSteps:
    """
    Construct the list of Installation Steps
    :param steps_element:
    :return:
    """
    isteps = InstallSteps(Order(steps_element.get("order"))) #TODO: handle the different orders appropriately

    for step in steps_element.installStep:
        step_name = step.get("name")

        ofg = [] #optionalFileGroups
        if step.find("optionalFileGroups/group") is not None: #means this element and at least one child exist
            for g in step.optionalFileGroups.group:
                ofg.append(buildGroup(g))

        if step.find("visible/dependencies") is not None:
            visible = buildDependencyList(step.visible.dependencies)
        else:
            visible = None

        # Adds an InstallStep instance to the list of steps with these properties
        isteps.addStep(step_name, visible=visible, optional_file_groups=ofg)

    return isteps


def buildGroup(el_group: objectify.ObjectifiedElement):
    """
    Parse and construct a member of an InstallStep's optional_file_groups
    :param el_group:
    :return: fomod.group.Group object
    """
    group = Group(name         = el_group.get("name"),
                  group_type   = GroupType(el_group.get("type")),
                  plugin_order = Order(el_group.plugins.get("order")))

    for el_plug in el_group.plugins.plugin:
        group.addPlugin(buildPlugin(el_plug))

    return group

def buildPlugin(plugin_element: objectify.ObjectifiedElement) -> Plugin:
    """
    Parse and construct a plugin contained by an optionalFileGroup

    Note: a "plugin" often appears in a manager as a Radio Button or Checkbox
    that allows the user to choose whether they want to install a part of the mod,
    or may allow them to answer yes or no to a question regarding their current setup.
    In this case, the "Yes" and "No" buttons would be separate plugins, each defining
    flags to set or files to install if the user chooses that option. Look to the GroupType
    to determine how many plugins may be chosen on a single page (install step/group)

    It may even just be a "noop" that there's to show a welcome/credits/warning/etc.
    page to the user.

    There are likely other possibilities, as well
    :param plugin_element:
    :return:
    """
    try:
        type_name = plugin_element.typeDescriptor.type.get("name")
        type_descriptor = PluginType(type_name)
    except AttributeError:
        # typeDescriptor has no "type" attribute:
        # that means this is a complex dependency type

        # grab dependencyType element
        el_dtype = plugin_element.typeDescriptor.dependencyType

        # initialize the instance
        type_descriptor = DependencyType(PluginType(el_dtype.defaultType.get("name")))

        # add patterns to the descriptor instance
        # TODO: maybe pass a list comprehension as an argument to the DependencyType constructor?
        for el_pattern in el_dtype.patterns.pattern:
            type_descriptor.addPattern(buildDepTypePattern(el_pattern))

    # get the image to be displayed, if any
    image = plugin_element.image.get("path") if plugin_element.find("image") is not None else None

    flags = {} #flags to set if this plugin is activated
    if plugin_element.find("conditionFlags/flag") is not None:
        for flag in plugin_element.conditionFlags.flag:
            flags[flag.get("name")] = flag.text

    # files to install if plugin activated
    files = buildFileList(plugin_element.files) if plugin_element.find("files") is not None else None

    return Plugin(plugin_element.get("name"), plugin_element.description.text, type_descriptor, image, files, flags)

def buildDependencyList(deps_element: objectify.ObjectifiedElement) -> DependencyList:
    assert deps_element.tag == "dependencies"
    # dl = _recorder("DependencyList")

    # because isinstance(fomod.enums.FallbackEnum, Operator),
    # a missing "operator" attribute on the dependencies
    # xml attribute should return the default value of
    # Operator.AND (i.e. the attempt to lookup Operator(None)
    # should fail and fallback to returning Operator("And"))
    dl = DependencyList(Operator(deps_element.get("operator")))

    for dep in deps_element.iterchildren():
        dl.addDependency(dep.tag, **dict(dep.items()))

    return dl

def buildPattern(pattern_element: objectify.ObjectifiedElement) -> Pattern:
    base_dl = buildDependencyList(pattern_element.dependencies)
    base_fl = buildFileList(pattern_element.files) \
        if pattern_element.find("files") is not None \
        else None

    return Pattern(base_dl.operator, base_dl.dependencies, None if base_fl is None else base_fl.fileObjects)

def buildDepTypePattern(pattern_element: objectify.ObjectifiedElement) -> DTPattern:
    base_dl = buildDependencyList(pattern_element.dependencies)
    base_fl = buildFileList(pattern_element.files) \
        if pattern_element.find("files") is not None \
        else None

    return DTPattern(pattern_element.type.get("name"), base_dl.operator,
                     base_dl.dependencies, None if base_fl is None else base_fl.fileObjects )