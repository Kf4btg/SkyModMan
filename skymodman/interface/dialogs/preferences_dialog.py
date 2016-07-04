from functools import partial

from PyQt5.QtWidgets import QDialog, QFileDialog, QDialogButtonBox
from PyQt5.QtCore import pyqtSlot #QStringListModel, Qt

from skymodman.managers import modmanager as Manager
from skymodman.interface import app_settings
from skymodman.interface.designer.uic.preferences_dialog_ui import Ui_Preferences_Dialog
from skymodman.utils import withlogger
from skymodman.utils.fsutils import checkPath
from skymodman.constants import INIKey, INISection, UI_Pref as P, DataDir as D


# SKYPATH=0
# MODPATH=1
# VFSPATH=2

@withlogger
class PreferencesDialog(QDialog, Ui_Preferences_Dialog):
    """
    Display a modal window allowing the user to modify general settings
    for the application.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.setupUi(self)

        ## Default Path values ##
        self.paths = {
            # pass false for `use_profile_override` to get the default value;
            # make sure that we have an empty string if get_directory return None
            D.SKYRIM: Manager.get_directory(D.SKYRIM, False) or "",
            D.MODS: Manager.get_directory(D.MODS, False) or "",
            D.VFS: Manager.get_directory(D.VFS, False) or ""
        }

        ## associate checkboxes w/ preference names
        self.checkboxes = {
            P.LOAD_LAST_PROFILE: self.cbox_loadlastprofile,
            P.RESTORE_WINSIZE: self.cbox_restore_size,
            P.RESTORE_WINPOS: self.cbox_restore_pos
        }

        ## associate text boxes with directories ##
        self.path_boxes = {
            D.SKYRIM: self.le_dirskyrim,
            D.MODS: self.le_dirmods,
            D.VFS: self.le_dirvfs
        }

        ## Set UI to reflect current preferences ##

        #-- checkboxes
        self.cbox_loadlastprofile.setChecked(
            app_settings.Get(P.LOAD_LAST_PROFILE))

        self.cbox_restore_size.setChecked(
            app_settings.Get(P.RESTORE_WINSIZE))

        self.cbox_restore_pos.setChecked(
            app_settings.Get(P.RESTORE_WINPOS))

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

    @pyqtSlot()
    def apply_changes(self):
        """
        Save the user changes to the appropriate config files.
        """
        # TODO: disable the OK/Apply buttons when there are no changes to apply.
        # TODO: allow resetting the paths to default

        for pref, cbox in self.checkboxes.items():
            app_settings.Set(pref, cbox.isChecked())

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
                                                  # self.path_list[folder] or "")

        if checkPath(chosen):
            # self.changed_paths.add(folder)
            # self.paths[folder] = chosen
            self.path_boxes[folder].setText(chosen)

