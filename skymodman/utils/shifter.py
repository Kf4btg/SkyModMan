from collections import deque

class shifter:
    """
    Get a callable object that shifts (in-place) part of a mutable
    sequence to different index in that sequence.  The length of the
    sequence must not change so long as the shifter object is in use.
    """
    def __init__(self, sequence, idx_block_start, idx_block_end,
                 idx_dest):
        """

        :param sequence:
        :param idx_block_start: start of shifted block
        :param idx_block_end: end of shifted block
        :param idx_dest: destination index; where the starting item
            should end up after the shift
        """

        self.list = sequence

        ## calculations ##
        self._count = 1 + idx_block_end - idx_block_start

        # shift distance; could be pos/neg
        d_shift = idx_dest - idx_block_start

        # get inverse step (normal vector);
        # this will be +1 for up, -1 for down
        self._step = -(d_shift // abs(d_shift))

        end_offset = 0  # need this later

        if idx_dest < idx_block_start:  # If we're moving UP:

            # get a slice from smallest index...
            self._slice_start = dest_child = idx_dest
            # ...to the end of the rows to displace
            rdest_child = self._slice_end = 1 + idx_block_end

        else:  # moving DOWN:
            rdest_child = self._slice_start = idx_block_start

            dest_child = idx_dest + self._count
            # we want to make sure we don't try to move past the end;
            # if we would, change the slice end to the max row number,
            # but save the amount we would have gone over for
            # later reference
            end_offset = max(0, dest_child - len(sequence))
            if end_offset > 0:
                dest_child -= end_offset

            self._slice_end = dest_child

        ## properties ##
        # the variables that start with '_r' are the "reverse" version
        # of the variable; i.e. the value when shifting in the opposite
        # direction of that defined by the step

        # here's where we use that offset we saved;
        # have to subtract it from both start and end when performing
        # the reverse operation to make sure we're referencing the
        # right block of rows when calling beginMoveRows

        # first index of the block
        self._bstart = idx_block_start
        self._rbstart = idx_dest - end_offset

        # last index of the block
        self._bend = idx_block_end
        self._rbend = idx_block_end + d_shift - end_offset

        # the destination of the block, or where the first item will
        # be located after the shift is performed
        self._newbstart =  dest_child
        self._rnewbstart = rdest_child

        ## this is the totality of the affected indices; includes the
        ## main block itself and any other items that had to be moved
        ## to accomodate the shift
        self.affected_range = range(self._slice_start, self._slice_end)

    def block_start(self, reverse=False):
        """The first index of the block to be shifted"""
        return self._rbstart if reverse else self._bstart

    def block_end(self, reverse=False):
        """The last index of the block to be shifted"""
        return self._rbend if reverse else self._bend

    def block_dest(self, reverse=False):
        """
        :return: the destination of the block, or where the first item
            will be located after the shift is performed
        """
        return self._rnewbstart if reverse else self._newbstart


    def __call__(self, reverse=False):
        """

        :param reverse: perform the shift in the opposite direction
            ("undo" the shift, assuming it was has already been
            performed once in the forward direction)
        """

        # copy the slice into a deque
        deck = deque(self.list[self._slice_start:self._slice_end])

        # then just rotate the deck in the opposite direction and voila!
        # its like we shifted everything.
        deck.rotate(self._count * (-self._step if reverse else self._step))

        # pop the items back in to the original sequence in their
        # new locations
        for i in range(self._slice_start, self._slice_end):
            self.list[i] = deck.popleft()

            # the ordinal-updating will be handled elsewhere, now
            # self.list[i].ordinal = i + 1
