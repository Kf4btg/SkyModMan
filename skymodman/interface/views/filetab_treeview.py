from PyQt5 import QtWidgets
from PyQt5.QtCore import Qt, pyqtSlot as Slot, QObject, QEvent

from skymodman import Manager
from skymodman.constants.enums import FileTreeColumn
# from skymodman.log import withlogger


# @withlogger

COL_NAME, COL_PATH, COL_CONFLICTS = (
    FileTreeColumn.NAME, FileTreeColumn.PATH, FileTreeColumn.CONFLICTS)

_stretch_mode = QtWidgets.QHeaderView.Stretch
_fixed_mode = QtWidgets.QHeaderView.Fixed
_interactive_mode = QtWidgets.QHeaderView.Interactive

class FileTabTreeView(QtWidgets.QTreeView):


    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)


        # source model
        self._srcmodel = None
        """:type: skymodman.interface.models.ModFileTreeModel_QUndo"""

        # search filter proxy model
        self._filter = None
        """:type: skymodman.interface.models.FileViewerTreeFilter"""

        self._filterbox = None
        """:type: skymodman.interface.designer.plugins.widgets.escapeablelineedit.EscapeableLineEdit"""

        self._resized = False

        # noinspection PyTypeChecker
        self._column_count = len(FileTreeColumn)

        # static ref to headerview
        self.setHeader(BetterHeader(Qt.Horizontal, self))
        self._header = self.header() # type: QtWidgets.QHeaderView
        self._header.setMinimumSectionSize(100)

        # track changes in viewport width
        self._viewport_width = -1

        # by default, name col will be 1/2 of the total width,
        # path will be 1/3, conflicts 1/6.  Because this is IMPORTANT
        self._column_ratios=[2, 3, 6]

        self._first_show=True

    @property
    def filter(self):
        return self._filter

    @property
    def undo_stack(self):
        """Returns the source-model's undo stack"""
        try:
            return self._srcmodel.undostack
        except AttributeError:
            # src model is not set yet
            return None

    @property
    def has_unsaved_changes(self):
        return self._srcmodel.has_unsaved_changes

    ##=============================================
    ## REAL initialization
    ##=============================================

    def setup(self, selection_list, filterbox):
        """

        :param selection_list: the QListView of mod names; when one is
            selected, update which mod is shown here
        """
        from skymodman.interface.models import ModFileTreeModel_QUndo, \
            FileViewerTreeFilter

        self._filterbox = filterbox
        # have escape key clear focus from filterbox
        self._filterbox.escapeLineEdit.connect(
            self._filterbox.clearFocus)

        # initialize model
        self._srcmodel = ModFileTreeModel_QUndo(self)

        # initialize proxy filter
        self._filter = FileViewerTreeFilter(self)

        # set source model on filter
        self._filter.setSourceModel(self._srcmodel)

        self._filter.setFilterCaseSensitivity(Qt.CaseInsensitive)

        # change display when filter text changes
        self._filterbox.textChanged.connect(
            self.on_filter_changed
        )

        # set filter as main model
        self.setModel(self._filter)

        # connect a selection-change in the modslist to updating the tree
        selection_list.selectedModChanged.connect(self.on_mod_changed)

        # turn off horizontal scrollbar
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        # h = self.header() # type: QtWidgets.QHeaderView

        #=================================
        # Header setup
        #---------------------------------

        # turn off last section stretch to allow us to manipulate its size
        self._header.setStretchLastSection(False)

        # don't allow rearranging columns
        self._header.setSectionsMovable(False)

        # set last section to Fixed mode to prevent user from trying
        # to resize it; they actually shouldn't even be ABLE to try to
        # resize it if everything were working perfectly because the
        # resize handle (on the right edge of the) section would be
        # inaccessible to mouse clicks. But since things don't always
        # line up quite right, it is sometimes visible.
        self._header.setSectionResizeMode(self._column_count-1,
                                          QtWidgets.QHeaderView.Fixed)




        # self._header.sectionResized.connect(self.on_section_resize)

        self._viewport_width = self.viewport().width()

        # self.setSizeAdjustPolicy(self.AdjustToContents)
        # self.setSizeAdjustPolicy(self.AdjustIgnored)


        # self.header().installEventFilter(HeaderResizeFixer(self))

        # for c in range(self.model().columnCount()):
        #     self.resizeColumnToContents(c)

        # self.apply_default_column_widths()

        # stop the header sections from being dragged around
        # h = self.header()

        # cleanup
        del ModFileTreeModel_QUndo, FileViewerTreeFilter

    def reset_view(self):
        """Reset view to a clean state"""

        self._filterbox.clear()

        self._srcmodel.setMod(None)

    def revert(self):
        self._srcmodel.revert_changes()

    def save(self):
        self._srcmodel.save()

    @Slot('PyQt_PyObject')
    def on_mod_changed(self, new_mod):
        """

        :param new_mod: could be a ModEntry object or ``None``
        """

        # first, clear the filter box

        if new_mod is not self._srcmodel.mod:
            self._filterbox.clear()

        # set new mod on model
        self._srcmodel.setMod(new_mod)

        # self.viewport().width()

        # self.resizeColumnToContents(0)
        # self.resizeColumnToContents(1)
        # self.resizeColumnToContents(2)


        # if not self._resized:
        #     h=self.header()
        #
        #     w = self.viewport().width()
        #     # make name and path columns equal to 1/3 of the available
        #     # space
        #     # h.resizeSection(2, 50)
        #     h.resizeSection(0, w // 2)
        #     h.resizeSection(1, w // 3)
        #
        #     # h.setSectionResizeMode(2, type(h).Fixed)
        #
        #     # self.resizeColumnToContents(0)
        #
        #     self._resized = True

    # def apply_default_column_widths(self):
    #     w = self.width()
    #
    #     col_count = self.model().columnCount()
    #
    #     # each col gets an even num of pixels:
    #     # but if we try to give each column an equal num of pixels,
    #     # we'll surely have a few left over
    #     col_width, extra_px = w // col_count, w % col_count
    #
    #     # just add the extra pixels to the first column...
    #     # surely no one will notice.
    #     self.setColumnWidth(0, col_width + extra_px)
    #
    #     # the rest get the normal width
    #     for column in range(1, col_count):
    #         self.setColumnWidth(column, col_width)

    @Slot(int, int, int)
    def on_section_resize(self, col, old, new):

        self._header.resizeSections(_stretch_mode)



    def sizeHintForColumn(self, column):
        # this is called during resizeColumnToContents()

        min_size = self._header.minimumSectionSize()

        if column == COL_CONFLICTS:
            # keep conflicts column at minimum size
            # return self.header().minimumSectionSize()
            return min_size

        # for name/path, return either 1/2 of the remaining width
        # or the default sizeHint, whichever is larger
        remaining = self._viewport_width - min_size
        half_remaining, extra_px = remaining // 2, remaining % 2

        if column == COL_NAME:
            # add any extra pixels to the first column
            return max(half_remaining + extra_px,
                       super().sizeHintForColumn(column))

        return max(half_remaining, super().sizeHintForColumn(column))

    def resizeEvent(self, event):
        """Override the resize event to make sure the columns remain
        reasonably-sized when the window/viewport is resized"""
        # if self._first_show:
        #     # self.apply_default_column_widths()
        #     for c in range(self.model().columnCount()):
        #         self.resizeColumnToContents(c)
        #     self._first_show=False
        # else:
        #     ## seems to be unnecessary
        #     super().resizeEvent(event)
        # return
        # print("resize event")

        self._viewport_width = event.size().width()

        for c in range(self.model().columnCount()):
            self.resizeColumnToContents(c)
        return

    def _resizeEvent(self, event):
        # print("resize event")

        # newsize=event.size()
        # newwidth = newsize.x()
        w = self._viewport_width = event.size().width()

        # print("vpw:", w)
        # print(event.size())

        # print(self.width()) # usually 3-4 px wider than the other two
        ## apparently due to those below excluding the scrollbar width
        # print(self.viewport().width())
        # print(self.header().width())

        # self.header().setMaximumWidth(w)

        # h = self.header() # type: QtWidgets.QHeaderView
        # h.setWidth(w)

        col_count = self.model().columnCount()

        # each col gets an even num of pixels:
        # but if we try to give each column an equal num of pixels,
        # we'll surely have a few left over
        col_width, extra_px = w // col_count, w % col_count

        # extra_px = w % col_count # will be in range 0-2

        # block signals from the header to avoid recursively calling
        # our on_section_resized() handler
        # self._header.blockSignals(True)


        # just add the extra pixels to the first column...
        # surely no one will notice.
        self.setColumnWidth(0, col_width + extra_px)

        # the rest get the normal width
        for column in range(1, col_count):
            self.setColumnWidth(column, col_width)

        # for column in range(col_count):
        #     # print("set width for col", column)
        #
        #     # divvy the few extra pixels to the first columns;
        #     # NTS: we could just give them to the first column, and
        #     # likely none would be the wiser...
        #     if extra_px > 0:
        #         self.setColumnWidth(column, col_width + 1)
        #         extra_px -= 1
        #     else:
        #         self.setColumnWidth(column, col_width)

        # fixme: blocking signals makes the header sections look wonky until they get manually resized
        # reenable header signals
        # self._header.blockSignals(False)

    @Slot(str)
    def on_filter_changed(self, text):
        """
        Query the modfiles table in the db for files matching the filter
        string given by `text`. The resulting matches are fed to the
        proxy filter on the file viewer which uses them to make sure
        that matching files are shown in the tree regardless of whether
        their parent directories match the filter or not.

        :param text:
        """

        f = self._filter

        # don't bother querying db for empty string,
        # the filter will ignore the matched files anyway
        if not text:
            f.setFilterWildcard(text)

        else:
            # turn wildcard filter into SQL-compatible pattern
            sqlexpr = r'%' + text.replace('?', '_').replace('*',
                                                            r'%') + r'%'

            # get list of matching files from db

            matches = list(Manager().DB.find_matching_files(
                self._srcmodel.modname, sqlexpr))

            # set the matches on the filter
            f.setMatchingFiles(matches)

            # set the wildcard; for this implementation, the filter only
            # needs to know the text so it can short-circuit empty strings
            # (and to do the normal filter-invalidation, etc.)
            f.setFilterWildcard(text)

            # expand full tree by default
            self.expandAll()


