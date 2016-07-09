from collections import deque
from functools import partial

from PyQt5.QtWidgets import QUndoCommand


class ModAttributeChangeCommand(QUndoCommand):
    """
    Used to change a mod attribute *other* than ordinal
    (i.e. do not use this when the mod's install order is
    being changed)


    """
    def __init__(self, mod_entry, attribute, value, *args, **kwargs):
        """
        :param QModEntry mod_entry: the mod object
        :param str attribute: name of the attribute to change
        :param value: the new value of the attribute
        """
        super().__init__(*args, **kwargs)

        self.mod = mod_entry
        self.attr = attribute
        self.old_val = getattr(self.mod, self.attr)
        self.new_val = value


    def redo(self):
        """
        Also known as "do". Change to value of the attribute from the
        old value to the new.
        """

        setattr(self.mod, self.attr, self.new_val)

    def undo(self):
        """
        Restore the original value of the attribute
        """
        setattr(self.mod, self.attr, self.old_val)


class ShiftRowsCommand(QUndoCommand):

    def __init__(self, collection, start, end, dest, begin_move_rows, end_move_rows, parent_index, *args, **kwargs):
        """

        :param collection: the int-indexable collection of items that
            is the target of this shift operation.

        :param int start: initial starting row of the range of items
        :param int end: final row of the range
        :param int dest: destination row (where `start` should end up)

        :param begin_move_rows: the beginMoveRows(...) method of the
            model creating this command; called immediately
            before the shift operation
        :param end_move_rows: the endMoveRows() method of the
            model creating this command; called immediately
            after the shift operation

        :param parent_index: the QModelIndex of the parent item in the
            model.

        :param args:
        :param kwargs:
        """
        super().__init__(*args, **kwargs)

        self.list = collection

        self.start = start
        self.end = end
        self.dest = dest

        self.count = 1 + end - start

        # shift distance, could be positive or negative
        delta_shift = dest - start

        # this is actually the inverse step (normal vector)
        # will be +1 for up, -1 for down
        self.step = -(delta_shift//abs(delta_shift))

        # will be needed later to prevent overshooting the end
        end_offset = 0

        if dest < start:
            # means we're moving items UP

            # get a slice from smallest index...
            self.slice_start = dest_item = dest

            # ...to the end of the rows to displace
            self.slice_end = 1 + end

        else:
            # we're moving down
            self.slice_start = start

            self.slice_end = dest + self.count
            # we want to make sure we don't try to move past the end;
            # if we would, change the slice end to the max row number,
            # but save the amount we would have gone over for later
            # reference
            end_offset = max(0, self.slice_end - len(collection))
            if end_offset > 0:
                self.slice_end -= end_offset
            dest_item = self.slice_end


        ## callbacks
        ## TODO: will the parent_index become invalid? Does it need to be a persistentModelIndex??

        # arguments for [re]do
        self.begin_move_rows_redo = partial(begin_move_rows, parent_index, start, end, parent_index, dest_item)

        # arguments for undo
        # here's where we use that offset we saved;
        # have to subtract it from both start and end to make sure
        # we're referencing the right block of rows when
        # calling beginMoveRows
        self.begin_move_rows_undo = partial(begin_move_rows,
                                            parent_index,
                                            dest - end_offset,
                                            end + delta_shift - end_offset,
                                            parent_index,
                                            self.slice_end
                                                if dest < start
                                                else self.slice_start)
        self.end_move_rows = end_move_rows

    def _do_shift(self, slice_start, slice_end, count, vector):

        # copy the slice into a deque;
        deck = deque(self.list[slice_start:slice_end])

        # rotate the deck in the opposite direction and voila!
        # its like we shifted everything.
        deck.rotate(count * vector)

        # pop em back in, replacing the entry's ordinal to reflect
        # the mod's new position
        for i in range(slice_start, slice_end):
            mod = deck.popleft()
            mod.ordinal = i+1
            self.list[i] = mod
            # self.list[i] = deck.popleft()
            # self.list[i].ordinal = i+1

    def redo(self):
        self.begin_move_rows_redo()
        # call shift with the regular step value
        self._do_shift(self.slice_start, self.slice_end,
                       self.count, self.step)
        self.end_move_rows()


    def undo(self):
        self.begin_move_rows_undo()
        # undo just involves rotating in the opposite direction
        self._do_shift(self.slice_start, self.slice_end,
                      self.count, -self.step)
        self.end_move_rows()

