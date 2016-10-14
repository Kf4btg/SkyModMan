from PyQt5 import QtWidgets as qtW
from PyQt5.QtCore import Qt, pyqtSignal as Signal, pyqtSlot as Slot

from skymodman import constants, Manager
from skymodman.constants.keystrings import INI, Section
from skymodman.log import withlogger


@withlogger
class FileTabModList(qtW.QListView):


    # emitted to tell when the 'only-show-enabled-mods' box should be
    # entirely disabled/enabled
    enableActiveOnlyCheckBox = Signal(bool)

    onlyShowActiveChanged = Signal(bool)
    """emitted when the active-only profile-setting is loaded or set"""


    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

        # flag for only showing 'enabled' mods
        self._activeonly = False

        # the source model
        self._srcmodel = None
        # placeholder for the search filter
        self._filter = None
        """:type: skymodman.interface.models.ActiveModsListFilter"""

        # we deal with the name column exclusively here
        self._column = constants.Column.NAME.value

    @property
    def only_show_active(self):
        if not self._filter:
            return False
        return self._filter.onlyShowActive

    @only_show_active.setter
    def only_show_active(self, value):
        if self._filter:
            self._filter.onlyShowActive=value



    def setup(self, source_model):
        """

        :param QAbstractItemModel source_model: the main mod-table model
        """
        from skymodman.interface.models import ActiveModsListFilter


        f = ActiveModsListFilter(self)

        f.setSourceModel(source_model)

        # ignore case when filtering
        f.setFilterCaseSensitivity(Qt.CaseInsensitive)

        # filter reads name column
        f.setFilterKeyColumn(self._column)

        # update modlist filter state

        # set filter as model for self
        self.setModel(f)

        # make sure we're showing the right column
        self.setModelColumn(self._column)


        # assign to instance attrs
        self._srcmodel = source_model
        self._filter = f

        # cleanup
        del ActiveModsListFilter


    def update_active_only_state(self):
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
            self.enableActiveOnlyCheckBox.emit(False)
        else:
            self._filter.onlyShowActive = active_only
            self.enableActiveOnlyCheckBox.emit(True)

        self.onlyShowActiveChanged.emit(self._filter.onlyShowActive)







