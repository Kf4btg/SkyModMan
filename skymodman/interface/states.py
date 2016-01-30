def tab_state_restorer(self, tabid):
    """Decorator for marking a function as the restorer for the specified tabstate. Calls the function with the dictionary of current state values saved in `tabstate`"""
    tabstate = self.states[tabid]
    def restorer(func):
        return func(tabstate._state)

    return restorer

_movebtns = (m_NONE, m_TOP, m_BOT, m_UP, m_DOWN) = (0, 0b1000, 0b0100, 0b0010, 0b0001)

class TabState:

    __default_statevars = {
        "unsaved":  False,
        "canundo":  False,
        "canredo":  False,
        "cantoggle": False,
        "current_index": None,
        "selection": None,
        "movement": m_NONE
    }

    def __init__(self, **kwargs):
        """copy the kwargs into the state namespace, or use the default state if none are given."""
        # we keep the state variables in a separate namespace.
        if not kwargs:
            self._state = TabState.__default_statevars.copy()

        self._state={k:v for k,v in kwargs}
        self._restore = lambda : None

    def __getitem__(self, item):
        return self._state[item]
    def __setitem__(self, key, value):
        self._state[key]=value

    @property
    def restore(self):
        return self._restore

    @restore.setter
    def restore(self, func):
        self._restore = func


class ModTableState(TabState):

    def __init__(self):
        super().__init__(
            unsaved=       False,
            canundo=       False,
            canredo=       False,
            # cantoggle=     False,
            current_index= None,
            selection=     None,
            movement=      m_NONE,
            mod_order=      None, #type: list # of strings
        )