from ..enums import Operator, PluginType
from .dependencylist import DependencyList
from .filelist import FileList
from io import StringIO
from pprint import pprint

class Pattern(DependencyList, FileList):
    """
    Conditional Install Pattern
    """
    def __init__(self, operator:Operator, dependencies:dict = None, file_items:list = None):
        """

        :param operator: Operator.AND or Operator.OR
        :param dependencies: allows construction of the instance from an existing DependencyList element; must be a dict with the format:
        {
            "fileDependency": [dict(str,str)...] or [],
            "flagDependency": [dict(str,str)...] or [],
            "gameDependency": [dict(str,str)...] or [],
            "fommDependency": [dict(str,str)...] or []
        }
        :param file_items: if provided, must be a list() of FileSystemObjects
        :return:
        """
        # super() is HAAAARRRRRDDDDDD!!!!!! so i didn't do it
        DependencyList.__init__(self, operator, dependencies)
        FileList.__init__(self, file_items)


    def __repr__(self):
        sio = StringIO()
        pprint(self.__dict__, sio)
        return sio.getvalue()

class DTPattern(Pattern):
    """
    Dependency Type Pattern
    """
    def __init__(self, plugin_type:PluginType, operator:Operator, dependencies:dict = None, file_items:list = None):
        Pattern.__init__(self, operator, dependencies, file_items)
        self._type = plugin_type

    @property
    def type(self) -> PluginType:
        return self._type

    def __repr__(self):
        sio = StringIO()
        pprint(self.__dict__, sio)
        return sio.getvalue()