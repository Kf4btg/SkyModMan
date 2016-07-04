from PyQt5.QtCore import QSettings

class QS_Property:
    """
    Represents a value that will stored to and read from the QSettings storage
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

class AppSettings:
    """
    Basically a data-object that can be passed around the application and which contains combined UI and Manager settings.
    """

    def __init__(self, qs_org="skymodman", qs_app="skymodman", qs_group="ManagerWindow"):
        self.org = qs_org
        self.app = qs_app
        self.group = qs_group

        self.props = [] # type: list[QS_Property]

        self.preferences = {}

    def set(self, pref_name, value):
        self.preferences[pref_name] = value

    def __getitem__(self, item):
        return self.preferences[item]

    def get(self, pref_name):
        return self.preferences[pref_name]

    def add(self, name, value=None, p_type=None,
            on_read=lambda t:None, on_change=lambda t:None):
        """
        Create a QSetting property that will be properly
        read-from/saved-to QSettings native storage.

        Examples:
            * add("restore_state", True, bool)
            * add("size", self.size, on_read=lambda s: self.resize(s))
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
            `value` is a constant, this parameter is not used and
            the read value is stored within the AppSettings instance
            (can be accessed via item access, e.g.
            ``my_settings["restore_state"]``).

        :param (T)->None on_change: not currently used
        """

        if callable(value):
            # no default, but read value from app when writing
            self.props.append(QS_Property(p_type, name,
                                          accessor=value,
                                          on_read=on_read,
                                          on_change=on_change))
        else:
            if value is not None and p_type is None:
                p_type = type(value)

            # property is constant (stored when read and changed,
            # not read dynamically from app state)
            self.props.append(QS_Property(p_type, name,
                                          default=value,
                                          accessor=lambda: self.preferences[name],
                                          on_read=lambda t: self.set(name, t),
                                          on_change=on_change))

    def read(self):
        """
        Read in the Qt settings from native storage
        """
        settings = QSettings(self.org, self.app)

        settings.beginGroup(self.group)

        for p in self.props:
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
        settings = QSettings(self.org, self.app)
        settings.beginGroup(self.group)

        for p in self.props:
            settings.setValue(p.name, p.accessor())

        settings.endGroup()







