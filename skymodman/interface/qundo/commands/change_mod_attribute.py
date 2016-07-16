"""
change_mod_attribute QUndoCommand
"""
from ..undocmd import UndoCmd

class ChangeModAttributeCommand(UndoCmd):
    """
    Used to change a mod attribute *other* than ordinal
    (i.e. do not use this when the mod's install order is
    being changed)


    """

    __slots__ = ("mod", "attr", "old_val", "new_val")

    def __init__(self, mod_entry, attribute, value, text="Change {}", *args, **kwargs):
        """
        :param QModEntry mod_entry: the mod object
        :param str attribute: name of the attribute to change
        :param value: the new value of the attribute
        """
        super().__init__(text=text.format(attribute), *args, **kwargs)

        self.mod = mod_entry
        self.attr = attribute
        self.old_val = getattr(self.mod, self.attr)
        self.new_val = value


    def _redo_(self):
        """
        Also known as "do". Change to value of the attribute from the
        old value to the new.
        """

        setattr(self.mod, self.attr, self.new_val)

    def _undo_(self):
        """
        Restore the original value of the attribute
        """
        setattr(self.mod, self.attr, self.old_val)


cmd = ChangeModAttributeCommand