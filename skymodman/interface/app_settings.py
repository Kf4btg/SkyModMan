"""
A singleton manager for the QSettings-based application preferences.
"""

from functools import partial

from PyQt5.QtCore import QSettings #, QObject, pyqtSignal

from skymodman.interface.typedefs import QS_Property

_qs_org = "skymodman"
_qs_app = "skymodman"
_qs_group="ManagerWindow"

# _preferences = {}
# """Dict containing static application settings (e.g. toggleable booleans and other explicitly-set parameters)"""
#
# _properties = [] # type: list [QS_Property]
# """List of ``QS_Property`` objects containing all defined properties, with default values, accessor functions, and associated callbacks."""


# class _AppSettings(QObject):
class _AppSettings:

    # setting_changed = pyqtSignal(str)
    # """Emitted with the name of the preference that was just changed"""

    def __init__(self, *args, **kwargs):
        # super().__init__(*args, **kwargs)

        self.preferences = {}

        self.properties = [] # type: list [QS_Property]

    def get_pref_val(self, pref_name):
        """
        :param pref_name:
        :return: the current value of the named preference
        """
        return self.preferences[pref_name]

    def set_pref_val(self, pref_name, value):
        """
        Change the current value of a stored preference

        :param pref_name:
        :param value:
        """
        self.preferences[pref_name] = value
        # self.setting_changed.emit(pref_name)

    def read_wrapper(self, func, name, value):
        """
        Wraps a provide on_read callback with one that first sets the value in
        the preferences store
        :param str name:
        :param value:
        :param callable func:
        """
        self.preferences[name] = value
        func(value)

    def add(self, name, value=None, p_type=None,
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
            self.properties.append(
                QS_Property(p_type, name,
                            accessor=value,
                            on_read=on_read
                                if callable(on_read)
                                else (lambda t: None),
                            on_change=on_change
                                if callable(on_change)
                                else (lambda t: None)))
        else:
            if value is not None and p_type is None:
                p_type = type(value)

            # property is constant (stored when read and changed,
            # not read dynamically from app state)
            self.properties.append(
                QS_Property(p_type, name, default=value,
                            accessor=lambda: self.preferences[name],
                            on_read=partial(self.read_wrapper, on_read, name)
                                if callable(on_read)
                                else partial(self.set_pref_val, name),
                            on_change=on_change
                                if callable(on_change)
                                else (lambda t: None)
                           )
               )

    def read(self):
        """
        Read in the Qt settings from native storage
        """
        settings = QSettings(_qs_org, _qs_app)

        settings.beginGroup(_qs_group)

        for p in self.properties:
            if p.type is None:
                # read without the type parameter,
                # let PyQt attempt to convert automatically
                v = settings.value(p.name, p.default)
            else:
                v = settings.value(p.name, p.default, p.type)

            # call the on_read callback
            p.on_read(v)

        settings.endGroup()

    def write(self):
        """
        Write the current settings to native storage
        """
        settings = QSettings(_qs_org, _qs_app)
        settings.beginGroup(_qs_group)

        for p in self.properties:
            settings.setValue(p.name, p.accessor())

        settings.endGroup()


__instance = None

# use this to maintain the singleton pattern
def _instance():
    global __instance

    # if we've yet to create an instance, do it now
    if __instance is None:
        __instance = _AppSettings()

    # return the singleton instance
    return __instance

##=============================================
## Instance proxy methods
##=============================================

def Set(pref_name, value):
    """
    Change the current value of a stored preference

    :param pref_name:
    :param value:
    """
    _instance().set_pref_val(pref_name, value)

def _readwrapper(func, name, value):
    """
    Wraps a provide on_read callback with one that first sets the value in
    the preferences store
    :param name:
    :param value:
    :param func:
    """
    _instance().read_wrapper(func, name, value)

def Get(pref_name):
    """

    :param pref_name:
    :return: the current value of the named preference
    """
    return _instance().get_pref_val(pref_name)

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

    _instance().add(name, value, p_type, on_read, on_change)

def read():
    """
    Read in the Qt settings from native storage
    """
    _instance().read()


def write():
    """
    Write the current settings to native storage
    """
    _instance().write()


