import sys

from PyQt5.QtCore import (Qt,
                          pyqtSignal,
                          pyqtSlot,
                          QStringListModel,
                          QModelIndex,
                          QDir,
                          QStandardPaths,
                          QSortFilterProxyModel)
from PyQt5.QtGui import QGuiApplication
from PyQt5.QtWidgets import (QApplication,
                             QMainWindow,
                             QDialogButtonBox,
                             QMessageBox,
                             QFileDialog)


from skymodman import skylog
from skymodman.constants import (Tab as TAB, INIKey, INISection)
from skymodman.qt_interface.qt_manager_ui import Ui_MainWindow
from skymodman.qt_interface.widgets import message, NewProfileDialog
from skymodman.qt_interface.models import ProfileListModel, ModTableView, ModFileTreeModel
from skymodman.utils import withlogger, Notifier, checkPath


# because it's getting a bit unwieldy trying to keep track of all these models,
# let's let this thing help
qModels = "mod_table", "profile_list", "mod_list", "file_tree"
qFilters = "mod_list", "file_tree", "mod_table"

@withlogger
class ModManagerWindow(QMainWindow, Ui_MainWindow):

    modListModified = pyqtSignal()
    modListSaved = pyqtSignal()

    windowInitialized = pyqtSignal()
    modNameBeingEdited = pyqtSignal(str)

    deleteProfileAction = pyqtSignal(str)

    moveModsUpOne = pyqtSignal()
    moveModsDownOne = pyqtSignal()

    moveModsUp = pyqtSignal(int)
    moveModsDown = pyqtSignal(int)


    def __init__(self, *, manager, **kwargs):
        """

        :param managers.ModManager manager:
        :param kwargs: anything to pass on the the base class constructors
        """
        super().__init__(**kwargs)
        self.LOGGER.info("Initializing ModManager Window")

        # reference to the Mod Manager
        self._manager = manager

        # setup trackers for all of our models and proxies
        self.models = {m:None for m in qModels}
        self.filters = {f:None for f in qFilters}

        # slots (methods) to be called after __init__ is finished
        setupSlots = [
            self.setupProfileSelector,
            self.setupTable,
            self.setupFileTree,
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
        self.mod_table = ModTableView(parent=self, manager=self.Manager)

        #########################
        ## connect the buttons ##

        # use a dialog-button-box for save/cancel
        # have to specify by standard button type
        self.save_cancel_btnbox.button(QDialogButtonBox.Apply).clicked.connect(self.saveModsList)
        self.save_cancel_btnbox.button(QDialogButtonBox.Reset).clicked.connect(self.revertTable)

        # connect mod move-up/down
        self.mod_up_button  .clicked.connect(self.emitMoveModUpOne)
        self.mod_down_button.clicked.connect(self.emitMoveModDownOne)

        #########################
        ## connect the actions ##
        self.action_Quit         .triggered.connect(self.safeQuitApp)
        self.action_Install_Fomod.triggered.connect(self.loadFomod)
        self.actionChoose_Mod_Folder.triggered.connect(self.chooseModFolder)

        # keep track of changes made to mod list
        self.file_tree_modified = False

        # set placeholder fields
        self.loaded_fomod = None
        
        # make some UI adjustments
        self.manager_tabs  .setCurrentIndex(0)
        self.installerpages.setCurrentIndex(0)

        # connect other signals
        self.manager_tabs.currentChanged.connect(self.updateUI)

        # Let sub-widgets know the main window is initialized
        self.windowInitialized.emit()

    @property
    def Manager(self):
        return self._manager

    ###################
    # ACTION HANDLERS #
    ###################

    def updateUI(self, *args):
        if self.loaded_fomod is None:
            self.fomod_tab.setEnabled(False)

        curtab = self.manager_tabs.currentIndex()

        self.save_cancel_btnbox.setVisible(curtab in [TAB.MODLIST, TAB.FILETREE])

        # if self.save_cancel_btnbox.isVisible():
        #     self.save_cancel_btnbox.setEnabled(
        #         (curtab == TAB.MODLIST and len(self._modified_cells)>0)
        #     or  (curtab == TAB.FILETREE and self.file_tree_modified)
        #     )

        self.next_button.setVisible(curtab == TAB.INSTALLER)

    def loadFomod(self):

        # mimes = [m for m in QImageReader.supportedMimeTypes()]
        # print(mimes)
        # mimes = ['application/x-7z-compressed']
        mimes = ['application/xml']
        start_locs = QStandardPaths.standardLocations(QStandardPaths.HomeLocation)
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

    def chooseModFolder(self):
        """
        Show dialog allowing user to choose a mod folder.

        :return:
        """
        moddir = QFileDialog.getExistingDirectory(self, "Choose Directory Containing Installed Mods", self.Manager.Config['dir_mods'])

        # update config with new path
        if checkPath(moddir):
            self.Manager.Config.updateConfig(moddir, INIKey.MODDIR, INISection.GENERAL)

            # reverify and reload the mods.
            if not self.Manager.validateModInstalls():
                self.mod_table.model().reloadErrorsOnly()



    def getTab(self, index:int):
        return self.manager_tabs.widget(index)

    # ===================================
    # FILETREE TAB FUNCTIONS
    # ===================================
    def setupFileTree(self):
        """
        Create and populate the list of mod-folders shown on the filetree tab, as well as prepare the fileviewer pane to show files when a mod is selected

        """

        ##################################
        # setup model for active mods list
        list_model = self.models["mod_list"] =  QStringListModel()
        list_model.setStringList(list(self.Manager.enabledMods()))

        # and now the filter proxy
        modfilter = QSortFilterProxyModel(self.filetree_modlist)
        modfilter.setSourceModel(list_model)

        # connect proxy to textchanged of filter box
        self.filetree_modfilter.textChanged.connect(modfilter.setFilterWildcard)

        # finally, set the filter as the model for the modlist
        self.filetree_modlist.setModel(modfilter)


        self.splitter.setSizes([1, 500]) # just make the left one smaller ok?

        file_tree_model = ModFileTreeModel(manager=self._manager, parent=self.filetree_fileviewer)
        self.filetree_fileviewer.setModel(file_tree_model)

        self.filetree_modlist.selectionModel().currentChanged.connect(self.showModFiles)

        # let setup know we're done here
        self.SetupDone()

    def showModFiles(self, indexCur, indexPre):
        """
        When the currently item changes in the modlist, change the fileviewer to show the files from the new mod's folder.

        :param QModelIndex indexCur: Currently selected index
        :param QModelIndex indexPre: Previously selected index
        """
        mod = self.filetree_modlist.model().stringList()[indexCur.row()]

        p = self.Manager.Config.paths.dir_mods / self.Manager.getModDir(mod)

        self.filetree_fileviewer.model().setRootPath(str(p))

    def updateFileTreeModList(self):
        self.filetree_modlist.model().setStringList(list(self.Manager.enabledMods()))

    # ===================================
    # TABLE OF INSTALLED MODS FUNCTIONS
    # ===================================
    # <editor-fold desc="...">

    def setupTable(self):
        # self.logger << "setupTable begin" + " now"
        self.Manager.loadActiveProfileData()
        self.mod_table.initUI(self.installed_mods_layout)

        self.mod_table.loadData()

        # when the list of modified rows changes from empty to
        # non-empty or v.v., enabled/disable the save/cancel btns
        self.mod_table.model().tableDirtyStatusChange.connect(self.markTableUnsaved)

        self.mod_table.itemsSelected   .connect(self.onModsSelected)
        self.mod_table.selectionCleared.connect(self.onSelectionCleared)
        self.mod_table.itemsMoved      .connect(self.updateModMoveButtons)

        self.moveModsUp  .connect(self.mod_table.onMoveModsUpAction)
        self.moveModsDown.connect(self.mod_table.onMoveModsDownAction)

        self.SetupDone()

    def emitMoveModUpOne(self):
        self.moveModsUp.emit(1)

    def emitMoveModDownOne(self):
        self.moveModsDown.emit(1)

    def onModsSelected(self):
        """
        Enable or disable movement buttons as needed
        :return:
        """
        self.move_mod_box.setEnabled(True)
        self.updateModMoveButtons(self.mod_table.selectedIndexes(),
                                  self.mod_table.model())

    def updateModMoveButtons(self, selected_indexes, model):
        """
        Enabled/disable the mod-up/down buttons depending on whether the first or last
        items in the table are selected.

        :param list[QModelIndex] selected_indexes: list of QModelIndex in the selection
        :param model: the table's model
        """
        index1 = model.index(0,0)
        index_last = model.index(model.rowCount()-1, 0)

        self.mod_up_button.setEnabled(index1 not in selected_indexes)
        self.mod_down_button.setEnabled(index_last not in selected_indexes)

    def onSelectionCleared(self):
        """With nothing selected, there's nothing to move, so disable the movement buttons"""
        self.move_mod_box.setEnabled(False)

    def markTableUnsaved(self, unsaved_changes_present):
        self.save_cancel_btnbox.setEnabled(unsaved_changes_present)

    def revertTable(self):
        self.mod_table.revertChanges()

        self.updateUI()

    @pyqtSlot()
    def saveModsList(self):
        """
        If the list of installed mods has been modified (e.g.
        some mods marked inactive, names changed, etc.), save
        the modified status of the mods to a file
        """
        self.mod_table.saveChanges()

        # update the filetree list
        self.updateFileTreeModList()

        # self.modListSaved.emit()
        # self.updateUI()

    # </editor-fold>

    #===============================
    #  Profile-handling UI
    #==============================
    # <editor-fold desc="...">

    def setupProfileSelector(self):
        """
        Initialize the dropdown list for selecting profiles with the names of the profiles found on disk
        """
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
        self.remove_profile_button.clicked.connect(self.onRemoveProfileClick)

        # let setup know we're done here
        self.SetupDone()

    def onNewProfileClick(self):
        """
        When the 'add profile' button is clicked, create and show a small dialog for the user to choose a name for the new profile.
        """
        popup = NewProfileDialog(combobox_model= self.profile_selector.model())
        # popup.comboBox.setModel(self.profile_selector.model())
        # popup.setComboboxModel(self.profile_selector.model())

        # display popup, wait for close and check signal
        if popup.exec_() == popup.Accepted:
            # add new profile if they clicked ok
            new_profile = self.Manager.newProfile(popup.final_name, popup.copy_from)

            self.profile_selector.model().addProfile(new_profile)

            # set new profile as active and load data
            self.profile_selector.setCurrentIndex(self.profile_selector.findText(new_profile.name, Qt.MatchFixedString))

    def onRemoveProfileClick(self):
        """
        Show a warning about irreversibly deleting the profile.
        """
        profile = self.Manager.active_profile

        if message('warning', 'Confirm Delete Profile', 'Delete "'+profile.name+'"?','Choosing "Yes" below will remove this profile and all saved information within it, including customized load-orders, ini-edits, etc. Note that installed mods will not be affected. This cannot be undone. Are you sure you wish to continue?'):
            self.Manager.deleteProfile(self.profile_selector.currentData())
            self.profile_selector.removeItem(self.profile_selector.currentIndex())

            # self.deleteProfileAction.emit(profile.name)

    @pyqtSlot('int')
    def onProfileChange(self, index):
        """
        When a new profile is chosen from the dropdown list, load all the appropriate data for that profile and replace the current data with it. Also show a message about unsaved changes to the current profile.
        :param index:
        :return:
        """
        if index<0:
            # we have a problem...
            self.LOGGER.error("No profile chosen?!")
        else:
            new_profile = self.profile_selector.currentData(Qt.UserRole).name
            if new_profile == self.Manager.active_profile.name:
                # somehow selected the same profile; do nothing
                return

            # check for unsaved changes to the mod-list
            self.checkUnsavedChanges()

            self.LOGGER.info("Activating profile '{}'".format(new_profile))
            self.Manager.active_profile = new_profile

            # if this is the profile 'default', disable the remove button
            self.checkEnableProfileDelete(new_profile)

            self.loadActiveProfile()

    def loadActiveProfile(self):
        """For now, this just repopulates the mod-table. There might be more to it later"""
        self.LOGGER.debug("About to repopulate table")
        self.mod_table.loadData()
        self.updateFileTreeModList()

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

    # </editor-fold>

    def checkUnsavedChanges(self):
        """
        Check for unsaved changes to the mods list and show a prompt if any are found.
        Clicking yes will save the changes and mark the table clean, while clicking no will
        simply disable the apply/revert buttons as IF the table were clean. This is because
        this is intended to be used right before an action like loading a new profile
        (thus forcing a full table reset) or quitting the app.
        """
        # check for unsaved changes to the mod-list
        if self.mod_table.model().isDirty:
            ok = QMessageBox(QMessageBox.Warning, 'Unsaved Changes',
                                 'Your mod install-order has unsaved changes. Would you like to save them before continuing?',
                                 QMessageBox.No | QMessageBox.Yes).exec_()

            if ok == QMessageBox.Yes:
                self.saveModsList()
            else:
                # don't bother reverting, mods list is getting reset; just disable the buttons
                self.markTableUnsaved(False)

    def safeQuitApp(self):
        """
        Show a prompt if there are any unsaved changes, then close the program.
        """
        self.checkUnsavedChanges()
        self.Manager.DB.shutdown()

        quit_app()



def quit_app():
    skylog.stop_listener()
    QApplication.quit()

# <editor-fold desc="__main__">
if __name__ == '__main__':

    from skymodman import managers

    app = QApplication(sys.argv)

    MM = managers.ModManager()

    w = ModManagerWindow(manager= MM)
    w.resize(QGuiApplication.primaryScreen().availableSize()*3/5)
    w.show()

    sys.exit(app.exec_())
# </editor-fold>