class BetterHeader(QtWidgets.QHeaderView):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.iswearimnotrecursing=True
        self._minsectsize=0
        self._count = 0

        # self._no_recurse = -1

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
        viewport width()

        note:: this requires ``setStretchLastSection(False)``

        :param col_index:
        :param old_size:
        :param new_size:
        :return:
        """
        # print("section", col_index, "resize")

        # TODO: mostly works, but can still be kinda wonky, mainly when moving the mouse quickly: it'll cause some gaps after the last column and inconsistencies in the "minimum" size of a column. I suspect the solution is to clamp the sizes below to minimumSectionSize rather than just going by calculated sizes since they may not add up correctly.

        minsize = self._minsectsize

        # print(col_index, new_size)

        # correct sizes smaller than minsize
        if new_size < minsize:

            # re-call resizeSection w/ minsize; the value of
            # ..notrecursing shouldn't be affected here--
            # if it is True, then this call will continue the handling
            # w/ the correct size; if it's False, it'll
            # just set the new size as normal
            self.resizeSection(col_index, minsize)
        elif self.iswearimnotrecursing:

        # if self._no_recurse < 0:
        # if self.iswearimnotrecursing:
            max_width = self.width()
            num_cols = self._count

            ssize = self.sectionSize
            ssizes = [ssize(i) for i in range(num_cols)]
            tot_width = sum(ssizes)


            delta_w = new_size - old_size

            # if we're expanding a section
            if delta_w > 0 and tot_width > max_width:

                # prevent infinite loops
                self.iswearimnotrecursing = False
                # self._no_recurse = col_index

                # find out how far we went over
                excess = tot_width - max_width

                sect = col_index+1
                # find the first column past this one that can
                # still have its size reduced
                while sect < num_cols:
                    s = ssizes[sect]

                    # if it's bigger than minsize, we can shrink it
                    if s > minsize:
                        # remove the excess width from the column
                        self.resizeSection(sect, s - excess)
                        break
                    # move left
                    sect += 1
                else:
                    # all following columns are at minimum already;
                    # disallow the change
                    self.resizeSection(col_index, old_size)

                self.iswearimnotrecursing = True
                # self._no_recurse = -1

            elif delta_w < 0 and col_index < num_cols-1:
                self.iswearimnotrecursing = False

                ##########################
                ## THIS idea was to, when shrinking a section, set
                ## the resize mode for the next section to stretch;
                ## when the resize is done, set it back to interactive.
                ## And, well, it actually KINDA worked! Things got a
                ## little jerky sometimes--sections would spring from
                ## a small size to a bigger size when changing
                ## drag directions, and occasionally a section wouldn't
                ## get set back to interactive correctly--but it's worth
                ## remembering, mulling over, and keeping in mind for
                ## later.

                # self._no_recurse = col_index
                #
                # self.setSectionResizeMode(col_index+1, _stretch_mode)
                #
                # self._no_recurse = -1
                #
                # return

                ##########################


                # see how much empty space we need to fill
                to_fill = max_width - tot_width

                # if we're shrinking, expand the NEXT section
                if new_size > minsize:
                    # that is, if we still CAN shrink this section

                    next_size = ssizes[col_index+1]


                    self.resizeSection(col_index+1,
                                       next_size + to_fill)
                else:
                    ## FIXME: this doesn't really work...when dragging past the min size, the "shrink prev. sections" code will be called once, but then stops. I guess maybe because it knows it has already reached the min. size and so doesn't bother emitting the resizeEvent after that
                    # if the section being resized has reached the min. size
                    # but the user is still dragging, we need to expand
                    # any following sections and shrink any previous
                    # sections if possible

                    shrink_by = -delta_w # invert negative

                    # because delta_w doesn't always line up correctly
                    # with the difference between the total and max
                    # widths, we need to calculate that difference
                    grow_by = max_width - tot_width - shrink_by

                    sect = col_index - 1
                    while sect >= 0:
                        s = ssizes[sect]

                        # if it's bigger than minsize, we can shrink it
                        if s > minsize:
                            # remove the excess width from the column
                            self.resizeSection(sect, s - shrink_by)
                            break
                        # move left
                        sect -= 1
                    else:
                        # we couldn't shrink anything, so we can't
                        # expand anything either; undo change
                        self.resizeSection(col_index, old_size)

                        # then short-circuit outta here
                        self.iswearimnotrecursing = True
                        return


                    # now expand
                    sect = col_index + 1 # we know we're not on the last section
                    self.resizeSection(sect, ssizes[sect]+grow_by)

                self.iswearimnotrecursing = True

        # else:
        #     self.setSectionResizeMode(self._no_recurse+1, _interactive_mode)


                # self._column_ratios[col_index] = self.width() / new_size

class HeaderResizeFixer(QObject):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


    def eventFilter(self, header_obj, event):

        if event.type() == QEvent.Resize:
            print("Resize!!")
            # return True # here if we want to cancel the event

        return super().eventFilter(header_obj, event)