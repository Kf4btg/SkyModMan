from ..enums import PluginType
from .filelist import FileList
from io import StringIO
from pprint import pprint

class Plugin:
    """
    A mod plugin belonging to a group.
    """
    def __init__(self, name: str, description: str, type_descriptor, image: str=None, files: FileList=None, flags: dict=None):
        """

        :param name: The name of the plugin.
        :param description: A textual description of the plugin.
        :param type_descriptor: Describes the type of the plugin; Can be a simple PluginType value or a complex DependencyType
        :param image: Path to the optional image associated with a plugin.
        :param files: The list of files and folders that need to be installed for the plugin.
        :param flags: The list of condition flags to set if the plugin is in the appropriate state.
        """
        self._name = name
        self._description = description
        self._image = image
        self._type = type_descriptor

        self._flags = dict() if flags is None else flags
        self._files = FileList() if files is None else files


    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return self._description

    @property
    def image(self) -> str:
        return self._image

    @property
    def flags(self) -> dict:
        return self._flags

    @property
    def files(self) -> FileList:
        return self._files

    @property
    def typeDescriptor(self):
        return self._type

    def addConditionFlag(self, name: str, value: str):
        self.flags[name]=value

    def addFile(self, tag: str, **kwargs):
        self._files.add(tag, **kwargs)

    def __repr__(self):
        sio = StringIO()
        pprint(self.__dict__, sio)
        return sio.getvalue()