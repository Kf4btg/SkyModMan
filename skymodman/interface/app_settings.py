"""
A singleton manager for the QSettings-based application preferences.
"""

from functools import partial

from PyQt5.QtCore import QSettings

class QS_Property:
    """
    Represents a value that will saved to and read from the QSettings storage
    """
    __slots__=("type", "name", "default", "accessor", "on_read", "on_change")

    def __init__(self, T, name, default=None, accessor=None, on_read=lambda t:None, on_change=lambda t:None):
        """
        :param type T:
        :param str name:
        :param T default:
        :param ()->T accessor:
        :param (T)->None on_read:
        :param (T)->None on_change:
        """

        self.type = T
        self.name = name
        self.default = default
        self.accessor = accessor
        self.on_read = on_read
        self.on_change = on_change

_qs_org = "skymodman"
_qs_app = "skymodman"
_qs_group="ManagerWindow"

_preferences = {}
"""Dict containing static application settings (e.g. toggleable booleans and other explicitly-set parameters)"""

# noinspection PyUnresolvedReferences
_properties = [] # type: list[QS_Property]
"""List of ``QS_Property`` objects containing all defined properties, with default values, accessor functions, and associated callbacks."""


def Set(pref_name, value):
    """
    Change the current value of a stored preference

    :param pref_name:
    :param value:
    """
    _preferences[pref_name] = value

def _readwrapper(func, name, value):
    """
    Wraps a provide on_read callback with one that first sets the value in
    the preferences store
    :param name:
    :param value:
    :param func:
    :return:
    """
    _preferences[name] = value
    func(value)

def Get(pref_name):
    """

    :param pref_name:
    :return: the current value of the named preference
    """
    return _preferences[pref_name]


def add(name, value=None, p_type=None,
        on_read=None, on_change=None):
    """
    Create a QSetting property (``QS_Property``) that will be properly
    read-from/saved-to QSettings native storage.

    Examples:
        * app_settings.add("restore_state", True, bool)
        * app_settings.add("size", self.size, on_read=lambda s: self.resize(s))
                # where self.size() returns a QSize object

    :param str name: the label that will be used to store and refer
        to the setting

    :param T|()->T value: either the (constant) default value for
        the setting or a callable that returns the current value
        when invoked.
    :param type p_type: python type of the value that will be
        stored. If `value` is a non-None constant and `p_type` is
        None, the type will be inferred from the type of `value`.
        If `value` is a callable that returns a Qt type (such as
        ``QSize``), this parameter may not be necessary as the type
        is usually encoded in the stored value and converted to
        that type automatically by PyQt when read.

        It is strongly recommended to provide this parameter if the
        data being stored is a non-string constant, as most
        settings will be read in as strings (e.g. saving ``True``
        will return "true" when read from storage).

    :param (T)->None on_read: called with the value read from
        native storage when the settings are first loaded. If
        `value` is a constant, the read value is first stored
        within the AppSettings (can be accessed using
        ``app_settings.Get("option_name")`` ) before the `on_read`
        callback--if any--is invoked.

    :param (T)->None on_change: currently unused
    """


    if callable(value):
        # no default, but read value from app when writing
        _properties.append(QS_Property(p_type, name,
                                      accessor=value,
                                      on_read=on_read if callable(on_read) else (lambda t: None),
                                      on_change=on_change if callable(on_read) else (lambda t: None)))
    else:
        if value is not None and p_type is None:
            p_type = type(value)

        # property is constant (stored when read and changed,
        # not read dynamically from app state)
        _properties.append(QS_Property(p_type,
                                       name,
                                       default=value,
                                       accessor=lambda: _preferences[name],
                                       on_read=partial(_readwrapper,
                                                       on_read,
                                                       name)
                                                if callable( on_read)
                                                else partial(Set, name),
                                       on_change=on_change
                                                if callable(on_change)
                                                else (lambda t: None)
                                       )
                           )


