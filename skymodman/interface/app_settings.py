"""
A singleton manager for the QSettings-based application preferences.
"""

# from functools import partial

from PyQt5.QtCore import QSettings #, QObject, pyqtSignal

from skymodman.interface.typedefs import QS_Property

# the following values define how the qsettings will be stored on disk.
# e.g. on linux, it creates "$XDG_CONFIG_HOME/<Organization Name>/<Application Name>.ini",
# with INI section header(s) defined by the group name(s).

_qs_orgname = "skymodman"
_qs_appname = "skymodman"
_qs_group="ManagerWindow"

# So, for us this means "~/.config/skymodman/skymodman.ini"
# with a section labeled [ManagerWindow]

# _preferences = {}
# """Dict containing static application settings (e.g. toggleable booleans and other explicitly-set parameters)"""
#
# _properties = [] # type: list [QS_Property]
# """List of ``QS_Property`` objects containing all defined properties, with default values, accessor functions, and associated callbacks."""


class _AppSettings:

    def __init__(self):

        # some properties will have values read from the state of the
        # application itself. Others could be considered "preferences"
        # in that they have arbitrary values set by the user and need
        # to be stored somewhere in order to know their current value.
        # That place is here:
        self.preferences = {}
        """Dict containing static application settings (e.g. toggleable booleans and other explicitly-set parameters)"""

        # for properties that are not "preferences" to be stored in this
        # object, we only need to keep their value temporarily until
        # apply() is called.
        self.temp_store = {}

        self.properties = [] # type: list [QS_Property]
        """List of ``QS_Property`` objects containing all defined properties along with their default values, accessor functions, and associated callbacks."""

        # track if we've read in the setting data yet
        self._settings_read = False
        self._settings_applied = False

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

    # def _read_wrapper(self, func, name, value):
    #     """
    #     Wraps a provided on_read callback with one that first sets the value in
    #     the preferences store
    #     :param str name:
    #     :param value:
    #     :param callable func:
    #     """
    #     self.preferences[name] = value
    #     func(value)

    def _store_value(self, name, value):
        """
        Store the value for the given property in a appropriate
        container.

        If we know the name as one of our tracked preferences,
        (would have been initialized with a default value when
        the property was registered with ``add()``),
        update the `preferences` dict. Otherwise it should go in
        temporary storage until apply() is called.

        :param name: name of property
        :param value: value read from qsettings storage
        """
        if name in self.preferences:
            self.preferences[name] = value
        else:
            self.temp_store[name] = value

    def _retrieve_value(self, name):
        """
        Called from apply() to get the values that were read in from
        disk. After this is called, the temporary storage will be
        cleared

        :param name:
        :return: stored value
        """
        try:
            return self.preferences[name]
        except KeyError:
            return self.temp_store[name]

    def add(self, name, value=None, p_type=None,
            apply=None, on_change=None):
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
            when invoked. If a constant value is provided, the property
            will be considered a "user preference" and the data read in
            will be stored on the AppSettings object itself; it can be
            accessed using ``app_settings.Get("option_name")``.

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

        :param (T)->None apply: a callable may be provided here that
            will be invoked with the data read from native storage in
            order to apply the stored setting to the application.
            All properties will have their `apply` callback invoked
            when the main app_settings apply() method is executed.

        :param (T)->None on_change: currently unused
        """

        if callable(value):
            # no default, but read value from app when writing
            self.properties.append(
                QS_Property(p_type, name,
                            accessor=value,
                            apply=apply
                                if callable(apply)
                                else (lambda t: None),
                            on_change=on_change
                                if callable(on_change)
                                else (lambda t: None)))
        else:
            # property is constant (stored when read and changed,
            # not read dynamically from app state)

            # if `value` was provided but its type was not, have
            # python figure it out for us.
            if value is not None and p_type is None:
                p_type = type(value)

            # initialize the preference entry w/ the default value
            self.preferences[name] = value

            # almost the same as above, except the accessor is defined
            # as reading the value from the local prefs store
            self.properties.append(
                QS_Property(p_type, name, default=value,
                            accessor=lambda: self.preferences[name],

                            apply=apply if callable(apply)
                                else (lambda t: None),
                            on_change=on_change if callable(on_change)
                                else (lambda t: None))
                            # apply=partial(self._read_wrapper, apply, name)
                            #     if callable(apply)
                            #     else partial(self.set_pref_val, name),
                            # on_change=on_change
                            #     if callable(on_change)
                            #     else (lambda t: None))
               )

    def read(self):
        """
        Read in the Qt settings from native storage. They will not be
        applied here.
        """
        settings = QSettings(_qs_orgname, _qs_appname)

        settings.beginGroup(_qs_group)

        for p in self.properties:
            if p.type is None:
                # read without the type parameter,
                # let PyQt attempt to convert automatically
                v = settings.value(p.name, p.default)
            else:
                v = settings.value(p.name, p.default, p.type)

            # put the value someplace for safe keeping
            self._store_value(p.name, v)

        settings.endGroup()

        # record that we've successfully read in the stored settings
        self._settings_read = True


    def apply(self):
        """
        Call the apply() callback for all properties read in.
        """
        # don't try to apply if we haven't read anything in yet
        if self._settings_read:
            for p in self.properties:
                p.apply(self._retrieve_value(p.name))

            # now clear the temp storage
            self.temp_store.clear()
            # record that we've applied the settings
            self._settings_applied = True

    def write(self):
        """
        Write the current settings to native storage
        """

        # in the case where something went wrong between reading the
        # values in and applying them, self.temp_store will not be
        # empty, and the user probably doesn't want the previous
        # values overwritten.
        if self._settings_applied:

            settings = QSettings(_qs_orgname, _qs_appname)
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

def Get(pref_name):
    """

    :param pref_name:
    :return: the current value of the named preference
    """
    return _instance().get_pref_val(pref_name)

def add(name, value=None, p_type=None,
        apply=None, on_change=None):
    """
    Create a QSetting property (``QS_Property``) that will be properly
        read-from/saved-to QSettings native storage.

        Examples:
            * app_settings.add("restore_state", True, bool)
            * app_settings.add("size", self.size, apply=lambda s: self.resize(s))
                # where self.size() returns a QSize object

        :param str name: the label that will be used to store and refer
            to the setting

        :param T|()->T value: either the (constant) default value for
            the setting or a callable that returns the current value
            when invoked. If a constant value is provided, the property
            will be considered a "user preference" and the data read in
            will be stored on the AppSettings object itself; it can be
            accessed using ``app_settings.Get("option_name")``.

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

        :param (T)->None apply: a callable may be provided here that
            will be invoked with the data read from native storage in
            order to apply the stored setting to the application.
            All properties will have their `apply` callback invoked
            when the main app_settings apply() method is executed.

        :param (T)->None on_change: currently unused
    """

    _instance().add(name, value, p_type, apply, on_change)

def read():
    """
    Read in the Qt settings from native storage
    """
    _instance().read()

def apply_all():
    """
    Apply the settings that have been read in. Should be called after
    read()
    """
    _instance().apply()

def read_and_apply():
    """
    Read in the Qt settings from native storage and apply them to the
    application.
    """
    _instance().read()
    _instance().apply()


def write():
    """
    Write the current settings to native storage
    """
    _instance().write()


