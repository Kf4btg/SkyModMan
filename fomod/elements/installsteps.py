from ..enums import Order
from .step import InstallStep
from io import StringIO
from pprint import pprint

class InstallSteps:
    """
    A list of install steps for the mod

    Each step is A step in the install process containing groups of optional plugins.
    """
    def __init__(self, order:Order = Order.ASC):
        self._order = order
        self._steps = []

    @property
    def order(self) -> Order:
        return self._order

    @property
    def steps(self) -> list:
        return self._steps

    @steps.setter
    def steps(self, value):
        assert isinstance(value, list)
        self._steps = value

    def addStep(self, name, visible = None, optional_file_groups = None ):
        """
        Adds an InstallStep instance to the list of steps with the given properties

        :param name: step name
        :param visible: pattern which, if matched, determines whether or not this install step is displayed
        :param optional_file_groups: The list of optional files (or plugins) that may optionally be installed for this module
        """
        self.steps.append( InstallStep(name, visible, optional_file_groups))

    def __repr__(self):
        sio = StringIO()
        pprint(self.__dict__, sio)
        return sio.getvalue()