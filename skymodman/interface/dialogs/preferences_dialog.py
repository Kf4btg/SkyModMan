from functools import partial

from PyQt5.QtWidgets import QDialog, QFileDialog

from skymodman.managers import modmanager as Manager
from skymodman.interface.designer.uic.preferences_ui import Ui_Preferences
from skymodman.utils import withlogger
from skymodman.utils.fsutils import checkPath
from skymodman.constants import INIKey, INISection, UI_Pref


@withlogger
class PreferencesDialog(QDialog, Ui_Preferences):
    """
    Display a modal window allowing the user to modify general settings
    for the application.
    """

    def __init__(self, ui_prefs, *args, **kwargs):
        """

        :param dict[UI_Pref, bool] ui_prefs: boolean preferences specific to the graphical manager (passed from mainwindow)
        """
        super().__init__(*args, **kwargs)

        self.setupUi(self)

        ## Extract UI preferences ##
        self._loadlast = ui_prefs[UI_Pref.LOAD_LAST_PROFILE]
        self._restore_size = ui_prefs[UI_Pref.RESTORE_WINSIZE]
        self._restore_pos = ui_prefs[UI_Pref.RESTORE_WINPOS]

        ## Default Path values ##
        self.paths = {
            # pass false for `use_profile_override` to get the default value
            INIKey.SKYRIMDIR: Manager.get_directory(INIKey.SKYRIMDIR, False),
            INIKey.MODDIR: Manager.get_directory(INIKey.MODDIR, False),
            INIKey.VFSMOUNT: Manager.get_directory(INIKey.VFSMOUNT, False)
        }

        ## associate text boxes with directories ##
        self.path_boxes = {
            INIKey.SKYRIMDIR: self.le_dirskyrim,
            INIKey.MODDIR: self.le_dirmods,
            INIKey.VFSMOUNT: self.le_dirvfs
        }

        ## Set UI to reflect current preferences ##
        self.cbox_loadlastprofile.setChecked(self._loadlast)
        self.cbox_restore_size.setChecked(self._restore_size)
        self.cbox_restore_pos.setChecked(self._restore_pos)

        self.le_dirskyrim.setText(self.paths[INIKey.SKYRIMDIR])
        self.le_dirmods.setText(self.paths[INIKey.MODDIR])
        self.le_dirvfs.setText(self.paths[INIKey.VFSMOUNT])

        ## connect buttons ##
        self.btn_choosedir_skyrim.clicked.connect(
            partial(self.choose_directory, INIKey.SKYRIMDIR))

        self.btn_choosedir_mods.clicked.connect(
            partial(self.choose_directory, INIKey.MODDIR))

        self.btn_choosedir_vfs.clicked.connect(
            partial(self.choose_directory, INIKey.VFSMOUNT))


    def choose_directory(self, folder):
        """
        Open the file dialog to allow the user to select a path for
        the given folder.

        :param INIKey folder:
        :return:
        """

        # fixme: this doesn't seem to actually show the current folder if there
        # is one...maybe that's a Qt bug, though. Or maybe it's because of the
        # hidden folder in the path?
        chosen = QFileDialog.getExistingDirectory(self,
                                                  "Select directory",
                                                  self.paths[folder] or "")

        if checkPath(chosen):
            self.paths[folder] = chosen
            # TODO: associate the box with the ``paths`` dict as a backing store so that this happens automatically
            self.path_boxes[folder].setText(chosen)


