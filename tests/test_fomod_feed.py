from skymodman.fomod.untangler2 import FomodServer, fomodcommon
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
def dummy_display():
    while 1:
        try:
            value = yield
            print(value)
        except GeneratorExit:
            return


commands = fomodcommon.commands
suffixes = fomodcommon.suffixes

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

            # for a in ["position", "colour"]:
            #     val = yield from _send_cmd("@", a) # send attr request
            #
            #     if val is None:
            #         val = DEFAULTS["moduleName"][a]
            #
            #     display.send("moduleName", a,
            #                  _convert_attr("moduleName", a, val))


        except GeneratorExit:
            display.close()
            return

class FomodClient:

    def __init__(self, display, scripts_map, server):
        self.display = display
        self.scripts = scripts_map
        self.server = server
        self.controller_responses = {}

    def start(self):
        self.server.connect(self.run(self.scripts['main']))


    @consumer
    def run(self, script):
        state={
            "xorchain": None,
            "to_controller": None,
            "from_controller": None,
        }
        for cmd in script:
            action = self.check_cmd(cmd, state)
            if action is None or action is True: continue
            if action is False: break

            response = yield from action





    get_cmd_parts = (#name      cmd     suf
        lambda com: (com,       '~',    ' '),
        lambda com: (com[1:],   com[0], ' '),
        lambda com: (com[:-1],  '~',   com[:-1]),
        lambda com: (com[1:-1], com[0], com[:-1]),
    )

    def check_cmd(self, command:str, state):
        """Checks for client control-codes in `command`"""

        if not command: return None

        if len(command)==1:
            if command in "#/":
                return self.send_cmd("", command)

            return None #fixme: raise exception


        # 'bitmask' corresponding to an index in get_cmd_parts
        _ = (1 if command[0] in commands else 0) \
            + (2 if command[-1] in suffixes else 0)


        if not _: return self.send_cmd(command)

        name, c, s = self.get_cmd_parts[_](command)

        # if have both and cmd is runscript()
        if _ & 1|2 and c == "!":

            # run subscript
            # but command could possibly have $ suffix,
            # so check that first
            if s == "$":
                state["to_controller"] = name
            return self.run(self.scripts[name])

        # if we have explicit cmd char
        if _ & 1:

            if c == "!":  # run subscript
                return self.run(self.scripts[name])
            if c == '&': # return response from controller
                return state["from_controller"]

            # uf we've satisfied the check,
            if state['xorchain'] is True:

                # skip further | commands
                if c == "|":
                    return None

                # else: the chain has ended
                state["xorchain"] = None

        # if we have suffix
        if _ & 2 and s in "|$":

            # starting new xor chain
            if s == "|": state['xorchain'] = False

            # send this name to controller before next command
            if s == "$": state["to_controller"] = name

            # unset suffix b/c server doesn't care about these 2
            s = " "

        return self.send_cmd(name, c, s)


    def check_response(self, response, state):

        # todo: actually handle the response
        self.display.send(response)


    @staticmethod
    def send_cmd(name, command="~", suffix=" "):
        """
        yields a command to the server in two parts:
        the first part is is a two-character command string,
        consisting of the concatenation of the `command` and `suffix`
        (or their defaults).  Using this, the server will be prepare
        the appropriate operation and then request the `name`, which
        is the second and final value to be yielded by this generator.

        Name is yielded even if it is an empty string.

        :param name:
        :param command:
        :param suffix:
        :return:
        """
        yield (command, suffix, name)

    @staticmethod
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





# <editor-fold desc="install-script command outline">
installscript = {
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
            "!files"
    )

}
# </editor-fold>







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





