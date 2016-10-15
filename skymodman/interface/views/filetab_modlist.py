from PyQt5 import QtWidgets as qtW
from PyQt5.QtCore import Qt, QModelIndex, pyqtSignal as Signal, pyqtSlot as Slot

from skymodman import constants, Manager
from skymodman.constants.keystrings import INI, Section
# from skymodman.log import withlogger

# templates for text shown in label above list (depending on option)
_lbl_text_allmods = "All Installed Mods ({shown}/{total})"
_lbl_text_only_active = "Active Mods ({shown}/{total})"

# @withlogger
class FileTabModList(qtW.QListView):


    # onlyShowActiveChanged = Signal(bool)
    # """emitted when the active-only profile-setting is loaded or set"""

    # from docs: using the PyQt_PyObject signal type allows passing any
    # python type via the signal. This way, we can easily pass a ModelIndex,
    # ModEntry, or ``None``, as needed
    selectedModChanged = Signal('PyQt_PyObject')
    """When a new mod is selected--and IFF the new selection is valid--
    this signal will be emitted with the ModEntry object of the newly-
    selected mod"""


    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

        # the source model
        self._srcmodel = None
        # placeholder for the search filter
        self._filter = None
        """:type: skymodman.interface.models.ActiveModsListFilter"""

        # placeholders for the associated checkbox and label; will
        # handle these here to keep all things related to the mods-list
        # coordinated in this class
        self._label = None # type: qtW.QLabel
        self._cbox = None # type: qtW.QCheckBox
        self._filterbox = None
        """:type: skymodman.interface.designer.plugins.widgets.escapeablelineedit.EscapeableLineEdit"""

        # reference to the tree viewer
        self._viewer = None

        # we deal with the name column exclusively here
        self._column = constants.Column.NAME.value

    @property
    def filter(self):
        return self._filter

    @property
    def only_show_active(self):
        if not self._filter:
            return False
        return self._filter.onlyShowActive

    @only_show_active.setter
    def only_show_active(self, value):
        if self._filter:
            self._filter.onlyShowActive=value

    @property
    def viewer(self):
        return self._viewer

    @viewer.setter
    def viewer(self, value):
        """Connect a change in this list's selection model with
        showing a new mod in the given tree-viewer"""

        # if viewer has somehow already been set, delete it to
        # disconnect all signals
        if self._viewer: del self._viewer

        self._viewer = value

        # TODO: need custom view for viewer; then we can connect a selection change to setting a new mod on that view

    def setup(self, source_model, label, checkbox, filterbox):
        """

        :param QAbstractItemModel source_model: the main mod-table model
        :param qtW.QLabel label:
        :param qtW.QCheckBox checkbox:
        :param skymodman.interface.designer.plugins.widgets.escapeablelineedit.EscapeableLineEdit filterbox:
        """

        self._label = label
        self._cbox = checkbox
        self._filterbox = filterbox

        from skymodman.interface.models import ActiveModsListFilter

        f = ActiveModsListFilter(self)

        f.setSourceModel(source_model)

        # ignore case when filtering
        f.setFilterCaseSensitivity(Qt.CaseInsensitive)

        # filter reads name column
        f.setFilterKeyColumn(self._column)

        # assign to instance attrs
        self._srcmodel = source_model
        self._filter = f

        # check initial active-only setting
        self.load_active_only_state()

        # set filter as model for self
        self.setModel(f)

        # make sure we're showing the right column
        self.setModelColumn(self._column)

        # make sure label text is updated properly
        self.update_label()

        ## connect signals ##

        # update proxy, label, profile when checkbox toggled
        self._cbox.toggled.connect(self.on_active_only_toggled)

        # change display when filter text changes
        self._filterbox.textChanged.connect(
            self.on_filter_changed
        )

        # have escape key clear focus from filterbox
        self._filterbox.escapeLineEdit.connect(self._filterbox.clearFocus)


        ## The most important part: connect a change in the selection
        # to emitting a signal indicating which mod was just selected
        self.selectionModel().currentChanged.connect(self.on_selection_changed)

        # cleanup
        del ActiveModsListFilter

    # don't override 'reset' because that has repercussions...
    def reset_view(self):
        """Reset the view to a clean state"""

        # clear filter box
        self._filterbox.clear()

        # disable list if main mods folder is inaccessible
        ###...TODO: hmm...maybe we shouldn't do this; unless Skyrim dir is also invalid...
        if not Manager().Folders['mods']:
            self.setEnabled(False)
            self.setToolTip("Mods directory is currently invalid")
        else:
            self.setEnabled(True)
            self.setToolTip(None)

        # update checkbox and label
        self.load_active_only_state()
        self.update_label()

    def load_active_only_state(self):
        """When something major changes (likely the active profile)
        query the profile for the value of the 'Only show active mods'
        setting for the files-tab modlist."""

        active_only = Manager().get_profile_setting(
            INI.ACTIVE_ONLY,
            Section.FILEVIEWER
        )

        if active_only is None:
            # if no profile loaded, set it unchecked and disable it
            self._filter.onlyShowActive=False
            self._cbox.setEnabled(False)
        else:
            self._filter.onlyShowActive = active_only
            self._cbox.setEnabled(True)

        self._cbox.setChecked(self.only_show_active)

        # self.onlyShowActiveChanged.emit(self.only_show_active)



    def update_label(self):
        """Based on whether all/active mods are shown, change the text
        displayed in the list's associated label"""
        text = _lbl_text_only_active if self.only_show_active else _lbl_text_allmods

        self._label.setText(
            text.format(
                shown=self._filter.rowCount(),
                total=self._srcmodel.rowCount()))

    @Slot(bool)
    def on_active_only_toggled(self, only_show_active):
        """

        :param bool only_show_active:
        """

        # ignore if somehow it's the same as before
        if only_show_active == self.only_show_active: return

        # save to Profile
        Manager().set_profile_setting(INI.ACTIVE_ONLY, Section.FILEVIEWER, only_show_active)

        # update filter setting...
        self.only_show_active = only_show_active

        # ... and label text
        self.update_label()

        # self.onlyShowActiveChanged.emit(only_show_active)

    @Slot(str)
    def on_filter_changed(self, text):
        """
        Updates the proxy filtering, and notifies the label
        to change its 'mods shown' count.

        :param text:
        """

        self._filter.setFilterWildcard(text)
        self.update_label()


    @Slot('QModelIndex', 'QModelIndex')
    def on_selection_changed(self, current, previous):
        """

        :param QModelIndex current: the index just selected
        :param QModelIndex previous: the index that was selected prior
            to this change (currently unused)
        """

        real_index = self._filter.mapToSource(current)

        if real_index.isValid():
            # if a valid mod was selected, emit the modentry object
            self.selectedModChanged.emit(real_index.internalPointer())
        else:
            # otherwise, emit ``None`` to clear the filetree
            self.selectedModChanged.emit(None)









