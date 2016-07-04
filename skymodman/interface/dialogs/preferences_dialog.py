from functools import partial

from PyQt5.QtWidgets import QDialog, QFileDialog, QDataWidgetMapper
# from PyQt5.QtCore import QStringListModel, Qt

from skymodman.managers import modmanager as Manager
from skymodman.interface.designer.uic.preferences_dialog_ui import Ui_Preferences_Dialog
from skymodman.utils import withlogger
from skymodman.utils.fsutils import checkPath
from skymodman.constants import INIKey, INISection, UI_Pref


# SKYPATH=0
# MODPATH=1
# VFSPATH=2

@withlogger
class PreferencesDialog(QDialog, Ui_Preferences_Dialog):
    """
    Display a modal window allowing the user to modify general settings
    for the application.
    """

    def __init__(self, ui_prefs, *args, **kwargs):
        """

        :param skymodman.interface.app_settings.AppSettings ui_prefs: boolean preferences specific to the graphical manager (passed from mainwindow)
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
            # partial(self.choose_directory, 0))

        self.btn_choosedir_mods.clicked.connect(
            partial(self.choose_directory, INIKey.MODDIR))
            # partial(self.choose_directory, 1))

        self.btn_choosedir_vfs.clicked.connect(
            partial(self.choose_directory, INIKey.VFSMOUNT))
            # partial(self.choose_directory, 2))

        ## experiment with qdatawidgetmapper ##
        ## XXX: this almost works, though as is it's still a 2-step
        # process to update the text displayed in the line edits. Also, changing the data in the model doesn't actually seem to update the text like I thought it should...hmm...
        # self.path_list = [self.paths[INIKey.SKYRIMDIR],
        #                           self.paths[INIKey.MODDIR],
        #                           self.paths[INIKey.VFSMOUNT]]
        #
        # self.model = QStringListModel()
        # self.model.setStringList(self.path_list)
        # # self.model.setStringList([self.paths[INIKey.SKYRIMDIR],
        # #                           self.paths[INIKey.MODDIR],
        # #                           self.paths[INIKey.VFSMOUNT]])
        #
        # self.mapper = QDataWidgetMapper()
        # self.mapper.setOrientation(Qt.Vertical)
        # self.mapper.setModel(self.model)
        #
        # self.mapper.addMapping(self.le_dirskyrim, 0)
        # self.mapper.addMapping(self.le_dirmods, 1)
        # self.mapper.addMapping(self.le_dirvfs, 2)
        #
        # self.mapper.toFirst()


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
            self.paths[folder] = chosen
            self.path_boxes[folder].setText(chosen)
            # self.path_list[folder] = chosen
            # self.model.setStringList(self.path_list)


