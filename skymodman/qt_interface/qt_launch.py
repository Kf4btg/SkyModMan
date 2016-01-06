import sys

from PyQt5.QtCore import Qt, QStandardPaths, QDir, pyqtSignal, pyqtSlot
from PyQt5.QtGui import QGuiApplication
from PyQt5.QtWidgets import QApplication, QMainWindow, QTableWidgetItem, \
    QFileDialog, QFileSystemModel, QDialogButtonBox

import PyQt5.QtWidgets as QtW

import skymodman.constants as const
from skymodman.qt_interface.qt_manager_ui import Ui_MainWindow
from skymodman.qt_interface.widgets import custom_widgets
from skymodman.qt_interface.models import ProfileListModel, ModTableModel, ModTableView
from skymodman.utils import withlogger, Notifier, ModEntry
# from collections import OrderedDict
from skymodman import skylog

@withlogger
class ModManagerWindow(QMainWindow, Ui_MainWindow):

    modListModified = pyqtSignal()
    modListSaved = pyqtSignal()
    # changesCanceled = pyqtSignal()

    windowInitialized = pyqtSignal()
    modNameBeingEdited = pyqtSignal(str)
    

    def __init__(self, manager: 'managers.ModManager', *args, **kwargs):
        super(ModManagerWindow, self).__init__(*args, **kwargs)
        self.LOGGER.info("Initializing ModManager Window")

        # reference to the Mod Manager
        self._manager = manager

        setupSlots = [
            self.setupProfileSelector,
            self.setupFileTree,
            self.setupTable,
                      ]

        # connect the windowinit signal to the setup slots
        for s in setupSlots:
            self.windowInitialized.connect(s)

        ## Notifier object for the above 'setup...' slots to
        ## call when they've completed their setup process.
        ## After the final call, the UI will updated and
        ## presented to the user
        self.SetupDone = Notifier(len(setupSlots), self.updateUI)

        # setup the base ui
        self.setupUi(self)

        #init mod table
        self.mod_table = ModTableView(self, self.Manager)

        # connect the buttons

        # use a dialog-button-box
        # have to specify by standard button type
        self.save_cancel_btnbox.button(QDialogButtonBox.Apply).clicked.connect(self.saveModsList)
        self.save_cancel_btnbox.button(QDialogButtonBox.Reset).clicked.connect(self.revertTable)

        # connect the actions
        self.action_Quit.triggered.connect(quit_app)
        self.action_Install_Fomod.triggered.connect(self.loadFomod)

        # keep track of changes made to mod list
        self.file_tree_modified = False

        # set placeholder fields
        self.loaded_fomod = None
        
        # make some UI adjustments
        self.manager_tabs.setCurrentIndex(0)
        self.installerpages.setCurrentIndex(0)

        # connect other signals
        self.manager_tabs.currentChanged.connect(self.updateUI)

        # update UI
        # self.updateUI()

        self.table_unsaved = False


        self.windowInitialized.emit()


    @property
    def Manager(self):
        return self._manager

    def updateUI(self, *args):
        if self.loaded_fomod is None:
            self.fomod_tab.setEnabled(False)

        curtab = self.manager_tabs.currentIndex()

        self.save_cancel_btnbox.setVisible(curtab in [const.TAB_MODLIST, const.TAB_FILETREE])

        # if self.save_cancel_btnbox.isVisible():
        #     self.save_cancel_btnbox.setEnabled(
        #         (curtab == const.TAB_MODLIST and len(self._modified_cells)>0)
        #     or  (curtab == const.TAB_FILETREE and self.file_tree_modified)
        #     )

        self.next_button.setVisible(curtab == const.TAB_INSTALLER)

    def loadFomod(self):
        # mimes = [m for m in QImageReader.supportedMimeTypes()]
        # print(mimes)
        # mimes = ['application/x-7z-compressed']
        mimes = ['application/xml']
        start_locs = QStandardPaths.standardLocations(QStandardPaths.HomeLocation) # type: List[str]
        dialog = QFileDialog(self, "Choose ModuleConfig.xml file",
                             QDir.currentPath()
                             # start_locs.pop() if start_locs else QDir.currentPath()
                             )
        dialog.setAcceptMode(QFileDialog.AcceptOpen)
        dialog.setMimeTypeFilters(mimes)
        dialog.selectMimeTypeFilter(mimes[0])

        if dialog.exec_() == QFileDialog.Accepted:
            files = dialog.selectedFiles()
            print(files)

            self.loaded_fomod = files[0]
            # todo: maybe run this method in a separate thread? at least the dialog
            # todo: setup 2nd tab with data from xml file and begin installation process
            # todo: support loading actual fomod archives. (7z, rar, zip, etc.)


    def getTab(self, index:int):
        return self.manager_tabs.widget(index)

    # ===================================
    # FILETREE TAB FUNCTIONS
    # ===================================
    def setupFileTree(self):
        file_tree_model = QFileSystemModel()
        file_tree_model.setRootPath(self._manager.Config['dir_mods'])
        self.filetree_tree.setModel(file_tree_model)
        self.filetree_tree.setRootIndex(file_tree_model.index(self._manager.Config["dir_mods"]))

        # let setup know we're done here
        self.SetupDone("setupTree")

    # ===================================
    # TABLE OF INSTALLED MODS FUNCTIONS
    # ===================================

    def setupTable(self):
        self.logger.debug("setupTable begin")
        self.Manager.loadActiveProfileData()
        self.mod_table.initUI(self.installed_mods_layout)

        self.mod_table.loadData()

        # when the list of modified rows changes from empty to
        # non-empty or v.v., enabled/disable the save/cancel btns
        self.mod_table.model().tableDirtyStatusChange.connect(self.markTableUnsaved)

        self.SetupDone()

    def markTableUnsaved(self, unsaved_changes_present: bool):
        self.table_unsaved = unsaved_changes_present
        self.save_cancel_btnbox.setEnabled(self.table_unsaved)


    def revertTable(self):
        self.mod_table.revertChanges()

        self.updateUI()

    @pyqtSlot()
    def saveModsList(self):
        """
        If the list of installed mods has been modified (e.g.
        some mods marked inactive, names changed, etc.), save
        the modified status of the mods to a file
        :return:
        """
        self.mod_table.saveChanges()

        # self.modListSaved.emit()
        # self.updateUI()

    #===============================
    #  Profile-handling UI
    #==============================

    def setupProfileSelector(self):
        model = ProfileListModel()

        start_idx = 0
        for name, profile in self.Manager.getProfiles(names_only=False):
            # self.LOGGER.debug("{}: {}".format(name, profile))
            model.insertRows(data=profile)
            if name==self.Manager.active_profile.name:
                self.logger.debug("Setting {} as chosen profile".format(name))
                start_idx=model.rowCount()-1

                # see if we should enable the remove-profile button
                self.checkEnableProfileDelete(name)

        self.profile_selector.setModel(model)
        self.profile_selector.setCurrentIndex(start_idx)
        self.profile_selector.currentIndexChanged.connect(self.onProfileChange)
        self.new_profile_button.clicked.connect(self.onNewProfileClick)

        # let setup know we're done here
        self.SetupDone()



    def onNewProfileClick(self):
        popup = custom_widgets.NewProfileDialog()
        popup.comboBox.setModel(self.profile_selector.model())

        # display popup, wait for close and check signal
        if popup.exec_() == popup.Accepted:
            # add new profile if they clicked ok
            new_profile = self.Manager.newUserProfile(popup.final_name, popup.copy_from)

            self.profile_selector.model().addProfile(new_profile)

            # set new profile as active and load data
            self.profile_selector.setCurrentIndex(self.profile_selector.findText(new_profile.name, Qt.MatchFixedString))


    @pyqtSlot('int')
    def onProfileChange(self, index):
        if index<0:
            # we have a problem...
            self.LOGGER.error("No profile chosen?!")
        else:
            new_profile = self.profile_selector.currentData(Qt.UserRole).name
            if new_profile == self.Manager.active_profile.name:
                # somehow selected the same profile; do nothing
                return

            # check for unsaved changes to the mod-list
            if self.mod_table.model().isDirty:
                ok = QtW.QMessageBox(QtW.QMessageBox.Warning, 'Unsaved Changes', 'Your mod install-order has unsaved changes. Would you like to save them before continuing?', QtW.QMessageBox.No | QtW.QMessageBox.Yes).exec_()


                if ok == QtW.QMessageBox.Yes:
                    self.saveModsList()
                else:
                    # don't bother reverting, mods list is getting reset; just disable the buttons
                    self.markTableUnsaved(False)

            self.LOGGER.info("Activating profile '{}'".format(new_profile))
            self.Manager.active_profile = new_profile

            # if this is the profile 'default', disable the remove button
            self.checkEnableProfileDelete(new_profile)

            self.loadActiveProfile()

    def loadActiveProfile(self):
        """For now, this just repopulates the mod-table. There might be more to it later"""
        self.LOGGER.debug("About to repopulate table")
        self.mod_table.loadData()
        self.updateUI()

    def checkEnableProfileDelete(self, profile_name):
        """
        If the profile name is anything other than the default profile
        (likely 'default') enable the remove_profile button
        :param profile_name:
        :return:
        """
        if profile_name.lower() == 'default':
            self.remove_profile_button.setEnabled(False)
            self.remove_profile_button.setToolTip('Cannot Remove Default Profile')
        else:
            self.remove_profile_button.setEnabled(True)
            self.remove_profile_button.setToolTip('Remove Profile')

def quit_app():
    skylog.stop_listener()
    QApplication.quit()

if __name__ == '__main__':

    from skymodman import managers

    app = QApplication(sys.argv)

    MM = managers.ModManager()

    w = ModManagerWindow(MM)
    w.resize(QGuiApplication.primaryScreen().availableSize()*3/5)
    w.show()

    sys.exit(app.exec_())
