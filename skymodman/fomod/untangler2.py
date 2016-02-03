from collections import deque

from skymodman.thirdparty.untangle import untangle
from skymodman.utils.color import Color
# from skymodman.managers import modmanager as Manager
from skymodman import exceptions

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



class fomodcommon:

    commands = r"/.#@|!&~"
    suffixes = r"?*|$"

    # <editor-fold desc="command documentation">
    # each command is a command-char followed by an element or attribute name
    cmd_doc = {
        "Selectors": {
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

        "Suffixes": {  # (add after name, eg '.elname?')

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
    # </editor-fold>

    class FomodError(exceptions.Error):
        pass

    class NoSuchElement(FomodError):
        """
        Indicates to the consumer that the element they requested does not exist.
        """
        pass

    class BadCommand(FomodError):
        """
        Indicates an unrecognized command was received
        """
        pass



class FomodServer:
    def __init__(self, config_xml):
        self.fomod_config = untangle.parse(config_xml)
        self.connected_client = None

    def connect(self, consumer):
        if self.connected_client is None:
            self.connected_client=consumer
            try:
                self.serve(consumer)
            finally:
                consumer.close()
                self.connected_client = None
        else:
            consumer.send(None) # says "I'm busy"




    # noinspection PyNoneFunctionAssignment
    def serve(self, consumer):
        """

        :param __generator consumer: Should be a generator equipped to receive send() commands from the feed. The values yielded by the generator will control the actions of the feeder.
        :return:
        """
        ancestors = deque()

        root = self.fomod_config.config # type: Element


        # this tracks the element hierarchy from root to the
        # current element, allowing us to step back up
        ancestors.append(root)
        # mod name is always first
        current = root.moduleName # type: Element

        # value = current.cdata
        command = consumer.send(current.cdata)
        while True:

            if command is None: # end
                break

            elif command == "@": # attributes
                requested = next(consumer)
                command = consumer.send(current[requested])

            elif command == "#": # cdata/text
                command = consumer.send(current.cdata)

            elif command == ".": # move to child element (single)
                requested = next(consumer)
                for el in current.get_elements(requested):
                    ancestors.append(current)
                    current = el
                    command = next(consumer)
                    break
                else:
                    command = consumer.throw(fomodcommon.NoSuchElement)




















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



# I don't know if this is the right way to do this...
# but it was the only way I could figure out (short of
# duplicating most of the code in untangle) to get untangle
# to use my Element subclass above

setattr(untangle, "_Element", untangle.Element)
setattr(untangle, "Element", Element)
# </editor-fold>
