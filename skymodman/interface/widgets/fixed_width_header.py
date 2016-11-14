from PyQt5.QtCore import pyqtSlot as Slot
from PyQt5.QtWidgets import QHeaderView


class FixedWidthHeader(QHeaderView):
    """
    Subclass of QHeaderView that always fills--but never expands
    beyond--the the width of its viewport, while still allowing the user
    to resize the sections in an intuitive manner
    """

    # noinspection PyUnresolvedReferences
    def __init__(self, *args, default_ratios=None, **kwargs):
        """

        :param default_ratios: must be a sequence of integers equal in
            length to the number of columns in the model. Each integer
            is a weight represents the percentage of the total width
            initially allotted to the corresponding column.

            For example, for 3 columns, one might pass a default_ratios
            sequence of ``[3, 2, 1]``. Here, column 0 has an initial
            weight of 3, column 1 a weight of 2, and column 2 a weight
            of 1.

            When the table is first shown, each column is resized
            to a percentage of the total width based on its weight with
            regards to the total weight of all columns. In our example,
            the total weight is ``6`` (from ``3+2+1=6``).  Thus, column
            0 will receive ``3/6`` of the available width, column 1
            gets ``2/6``, and column 2 gets ``1/6``.

            So, if our view were 600px wide (chosen for ease of
            demonstration), the initial column widths would be
            ``[300px, 200px, 100px]``



        :param args: passed on to superclass
        :param kwargs: passed on to superclass
        """
        super().__init__(*args, **kwargs)

        # prevents infinite loops in resize handler()
        self.nestpasunrecurse=True
        self._minsectsize=0
        self._count = 0

        self._first_resize=True
        self._initial_ratios = default_ratios

        self.sectionResized.connect(self.on_section_resize)

        self.sectionCountChanged.connect(self._update_section_count)

    def setMinimumSectionSize(self, px):
        self._minsectsize=px
        super().setMinimumSectionSize(px)

    # noinspection PyUnusedLocal
    @Slot(int, int)
    def _update_section_count(self, old, new):
        self._count=new

    @Slot(int, int, int)
    def on_section_resize(self, col_index, old_size, new_size):
        """
        Don't know how else to do it...so, we're going to listen for
        all section resize events and force correction based on
        width()

        note:: this requires ``setStretchLastSection(False)``

        :param col_index:
        :param old_size:
        :param new_size:
        :return:
        """
        minsize = self._minsectsize

        # correct sizes smaller than minsize
        if new_size < minsize:

            # re-call resizeSection w/ minsize; the value of
            # ..notrecursing shouldn't be affected here--
            # if it is True, then this call will continue the handling
            # w/ the correct size; if it's False, it'll
            # just set the new size as normal
            self.resizeSection(col_index, minsize)
        elif self.nestpasunrecurse:

            max_width = self.width()
            num_cols = self._count

            ssize = self.sectionSize
            ssizes = [ssize(i) for i in range(num_cols)]
            tot_width = sum(ssizes)


            delta_w = new_size - old_size

            # if we're expanding a section
            if delta_w > 0 and tot_width > max_width:

                # prevent infinite loops
                self.nestpasunrecurse = False

                # find out how far we went over
                excess = tot_width - max_width

                sect = col_index+1
                # find the first column past this one that can
                # still have its size reduced
                while sect < num_cols and excess:
                    s = ssizes[sect]

                    # if it's bigger than minsize, we can shrink it
                    if s > minsize:
                        # buuuut only by the amount by which it differs
                        # from minsize...
                        remove = min(excess, s-minsize)
                        # remove the excess width from the column
                        self.resizeSection(sect, s - remove)

                        # subtract the amount removed from excess
                        excess -= remove
                        # if not excess:
                            # if we've consumed all of excess, break out
                            # break
                    # move right
                    sect += 1
                # else:
                    # all following columns are at minimum already;

                    # disallow change
                    # self.resizeSection(col_index, old_size)


                # if there's any excess left, adjust original section
                # to make up for it
                if excess:
                    # however much we could not remove from following
                    # sections, remove now from original to reduce
                    # total width
                    self.resizeSection(col_index, new_size-excess)

                self.nestpasunrecurse = True

            elif (delta_w < 0
                  and col_index < num_cols-1
                  and tot_width < max_width):
                # if we're shrinking a section

                self.nestpasunrecurse = False

                # see how much empty space we need to fill
                to_fill = max_width - tot_width

                next_size = ssizes[col_index+1]

                # expand the next section to compensate
                self.resizeSection(col_index+1,
                                   next_size + to_fill)

                self.nestpasunrecurse = True


    def set_initial_sizes(self):

        # if no initial ratios were given or an incorrect amount
        # were given, ignore this step

        if self._initial_ratios is not None and len(
                self._initial_ratios) == self._count:

            tot_weight = sum(self._initial_ratios)

            w = self.width()

            # for c in range(self._count-1, -1, -1):
            for c in range(self._count):
                self.resizeSection(c,
                       int(w*(self._initial_ratios[c] / tot_weight)))


    def resizeEvent(self, event):
        """
        Capture resize events in order to adjust width of sections
        :param event:
        :return:
        """

        if self._first_resize:
            self.set_initial_sizes()
            self._first_resize = False
        else:

            old_width = event.oldSize().width()
            new_width = self.width()

            dW = new_width - old_width

            # just add or remove the extra width from the first section
            self.resizeSection(0, self.sectionSize(0) + dW)

        # if dW > 0: # we got wider
        #     # add the extra width to the first column
        #     self.resizeSection(0, self.sectionSize(0)+dW)
        #
        # elif dW < 0:  # we shrunk
        #     # subtract the width from the first section if possible
        #     # self.resizeSection(0, self.sectionSize(0))
        #
        #     # subtract from the left-most column that is still larger
        #     # than minimum
        #
        #     c=self._count-1
        #     while c >= 0:
        #         s = self.sectionSize(c)
        #         if s > self._minsectsize:
        #             self.resizeSection(c, s + dW)
        #             break
        #         c-=1



