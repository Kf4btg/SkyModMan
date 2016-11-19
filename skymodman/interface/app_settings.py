"""
A singleton manager for the QSettings-based application preferences.

To set group (INI-section) names, the module-level ``init()`` method MUST
be called once (with the names of the groups as parameters) before
using any of the other methods.
"""

from collections import deque

from PyQt5.QtCore import QSettings #, QObject, pyqtSignal

from skymodman.interface.typedefs import QS_Property
from skymodman.log import withlogger

# the following values define how the qsettings will be stored on disk.
# e.g. on linux, it creates "$XDG_CONFIG_HOME/<Organization Name>/<Application Name>.ini",
# with INI section header(s) defined by the group name(s).

_qs_orgname = "skymodman"
_qs_appname = "skymodman"
# _qs_group="ManagerWindow"

# So, for us this means "~/.config/skymodman/skymodman.ini"
# with a section labeled [ManagerWindow]

# _preferences = {}
# """Dict containing static application settings (e.g. toggleable booleans and other explicitly-set parameters)"""
#
# _properties = [] # type: list [QS_Property]
# """List of ``QS_Property`` objects containing all defined properties, with default values, accessor functions, and associated callbacks."""

@withlogger
class _AppSettings:

    def __init__(self, *groups):

        self._groups = list(groups) # type: list [str]

        # some properties will have values read from the state of the
        # application itself. Others could be considered "preferences"
        # in that they have arbitrary values set by the user and need
        # to be stored somewhere in order to know their current value.
        # That place is here:
        self.preferences = {g:{} for g in self._groups}
        """Dict containing static application settings (e.g.
        toggleable booleans and other explicitly-set parameters) """

        self.MRUs = {g:{} for g in self._groups}

        # for properties that are not "preferences" to be stored in this
        # object, we only need to keep their value temporarily until
        # apply() is called.
        self.temp_store = {g:{} for g in self._groups}

        # List of ``QS_Property`` objects containing all defined
        # properties along with their default values, accessor
        # functions, and associated callbacks.
        self.properties = {g:[] for g in self._groups}
        """:type: dict[str, list[QS_Property]]"""

        # self.properties = [] # type: list [QS_Property]

        # track if we've read in the setting data yet
        self._settings_read = False
        self._settings_applied = False

    def get_pref_val(self, group, pref_name):
        """
        :param pref_name:
        :return: the current value of the named preference
        """
        try:

            if pref_name in self.preferences[group]:
                return self.preferences[group][pref_name]
            elif pref_name in self.MRUs[group]:
                # for MRUs, return the first value in the deque
                if self.MRUs[group][pref_name]:
                    return self.MRUs[group][pref_name][0]

                # if the MRU-list was empty, return None
                return None
            # otherwise, pref_name is not a known preference
            raise KeyError(pref_name)
        except KeyError as ke:
            self.LOGGER.error("KeyError when retrieving preference {0!r} from group {1!r}: {2}".format(pref_name, group, ke))
            return None


    def set_pref_val(self, group, pref_name, value):
        """
        Change the current value of a stored preference

        :param pref_name:
        :param value:
        """
        try:
            if pref_name in self.preferences[group]:
                self.preferences[group][pref_name] = value

            elif pref_name in self.MRUs[group]:
                d=self.MRUs[group][pref_name] # type: deque
                if value in d:
                    # don't add duplicate values:
                    # if the value already exists, remove it before
                    # adding it back to the beginning of the list
                    d.remove(value)
                # for MRUs, add to the beginning of the deque
                d.appendleft(value)

        except KeyError:
            self.LOGGER.error("Invalid app-settings group name: {0!r}".format(group))
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

    def add(self, group, name, value=None, p_type=None,
            apply=None, on_change=None):
        """
        Create a QSetting property (``QS_Property``) that will be properly
        read-from/saved-to QSettings native storage.

        Examples:
            * app_settings.add("restore_state", True, bool)
            * app_settings.add("size", self.size,
                               apply=lambda s: self.resize(s))
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

        assert group in self._groups

        # NOTE: `accessor` attribute is ONLY ever used when writing the value to disk

        if callable(value):
            # no default, but read value from app when writing
            self.properties[group].append(
                QS_Property(p_type, name,
                            accessor=value,
                            apply=apply
                                if callable(apply)
                                else None,
                            on_change=on_change
                                if callable(on_change)
                                else None))
        else:
            # property is constant (stored when read and changed,
            # not read dynamically from app state)

            # if `value` was provided but its type was not, have
            # python figure it out for us.
            if value is not None and p_type is None:
                p_type = type(value)

            # initialize the preference entry w/ the default value
            self.preferences[group][name] = value

            # almost the same as above, except the accessor is defined
            # as reading the value from the local prefs store
            self.properties[group].append(
                QS_Property(p_type, name, default=value,
                            accessor=lambda: self.preferences[group][name],

                            apply=apply if callable(apply) else None,
                            on_change=on_change if callable(on_change)
                                else None)
               )

    def add_mru(self, group, name, value=None, p_type=None,
            apply=None, on_change=None):
        """
        Special version of add() that creates Most-Recently-Used
        lists. For MRUs, Get() and Set() will return/assign the
        most-recently accessed value, respectively.

        If needing to simply store and retrieve a list as a value,
        the regular add() works just fine with sequence-types.

        :param group:
        :param name:
        :param value:
        :param p_type:
        :param apply:
        :param on_change:
        """

        assert group in self._groups

        if value is not None:
            value = deque(value, maxlen=10)
            if p_type is None:
                p_type = type(value[0])
        else:
            value = deque(maxlen=10)

        self.MRUs[group][name] = value

        self.properties[group].append(
            QS_Property(p_type, name,
                        # have to provide list to default and write()
                        # because QSettings doesn't seem to understand
                        # deques.
                        default=list(value),
                        accessor=lambda: list(self.MRUs[group][
                            name]),
                        apply=apply if callable(apply)
                            else None,
                        on_change=on_change if callable(on_change)
                            else None)
        )


    def read(self, groups=None):
        """
        Read in the Qt settings from native storage. They will not be
        applied here.
        """
        settings = QSettings(_qs_orgname, _qs_appname)

        if groups is None:
            groups = self._groups

        for group in groups:

            settings.beginGroup(group)

            # TODO: gracefully handle the stored value being of the wrong type (by doing something like overwriting the invalid value with the default value...ok maybe that's not so graceful, but at least it won't crash)

            for p in self.properties[group]:
                if p.type is None:
                    # read without the type parameter,
                    # let PyQt attempt to convert automatically
                    v = settings.value(p.name, p.default)
                else:
                    v = settings.value(p.name, p.default, p.type)

                # put the value someplace for safe keeping
                self._store_value(group, p.name, v)

            settings.endGroup()

        # record that we've successfully read in the stored settings
        self._settings_read = True

    def _store_value(self, group, name, value):
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
        if name in self.preferences[group]:
            self.preferences[group][name] = value
        elif name in self.MRUs[group]:
            self.MRUs[group][name] = deque(value, maxlen=10)
        else:
            self.temp_store[group][name] = value


    def apply(self, groups=None):
        """
        Call the apply() callback for all properties read in.
        """

        if groups is None:
            groups = self._groups

        # don't try to apply if we haven't read anything in yet
        if self._settings_read:
            for g in groups:
                for p in self.properties[g]:
                    if p.apply:
                        p.apply(self._retrieve_value(g, p.name))

            # now clear the temp storage
            self.temp_store.clear()
            # record that we've applied the settings
            self._settings_applied = True

    def _retrieve_value(self, group, name):
        """
        Called from apply() to get the values that were read in from
        disk. After this is called, the temporary storage will be
        cleared

        :param name:
        :return: stored value
        """

        if name in self.preferences[group]:
            return self.preferences[group][name]
        elif name in self.MRUs[group]:
            return self.MRUs[group][name]
        else:
            return self.temp_store[group][name]

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

            for group in self._groups:
                settings.beginGroup(group)


                for p in self.properties[group]:
                    settings.setValue(p.name, p.accessor())

                settings.endGroup()


__instance = None

# use this to maintain the singleton pattern
# def _instance():
#     global __instance
#
#     # if we've yet to create an instance, do it now
#     if __instance is None:
#         __instance = _AppSettings()
#
#     # return the singleton instance
#     return __instance

def init(*groups):
    """Initialize the AppSettings instance w/ the given group name(s).
    A group corresponds to a section in the INI file."""

    global __instance

    if __instance is None:
        # only create the instance once, to maintain the singleton pattern
        __instance = _AppSettings(*groups)

    return __instance

##=============================================
## Instance proxy methods
##=============================================

def Set(group, pref_name, value):
    """
    Change the current value of a stored preference

    :param pref_name:
    :param value:
    """
    __instance.set_pref_val(group, pref_name, value)

def Get(group, pref_name):
    """

    :param pref_name:
    :return: the current value of the named preference
    """
    return __instance.get_pref_val(group, pref_name)

def add(group, name, value=None, p_type=None,
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

        :param type|str p_type: python type of the value that will be
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

    __instance.add(group, name, value, p_type, apply, on_change)

def add_mru(group, name, value=None, p_type=None,
        apply=None, on_change=None):
    """
    Special version of ``add()`` that creates Most-Recently-Used lists.
    `value` should be an Iterable such a list or tuple. `p_type` needs
    to be the type of the elements of `value`.

    When using ``Get()`` and ``Set()`` for MRU-properties, ``Set()``
    adds the argument to the front of the MRU-list, while ``Get()``
    returns the most-recently added value.

    :param group:
    :param name:
    :param value:
    :param p_type:
    :param apply:
    :param on_change:
    :return:
    """
    __instance.add_mru(group, name, value, p_type, apply, on_change)

def read(groups=None):
    """
    Read in the Qt settings from native storage
    """
    __instance.read(groups)

def apply_all(groups=None):
    """
    Apply the settings that have been read in. Should be called after
    read()
    """
    __instance.apply(groups)

def read_and_apply(groups=None):
    """
    Read in the Qt settings from native storage and apply them to the
    application.
    """
    __instance.read(groups)
    __instance.apply(groups)


def write():
    """
    Write the current settings to native storage
    """
    __instance.write()


