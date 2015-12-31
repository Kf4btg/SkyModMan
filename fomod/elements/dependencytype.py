from ..enums import PluginType
from .pattern import DTPattern
from io import StringIO
from pprint import pprint

class DependencyType:
    def __init__(self, defaultType: PluginType, patterns:list=None):
        """
        :param defaultType: The default type of the plugin used if none of the specified dependency states are satisfied
        :param patterns: The list of dependency patterns against which to match the user's installation. The first pattern that matches the user's installation determines the type of the plugin.
        """
        self._defType = defaultType
        if patterns is not None:
            self._patterns = patterns
        else:
            self._patterns = []

    @property
    def defaultType(self) -> PluginType:
        return self._defType

    @property
    def patterns(self) -> list:
        return self._patterns

    @patterns.setter
    def patterns(self, value: list):
        assert isinstance(value, list)
        self._patterns = value

    def addPattern(self, pattern: DTPattern):
        assert isinstance(pattern, DTPattern)
        self._patterns.append(pattern)

    def __repr__(self):
        sio = StringIO()
        pprint(self.__dict__, sio)
        return sio.getvalue()