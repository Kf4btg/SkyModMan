from skymodman.fomod.untangler2 import FomodFeed
from contextlib import wraps
from skymodman.utils.color import Color

# consumer decorator basically copied from https://www.python.org/dev/peps/pep-0342/
def consumer(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        gen = func(*args, **kwargs)
        next(gen)
        return gen
    return wrapper


@consumer
def fomod_receiver(display):
    """

    :param display: secondary consumer that will display the values to the user.
    """
    while True:
        try:
            # first thing to do is wait for the mod name
            modname = yield
            display.send(("moduleName", modname))

            for a in ["position", "colour"]:
                val = yield from _yield_cmd("@", a)
                if val is None:
                    val = DEFAULTS["moduleName"][a]
                display.send("moduleName", a,
                             _convert_attr("moduleName", a, val))


        except GeneratorExit:
            display.close()
            return


def _yield_cmd(cmd, request=None):
    yield cmd
    if request is not None:
        response = yield request
        return response

def _convert_attr(element_name, attrname, value):
    """
    If the attribute is listed in the conversions dict, return the converted value; otherwise just return the value unchanged.
    :param element_name:
    :param attrname:
    :param value:
    :return:
    """
    try:
        return DEFAULTTYPES[element_name][attrname](value)
    except AttributeError:
        return value

@consumer
def dummy_display():
    while 1:
        try:
            value = yield
            print(value)
        except GeneratorExit:
            return





# <editor-fold desc="defaults">
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
# </editor-fold>





