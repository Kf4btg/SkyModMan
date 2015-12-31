from .dependencylist import DependencyList
from io import StringIO
from pprint import pprint

class InstallStep:
    """
    A step in the install process containing groups of optional plugins.
    """
    def __init__(self, name:str, visible: DependencyList=None, optional_file_groups: list = None):
        """
        :param name:  The name of the install step.
        :param visible:  The pattern against which to match the conditional flags and installed files. If the pattern is matched, then the install step will be visible.
        :param optional_file_groups: The list of optional files (or plugins) that may optionally be installed for this module
        """
        self._name = name
        self._visible = visible
        self._opt_file_groups = optional_file_groups

    @property
    def name(self) -> str:
        return self._name

    @name.setter
    def name(self, value:str):
        self._name = value

    @property
    def visible(self) -> DependencyList:
        return self._visible

    @visible.setter
    def visible(self, value: DependencyList):
        self._visible = value

    @property
    def optional_file_groups(self) -> list:
        return self._opt_file_groups

    @optional_file_groups.setter
    def optional_file_groups(self, value: list):
        assert isinstance(value, list)
        self._opt_file_groups = value

    def __repr__(self):
        sio = StringIO()
        pprint(self.__dict__, sio)
        return sio.getvalue()