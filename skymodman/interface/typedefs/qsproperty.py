class QS_Property:
    """
    Represents a value that will be saved to and read from the QSettings storage
    """
    __slots__=("type", "name", "default", "accessor", "apply", "on_change")

    def __init__(self, T, name, default=None, accessor=None, apply=lambda t:None, on_change=lambda t:None):
        """
        :param type T:
        :param str name:
        :param T default:
        :param ()->T accessor:
        :param (T)->None apply:
        :param (T)->None on_change:
        """

        self.type = T
        self.name = name
        self.default = default
        self.accessor = accessor
        self.apply = apply
        self.on_change = on_change