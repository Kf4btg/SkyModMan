from ..enums import Operator
from io import StringIO
from pprint import pprint

class DependencyList:
    """
    Contains a list of dependencies
    """
    # def __init__(self, deps_element):
    def __init__(self, operator = Operator.AND, dependencies:dict = None):
        """

        :param operator:
        :param dependencies: mainly allows construction of subclasses from an existing DependencyList element; must be a dict with the format:
        {
            "fileDependency": [dict(str,str)...] or [],
            "flagDependency": [dict(str,str)...] or [],
            "gameDependency": [dict(str,str)...] or [],
            "fommDependency": [dict(str,str)...] or []
        }
        :return:
        """

        # assert deps_element.tag == "dependencies"

        self._operator = operator #deps_element.get("operator") or "And"
        self._deps = {
            "fileDependency": [],
            "flagDependency": [],
            "gameDependency": [],
            "fommDependency": []
        } if dependencies is None else dependencies
        # for d in (deps_element.iterchildren()):
        #     self._deps[d.tag].append(dict(d.items()))

    @property
    def operator(self):
        return self._operator

    @property
    def dependencies(self):
        return self._deps

    def addDependency(self, dep_type: str, **kwargs):
        """
        :param dep_type: can be:
        'fileDependency' -- requires kwargs "file", "state"
        'flagDependency' -- requires kwargs "flag", "value"
        'gameDependency' -- requires kwarg "version"
        'fommDependency' -- requires kwarg "version"
        """

        self._deps[dep_type].append(kwargs)

    def __repr__(self):
        sio = StringIO()
        pprint(self.__dict__, sio)
        return sio.getvalue()

class Visible(DependencyList):
    """
    May be an element in an Install Step.
    The pattern against which to match the conditional flags and installed files.
    If the pattern is matched, then the install step will be visible.
    """
    # TODO: make accessible the final boolean result of the pattern matching
    pass