def read():
    """
    Read in the Qt settings from native storage
    """
    settings = QSettings(_qs_org, _qs_app)

    settings.beginGroup(_qs_group)

    for p in _properties:
        if p.type is None:
            # read without the type parameter,
            # let PyQt attempt to convert automatically
            v = settings.value(p.name, p.default)
        else:
            v = settings.value(p.name, p.default, p.type)

        # call the on_read callback
        p.on_read(v)

    settings.endGroup()


def write():
    """
    Write the current settings to native storage
    """
    settings = QSettings(_qs_org, _qs_app)
    settings.beginGroup(_qs_group)

    for p in _properties:
        settings.setValue(p.name, p.accessor())

    settings.endGroup()

# class AppSettings:
#     """
#     Basically a data-object that can be passed around the application and which contains combined UI and Manager settings.
#     """
#
#     def __init__(self, qs_org="skymodman", qs_app="skymodman", qs_group="ManagerWindow"):
#         self.org = qs_org
#         self.app = qs_app
#         self.group = qs_group
#
#         self.props = [] # type: list[QS_Property]
#
#         self.preferences = {}
#
#     def set(self, pref_name, value):
#         self.preferences[pref_name] = value
#
#     def __getitem__(self, item):
#         return self.preferences[item]
#
#     def get(self, pref_name):
#         return self.preferences[pref_name]
#
#     def add(self, name, value=None, p_type=None,
#             on_read=lambda t:None, on_change=lambda t:None):
#         """
#         Create a QSetting property that will be properly
#         read-from/saved-to QSettings native storage.
#
#         Examples:
#             * add("restore_state", True, bool)
#             * add("size", self.size, on_read=lambda s: self.resize(s))
#                     # where self.size() returns a QSize object
#
#         :param str name: the label that will be used to store and refer
#             to the setting
#
#         :param T|()->T value: either the (constant) default value for
#             the setting or a callable that returns the current value
#             when invoked.
#         :param type p_type: python type of the value that will be
#             stored. If `value` is a non-None constant and `p_type` is
#             None, the type will be inferred from the type of `value`.
#             If `value` is a callable that returns a Qt type (such as
#             ``QSize``), this parameter may not be necessary as the type
#             is usually encoded in the stored value and converted to
#             that type automatically by PyQt when read.
#
#             It is strongly recommended to provide this parameter if the
#             data being stored is a non-string constant, as most
#             settings will be read in as strings (e.g. saving ``True``
#             will return "true" when read from storage).
#
#         :param (T)->None on_read: called with the value read from
#             native storage when the settings are first loaded. If
#             `value` is a constant, this parameter is not used and
#             the read value is stored within the AppSettings instance
#             (can be accessed via item access, e.g.
#             ``my_settings["restore_state"]``).
#
#         :param (T)->None on_change: not currently used
#         """
#
#         if callable(value):
#             # no default, but read value from app when writing
#             self.props.append(QS_Property(p_type, name,
#                                           accessor=value,
#                                           on_read=on_read,
#                                           on_change=on_change))
#         else:
#             if value is not None and p_type is None:
#                 p_type = type(value)
#
#             # property is constant (stored when read and changed,
#             # not read dynamically from app state)
#             self.props.append(QS_Property(p_type, name,
#                                           default=value,
#                                           accessor=lambda: self.preferences[name],
#                                           on_read=lambda t: self.set(name, t),
#                                           on_change=on_change))
#
#     def read(self):
#         """
#         Read in the Qt settings from native storage
#         """
#         settings = QSettings(self.org, self.app)
#
#         settings.beginGroup(self.group)
#
#         for p in self.props:
#             if p.type is None:
#                 # read without the type parameter,
#                 # let PyQt attempt to convert automatically
#                 v = settings.value(p.name, p.default)
#             else:
#                 v = settings.value(p.name, p.default, p.type)
#
#             # call the on_read callback
#             p.on_read(v)
#
#         settings.endGroup()
#
#     def write(self):
#         """
#         Write the current settings to native storage
#         """
#         settings = QSettings(self.org, self.app)
#         settings.beginGroup(self.group)
#
#         for p in self.props:
#             settings.setValue(p.name, p.accessor())
#
#         settings.endGroup()







