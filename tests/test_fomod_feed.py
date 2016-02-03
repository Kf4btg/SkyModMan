from skymodman.fomod.untangler2 import FomodServer
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
def fomod_client(display):
    """

    :param display: 'client' generator-consumer that will request values from the server and feed them to the display.
    """
    while True:
        try:
            # first thing to do is wait for the mod name
            modname = yield
            display.send(("moduleName", modname))

            for a in ["position", "colour"]:
                val = yield from _send_cmd("@", a) # send attr request

                if val is None:
                    val = DEFAULTS["moduleName"][a]

                display.send("moduleName", a,
                             _convert_attr("moduleName", a, val))


        except GeneratorExit:
            display.close()
            return

# each command is a command-char followed by an element or attribute name
cmd_doc = {
    "Selectors":{
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

    "Suffixes": { # (add after name, eg '.elname?')

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

script = {
    "main": ("#moduleName",
                 '@position',
                 '@colour',

             'moduleImage',
                 '@showImage',
                 '@showFade',
                 '@height',

             'moduleDependencies?',
                '!dependencies',

             'requiredInstallFiles?',
                '.files?',
                '!files',

             '/installSteps?',
                '@order',
                ".installStep*",
                    '!installsteps',
             
             '/conditionalFileInstalls?',
                 '.patterns',
                    '.pattern*',
                        '!pattern'
             ),

    "dependencies": ('.dependencies?',
                         '@operator',
                     '.fileDependency*',
                         '@file',
                         '@state',
                     'flagDependency*',
                         '@flag',
                         '@value',
                     'gameDependency?',
                         '@version',
                     'fommDependency?',
                         '@version',
                     ),

    "files": ('.file*',
                '!file_attrs',
              'folder*',
                '!file_attrs'
              ),

    "file_attrs": ('@source',
                   '@destination',
                   '@alwaysInstall',
                   '@installIfUsable',
                   '@priority',
                   ),
    "installstep": (
        ".visible?",
            "!dependencies$",
            "&dependencies",
        ".optionalFileGroups?",
            ".group*",
                "!group",
    ),
    "group": (
        "@name",
        "@type",
        ".plugins?",
            "@order",
            ".plugin*",
                "!plugin"
    ),
    "plugin": (
        "@name",
        "#description",
        "image",
            '@path',
        "conditionFlags?",
            ".flag*",
                "@name",
                "#",
        "/files?",
            "!files",
        "/typeDescriptor",
            "!typedescriptor"
    ),
    "typedescriptor": (
        ".type|",
            "@name",
        "|dependencyType",
            "@name",
            ".defaultType",
                "@aname",
            'patterns',
                ".pattern",
                    '!pattern'
    ),
    "pattern": (
        ".type",
           "@name",
        "!dependencies",
        "/files?",
            "!file"
    )

}
















def _send_cmd(cmd, request=None):
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





