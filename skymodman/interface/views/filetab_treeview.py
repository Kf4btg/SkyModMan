from PyQt5 import QtWidgets
from PyQt5.QtCore import Qt, pyqtSlot as Slot, QObject, QEvent

from skymodman import Manager
# from skymodman.log import withlogger


# @withlogger
class FileTabTreeView(QtWidgets.QTreeView):

    ## SIR HAXALOT
    _ignore_section_resize = False

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

        # static ref to headerview
        self._header = self.header() # type: QtWidgets.QHeaderView

        # track changes in viewport width
        self._viewport_width = -1

        # by default, name col will be 1/2 of the total width,
        # path will be 1/3, conflicts 1/6.  Because this is IMPORTANT
        self._column_ratios=[2, 3, 6]

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

        self._header.sectionResized.connect(self.on_section_resize)

        self._viewport_width = self.viewport().width()

        # self.setSizeAdjustPolicy(self.AdjustToContents)
        # self.setSizeAdjustPolicy(self.AdjustIgnored)


        # self.header().installEventFilter(HeaderResizeFixer(self))

        # self.resizeColumnToContents(0)
        # self.resizeColumnToContents(1)
        # self.resizeColumnToContents(2)

        # stop the header sections from being dragged around
        # h = self.header()

        # h.setSectionsMovable(False)

        # h=self.header()

        # one_third_width = h.length() // 3

        # make name and path columns equal to 1/3 of the available
        # space
        # h.resizeSection(2, 50)
        # h.resizeSection(0, h.length() // 2)
        # h.resizeSection(1, h.length() // 3)
        # h.setSectionResizeMode(type(h).Interactive)
        # h.setSectionResizeMode(0, type(h).Stretch)

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


    def sizeHintForColumn(self, column):
        # this is called during resizeColumnToContents()

        if column == 2: # conflicts
            return self.header().minimumSectionSize()

        # for name/path, return either 1/3 of the viewport width
        # or the default sizeHint, whichever is larger
        return max(self.viewport().width() // 3,
                   super().sizeHintForColumn(column))

    def resizeEvent(self, event):
        """Override the resize event to make sure the columns remain
        reasonably-sized when the window/viewport is resized"""

        ## seems to be unnecessary
        # super().resizeEvent(event)

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
        self._header.blockSignals(True)


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
        self._header.blockSignals(False)


    @Slot(int, int, int)
    def on_section_resize(self, col_index, old_size, new_size):
        """
        Don't know how else to do it...so, we're going to listen for
        all section resize events and force correction based on
        viewport width()

        :param col_index:
        :param old_size:
        :param new_size:
        :return:
        """

        # if not self._ignore_section_resize:
        print("section", col_index, "resize")
        # record new ratio of column's width:total width
        # h = self.header() # type: QtWidgets.QHeaderView

        # h.section


        # self._column_ratios[col_index] = self.width() / new_size

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



class HeaderResizeFixer(QObject):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


    def eventFilter(self, header_obj, event):

        if event.type() == QEvent.Resize:
            print("Resize!!")
            # return True # here if we want to cancel the event

        return super().eventFilter(header_obj, event)