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


class FomodFeed:
    def __init__(self, config_xml):
        self.fomod_config = untangle.parse(config_xml)

    # noinspection PyNoneFunctionAssignment
    def feeder(self, consumer):
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
                    command = consumer.throw(NoSuchElement)













class NoSuchElement(exceptions.Error):
    """
    Indicates to the consumer that the element they requested does not exist.
    """






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
