from PyQt5 import QtWidgets
from PyQt5.QtCore import Qt, pyqtSlot as Slot

from skymodman import Manager
# from skymodman.log import withlogger


# @withlogger
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

        # create an undo stack for the viewer
        self._undostack = QtWidgets.QUndoStack()


    @property
    def filter(self):
        return self._filter

    @property
    def undo_stack(self):
        """Returns the source-model's undo stack"""

        # TODO: move the undostack from the model to this view
        try:
            return self._srcmodel.undostack
        except AttributeError:
            # src model is not set yet
            return None

    @property
    def has_unsaved_changes(self):
        return self._srcmodel.has_unsaved_changes


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
