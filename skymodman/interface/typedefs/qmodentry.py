# from functools import total_ordering

from PyQt5.QtCore import Qt

from skymodman.types import ModEntry

Qt_Checked   = Qt.Checked
Qt_Unchecked = Qt.Unchecked

# @total_ordering
class QModEntry(ModEntry):
    """
    Modentry subclass that eases accessing derived properties for displaying in the Qt GUI
    """
    # from the python docs: [Set] __slots__ to an empty tuple. This
    # helps keep memory requirements low by preventing the creation of
    # instance dictionaries.
    __slots__=()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


    @property
    def checkState(self):
        return Qt_Checked if self.enabled else Qt_Unchecked
    #
    # def __lt__(self, other):
    #     return self.ordinal < other.ordinal #ordinal is unique, but not constant
    # def __gt__(self, other):
    #     return self.ordinal > other.ordinal


    # def __eq__(self, other):
    #     """This is for checking if two mods are are equal with regards
    #     to their **editable** fields"""
    #     return self.name == other.name \
    #            and self.enabled == other.enabled \
    #            and self.ordinal == other.ordinal