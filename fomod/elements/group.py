from ..enums import GroupType, Order
from .plugin import Plugin
from io import StringIO
from pprint import pprint

class Group:
    """
    A group of plugins.
    """
    def __init__(self, name: str, group_type: GroupType, plugin_order: Order = Order.ASC):
        """

        :param name: The name of the group.
        :param group_type: The type of the group, describing how plugins can/must be selected
        :param plugin_order: The order by which to list the plugins.
        :return:
        """
        self._name = name
        self._type = group_type
        self._order = plugin_order
        self._plugins = []

    @property
    def plugins(self) -> list:
        return self._plugins

    @plugins.setter
    def plugins(self, plugins):
        assert isinstance(plugins, list)
        self._plugins = plugins

    @property
    def name(self) -> str:
        return self._name

    @property
    def type(self) -> GroupType:
        return self._type

    @property
    def plugin_order(self) -> Order:
        return self._order

    def addPlugin(self, plugin: Plugin):
        """
        :param plugin: fully-constructed plugin to add to this group
        """
        assert isinstance(plugin, Plugin)
        self._plugins.append(plugin)

    # def __str__(self):
    #     d = {"name": self._name, "type": self._type, "order": self._order, "Plugins": self._plugins}
    #
    #     sio = StringIO()
    #     pprint(d, sio)
    #     return sio.getvalue()
    #
    # def __repr__(self):
    #     return str(self)

    def __repr__(self):
        sio = StringIO()
        pprint(self.__dict__, sio, indent=4)
        return sio.getvalue()