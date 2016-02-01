import xmltodict
from addict import Dict
import re

atmatch=re.compile('[@#]')

def dictParse(xml_file) -> Dict:
    """
    Parse the fomod ModuleConfig.xml file into an addict.Dict, thus making all elements
    and properties accessible by attrubute access (e.g. config.moduleName.position)
    :param xml_file:
    :return:
    """
    xdict = xmltodict.parse(xml_file)

    adict = Dict(xdict)

    processAttributes(adict)

    return adict

def checkElement(container, key, value):

    if value is None: return

    if key=="config":
        processModName(value)
        processModImage(value)

    elif key in ["group", "plugin", "flagDependency", "fileDependency", "flag"] and isinstance(value, Dict):
        # make sure we can always treat these items as lists
        container[key]=[value]

    elif key=="dependencies" and "operator" not in value:
        value.operator = "And"
    elif key in ["file", "folder"]:
        container[key]=[value]
        processFileItem(container[key])
    elif key in ["plugins", "installSteps"]:
        if "order" not in value:
            value.order = "Ascending"

def checkElementList(key, value):
    if value is None: return

    if key in ["file", "folder"]:
        processFileItem(value)


def processAttributes(adict: Dict):
    """
    Recursively remove the '@' from the attribute names of items in the Dict
    and the '#' from the key '#text' that describes the element's text value
    :param adict:
    :return:
    """
    for k,v in adict.items():
        # i thought it made sense to put this after the other
        # two checks, but some keys were being arbitrarily
        # skipped (i.e. different keys were missed each time)
        if atmatch.match(k):
            newkey = k[1:]
            adict[newkey]=v
            del adict[k]
        if isinstance(v, Dict):
            processAttributes(v)
            checkElement(adict, k,v)

        elif isinstance(v, list):
            for d in v:
                processAttributes(d)
                checkElementList(k, d)

def processModName(config: Dict):
    if isinstance(config.moduleName, str):
        name = config.moduleName
        config.moduleName=Dict()
        config.moduleName.text=name
        config.moduleName.position="Left"
        config.moduleName.colour="000000"
    else:
        if "position" not in config.moduleName:
            config.moduleName.position="Left"
        if "colour" not in config.moduleName:
            config.moduleName.colour="000000"

def processModImage(config: Dict):
    if "moduleImage" in config:
        mi=config.moduleImage

        if "path" not in mi: mi.path = "screenshot.png"

        mi.showImage = "showImage" not in mi or mi.showImage == "True"
        mi.showFade = "showFade" not in mi or mi.showFade == "True"

        mi.height = int(mi.height) if "height" in mi else -1

    else:
        config.moduleImage.path = "screenshot.png"
        config.moduleImage.showImage = True
        config.moduleImage.showFade = True
        config.moduleImage.height = -1

def processFileItem(file_item):
    if isinstance(file_item, list):
        flist = file_item
    else:
        flist = [file_item]
    for fitem in flist:
        if "destination" not in fitem:
            fitem.destination = fitem.source

        fitem.priority = int(fitem.priority) if "priority" in fitem else 0

        # default = False
        fitem.alwaysInstall = "alwaysInstall" in fitem and fitem.alwaysInstall == "True"
        fitem.installIfUsable = "installIfUsable" in fitem and fitem.installIfUsable == "True"

# def processDependencyList(deplist: Dict):
#     if "operator" not in deplist:
#         deplist.operator = "And"


if __name__ == '__main__':
    from pprint import pprint
    with open("res/SMIM/ModuleConfig.xml", "rb") as f:
        c=dictParse(f).config

    pprint(c)
