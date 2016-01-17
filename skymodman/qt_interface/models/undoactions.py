from PyQt5.QtWidgets import QUndoCommand, QUndoGroup, QUndoStack, QUndoView
from .modtable_tree import QModEntry
from collections import deque, namedtuple


class CleanStateManager:

    pass



Slice = namedtuple('Slice', 'start, end')
class ShiftRowsCommand(QUndoCommand):


    def __init__(self, entrylist, start, end, dest, parent):
        """

        :param entrylist:
        :param start:
        :param end:
        :param dest:
        :param parent:
        :return:
        """
        super().__init__()

        self.entrylist = entrylist

        self.start  = start
        self.end    = end
        self.dest   = dest
        self.parent = parent


        self.count   = 1 + end - start

        d_shift      = dest - start # shift distance; could be +-
        self.rvector = -(d_shift / abs(d_shift))  # get inverse normal vector (see below)

        s_start = min(dest, start)  # get a slice from smallest index
        s_end   = 1 + (end if s_start == dest # ... to the end of the rows to displace
                         else dest + self.count)

        self.slice = Slice(s_start,s_end)

        self.initial = entrylist[self.slice.start, self.slice.end]

        self.deck = deque(entrylist[self.initial])

    def redo(self):
        """also 'do the first time'"""
        self.deck.rotate(self.count*self.rvector)
        self.putBackIn()

    def undo(self):
        self.deck.rotate(self.count * -self.rvector)
        self.putBackIn()

    def putBackIn(self):

        # slice em back in, but first replace the ordinal to reflect the mod's new position
        self.entrylist[self.slice.start:self.slice.end] = \
            [me.replace(ordinal=self.slice.start + i)
             for i, me in enumerate(self.deck, start=1)]  # ordinal is 1 higher than index




