from functools import partial

from PyQt5.QtWidgets import QDialog, QFileDialog, QDialogButtonBox
from PyQt5.QtCore import pyqtSlot, pyqtSignal #QStringListModel, Qt

from skymodman.managers import modmanager as Manager
from skymodman.interface import app_settings, blocked_signals
from skymodman.interface.designer.uic.preferences_dialog_ui import Ui_Preferences_Dialog
from skymodman.utils import withlogger
from skymodman.utils.fsutils import checkPath
from skymodman import constants


# ref to the ConfigManager
Config = Manager.conf

## text and style sheets for indicator labels
_invalid_path_str = "Path not found"
_invalid_path_style = "QLabel {color: red; font-size: 10pt;}"

_missing_path_str = "Path is required"
_missing_path_style = "QLabel {color: orange; font-size: 10pt; font-style: italic; }"

@withlogger
class PreferencesDialog(QDialog, Ui_Preferences_Dialog):
    """
    Display a modal window allowing the user to modify general settings
    for the application.
    """

    profilePolicyChanged = pyqtSignal(int, bool)
    pathEditFinished = pyqtSignal(str)

    def __init__(self, profilebox_model, profilebox_index, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.setupUi(self)

        # because I'm lazy
        D = constants.KeyStr.Dirs
        UI = constants.KeyStr.UI
        PLP = constants.ProfileLoadPolicy

        ## Default Path values ##
        # pass false for `use_profile_override` to get the default value;
        # make sure that we have an empty string if get_directory return None
        # self.paths={p:Manager.get_directory(p, False) or "" for p in KeyStr.Dirs}
        self.paths={p:Config.paths[p] for p in D}

        ## associate text boxes with directories ##
        self.path_boxes = {
            D.PROFILES: self.le_profdir,
            D.SKYRIM: self.le_dirskyrim,
            D.MODS:   self.le_dirmods,
            D.VFS:    self.le_dirvfs
        }

        ##=================================
        ## Tab 1: General/App dirs
        ##---------------------------------

        ## associate checkboxes w/ preference names
        self.checkboxes = {
            UI.RESTORE_WINSIZE: self.cbox_restore_size,
            UI.RESTORE_WINPOS: self.cbox_restore_pos
        }

        ## Set UI to reflect current preferences ##

        # -- checkboxes
        self.cbox_restore_size.setChecked(
            app_settings.Get(UI.RESTORE_WINSIZE))

        self.cbox_restore_pos.setChecked(
            app_settings.Get(UI.RESTORE_WINPOS))

        ## Setup Profile Load Policy radiobuttons ##
        self.radios = {
            PLP.last: self.rad_load_last_profile,
            PLP.default: self.rad_load_default_profile,
            PLP.none: self.rad_load_no_profile
        }

        # load and store the current policy
        self._active_plp = self._selected_plp = app_settings.Get(
                             UI.PROFILE_LOAD_POLICY)

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


        ## setup profiles-dir selector
        self.le_profdir.setText(self.paths[D.PROFILES])


        ##=================================
        ## Tab 2: Default Data Directories
        ##---------------------------------

        #-- line-edit text displays
        self.le_dirskyrim.setText(self.paths[D.SKYRIM])
        self.le_dirmods.setText(self.paths[D.MODS])
        self.le_dirvfs.setText(self.paths[D.VFS])

        #-- "path is valid" indicator labels

        self.indicator_labels = {
            D.SKYRIM: self.lbl_skydir_status,
            D.MODS: self.lbl_moddir_status,
            D.VFS: self.lbl_vfsdir_status
        }

        # hide the label for valid paths
        for key, lbl in self.indicator_labels.items():
            if not self.paths[key]:
                lbl.setText(_missing_path_str)
                lbl.setStyleSheet(_missing_path_style)
                lbl.setVisible(True)
            elif not checkPath(self.paths[key]):
                lbl.setText(_invalid_path_str)
                lbl.setStyleSheet(_invalid_path_style)
                lbl.setVisible(True)
            else:
                lbl.hide()

        # have the line edits with an indicator label emit a signal when editing is finished
        for k,b in self.path_boxes.items():
            if k in self.indicator_labels.keys():
                b.editingFinished.connect(partial(self.pathEditFinished.emit, k))

        self.pathEditFinished.connect(self.on_path_edit)

        ##=================================
        ## Tab 3: Profiles
        ##---------------------------------

        # reuse the main profile-combobox-model for this one here
        self.combo_profiles.setModel(profilebox_model)
        self.combo_profiles.setCurrentIndex(profilebox_index)

        # store the currently-selected Profile object
        self._selected_profile = self.combo_profiles.currentData()
        self.check_default()

        self.combo_profiles.currentTextChanged.connect(self.change_profile)

        self.cbox_default.toggled.connect(self.set_default_profile)

        ##=================================
        ## Connect Buttons
        ##---------------------------------

        self.btn_choosedir_profiles.clicked.connect(
            partial(self.choose_directory, D.PROFILES))

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
            self._selected_plp = constants.ProfileLoadPolicy(value)

    @pyqtSlot(str)
    def on_path_edit(self, key):
        """
        Called when the user manually edits a path box
        """
        new_value = self.path_boxes[key].text()
        label = self.indicator_labels[key]

        # if they cleared the box
        if not new_value:
            label.setText("Path is required")
            label.setStyleSheet("QLabel {color: orange; font-size: 10pt; font-style: italic; }")
            label.setVisible(True)

        # if they entered an invalid path
        elif not checkPath(new_value, True):
            label.setText("Path not found")
            label.setStyleSheet("QLabel {color: red; font-size: 10pt;}")
            label.setVisible(True)
        else:
            label.setVisible(False)


    @pyqtSlot()
    def change_profile(self):
        """Update the data on the profiles tab to reflect the data from the selected profile."""
        self._selected_profile = self.combo_profiles.currentData()
        self.check_default()

    @pyqtSlot(bool)
    def set_default_profile(self, checked):
        """
        When the user checks the "default" box next to the profile selector,
        update the config to mark the current profile as default.
        If they uncheck it, mark 'default' as default...
        """
        if checked:
            if self._selected_profile:
                Config.default_profile = self._selected_profile.name
        else:
            Config.default_profile = constants.FALLBACK_PROFILE

    def check_default(self):
        """
        If the active profile is marked as default, check the "is_default" checkbox.
        Otherwise, uncheck it.
        """
        # make sure we have a valid profile
        if self._selected_profile:
            # don't want unchecking this to trigger changing the default profile
            with blocked_signals(self.cbox_default):
                self.cbox_default.setChecked(self._selected_profile.name == Config.default_profile)


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
            app_settings.Set(constants.KeyStr.UI.PROFILE_LOAD_POLICY, self._selected_plp)

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
            if folder in self.indicator_labels.keys():
                self.indicator_labels[folder].setVisible(False)
