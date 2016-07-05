from functools import partial

from PyQt5.QtWidgets import QDialog, QFileDialog, QDialogButtonBox
from PyQt5.QtCore import pyqtSlot, pyqtSignal #QStringListModel, Qt

from skymodman.managers import modmanager as Manager
from skymodman.interface import app_settings
from skymodman.interface.designer.uic.preferences_dialog_ui import Ui_Preferences_Dialog
from skymodman.utils import withlogger
from skymodman.utils.fsutils import checkPath
from skymodman.constants import DataDir as D
from skymodman.constants import KeyStr, ProfileLoadPolicy


# SKYPATH=0
# MODPATH=1
# VFSPATH=2

@withlogger
class PreferencesDialog(QDialog, Ui_Preferences_Dialog):
    """
    Display a modal window allowing the user to modify general settings
    for the application.
    """

    profilePolicyChanged = pyqtSignal(int, bool)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.setupUi(self)


        ## Default Path values ##
        # pass false for `use_profile_override` to get the default value;
        # make sure that we have an empty string if get_directory return None
        self.paths={p:Manager.get_directory(p, False) or "" for p in KeyStr.Dirs}

        ## associate checkboxes w/ preference names
        self.checkboxes = {
            KeyStr.UI.RESTORE_WINSIZE: self.cbox_restore_size,
            KeyStr.UI.RESTORE_WINPOS: self.cbox_restore_pos
        }


        ## Setup Profile Load Policy radiobuttons ##
        self.radios = {
            ProfileLoadPolicy.last: self.rad_load_last_profile,
            ProfileLoadPolicy.default: self.rad_load_default_profile,
            ProfileLoadPolicy.none: self.rad_load_no_profile
        }

        # load and store the current policy
        self._active_plp = self._selected_plp = app_settings.Get(
                             KeyStr.UI.PROFILE_LOAD_POLICY)

        # check the appropriate radio button based on current policy;
        # associate a change in the radio selection with updating _selected_plp
        for plp, rb in self.radios.items():
            if plp == self._selected_plp:
                rb.setChecked(True)

            # chain each button's toggled(bool) signal to the profilePolicyChanged
            # signal, which includes the value of the button's associated policy
            rb.toggled.connect(partial(self.profilePolicyChanged.emit, plp.value))

        # and connect this signal to the handler which updates _selected_plp
        self.profilePolicyChanged.connect(self.on_profile_policy_changed)


        ## associate text boxes with directories ##
        self.path_boxes = {
            KeyStr.Dirs.SKYRIM: self.le_dirskyrim,
            KeyStr.Dirs.MODS: self.le_dirmods,
            KeyStr.Dirs.VFS: self.le_dirvfs
        }

        ## Set UI to reflect current preferences ##

        #-- checkboxes
        self.cbox_restore_size.setChecked(
            app_settings.Get(KeyStr.UI.RESTORE_WINSIZE))

        self.cbox_restore_pos.setChecked(
            app_settings.Get(KeyStr.UI.RESTORE_WINPOS))

        #-- line-edit text displays
        self.le_dirskyrim.setText(self.paths[D.SKYRIM])
        self.le_dirmods.setText(self.paths[D.MODS])
        self.le_dirvfs.setText(self.paths[D.VFS])


        ## connect buttons ##

        self.btn_choosedir_skyrim.clicked.connect(
            partial(self.choose_directory, D.SKYRIM))

        self.btn_choosedir_mods.clicked.connect(
            partial(self.choose_directory, D.MODS))

        self.btn_choosedir_vfs.clicked.connect(
            partial(self.choose_directory, D.VFS))

        ## apply button ##
        self.prefs_btnbox.button(QDialogButtonBox.Apply).clicked.connect(self.apply_changes)

        # also apply changes when clicking OK
        self.accepted.connect(self.apply_changes)

    @pyqtSlot(int, bool)
    def on_profile_policy_changed(self, value, enabled):
        """

        :param int value: corresponding to a value in constants.ProfileLoadPolicy
        :param bool enabled: whether the button associated with this value was just enabled or disabled
        """

        if enabled:
            self._selected_plp = ProfileLoadPolicy(value)

    @pyqtSlot()
    def apply_changes(self):
        """
        Save the user changes to the appropriate config files.
        """
        # TODO: disable the OK/Apply buttons when there are no changes to apply.
        # TODO: allow resetting the paths to default

        for pref, cbox in self.checkboxes.items():
            app_settings.Set(pref, cbox.isChecked())

        # check for a change in the profile-load-policy
        if self._active_plp != self._selected_plp:
            app_settings.Set(KeyStr.UI.PROFILE_LOAD_POLICY, self._selected_plp)

        # check if any of the paths have changed and update accordingly
        for label, path in self.paths.items():
            newpath = self.path_boxes[label].text()

            # allow changing if the path is valid or cleared
            if path != newpath and (newpath == "" or checkPath(newpath)):
                Manager.set_directory(label, newpath, False)
                self.paths[label] = newpath

    @pyqtSlot(str)
    def choose_directory(self, folder):
        """
        Open the file dialog to allow the user to select a path for
        the given folder.

        :param folder:
        :return:
        """

        # fixme: this doesn't seem to actually show the current folder if there
        # is one...maybe that's a Qt bug, though. Or maybe it's because of the
        # hidden folder in the path?
        chosen = QFileDialog.getExistingDirectory(self,
                                                  "Select directory",
                                                  self.paths[folder] or "")

        if checkPath(chosen):
            self.path_boxes[folder].setText(chosen)

