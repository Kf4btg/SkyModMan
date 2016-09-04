from collections import namedtuple

__all__ = ['LOW', 'NORMAL', 'HIGH', 'Alert']

## values for ``level``
LOW=0
NORMAL=1
HIGH=2

## this may be better off a plain class w/ __slots__...but I really
## like the convenience of the built-in __repr__ that namedtuples get...
class Alert(namedtuple("Alert", "level label desc fix check")):
    """
    Represents information about an error or issue that has arisen
    and requires the user's attention.

    Fields:
        level: One of the values 'LOW', 'NORMAL', or 'HIGH',
        denoting the severity of the issue.

        label: A short string used to title the alert

        desc: A longer text description of the issue.

        fix: Text describing the suggested fix for the issue, if any.

        check: a callable that returns a bool value indicating whether
        this alert is still active: if the alert still applies,
        this method should return True. If it has been resolved,
        check() should return False.

    Properties:
        is_active: returns the current value of check()
    """
    __slots__ = ()

    @property
    def is_active(self):
        """
        :return: the current value of check(): True if the alert still applies, False if it has been resolved. NOTE: This property assumes check() has no required parameters; if that assumption is incorrect, check() should be instead be called directly with the applicable arguments.
        """
        return self.check()


Alert.level.__doc__ = "One of the values 'LOW', 'NORMAL', or 'HIGH', denoting the severity of the issue."
Alert.label.__doc__ = "A short string used to title the alert"
Alert.desc.__doc__ = "A longer text description of the issue."
Alert.fix.__doc__ = "Text describing the suggested fix for the issue, if any."
Alert.check.__doc__ = "a callable returning a bool value indicating whether this alert is still active: if the alert still applies, check() should return True. If it has been resolved, check() should return False."
