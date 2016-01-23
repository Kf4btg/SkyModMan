import sys
from functools import partial

from PyQt5.QtCore import (Qt,
                          pyqtSignal,
                          pyqtSlot,
                          QModelIndex,
                          QDir,
                          QStandardPaths,
                          QSortFilterProxyModel)
from PyQt5.QtGui import QGuiApplication, QKeySequence
from PyQt5.QtWidgets import (QApplication,
                             QMainWindow,
                             QDialogButtonBox,
                             QMessageBox,
                             QFileDialog,
                             # QAction,
                             # QActionGroup,
                             # QHeaderView,
                             )

from skymodman import skylog
from skymodman.constants import (Tab as TAB,
                                 INIKey,
                                 INISection,
                                 qModels as M,
                                 qFilters as F,
                                 Column)
from skymodman.qt_interface.qt_manager_ui import Ui_MainWindow
from skymodman.qt_interface.widgets import message, NewProfileDialog
from skymodman.qt_interface.models import ProfileListModel, \
    ModFileTreeModel, ModTable_TreeView, ActiveModsListFilter
from skymodman.utils import withlogger, Notifier, checkPath


@withlogger
class ModManagerWindow(QMainWindow, Ui_MainWindow):
    modListModified     = pyqtSignal()
    modListSaved        = pyqtSignal()

    windowInitialized   = pyqtSignal()
    modNameBeingEdited  = pyqtSignal(str)

    deleteProfileAction = pyqtSignal(str)

    moveMods            = pyqtSignal(int)
    movemodstotop       = pyqtSignal()
    movemodstobottom    = pyqtSignal()

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
        self.models  = {}
        self.filters = {}

        # slots (methods) to be called after __init__ is finished
        setupSlots = [
            self.setupProfileSelector,
            self.setupTable,
            self.setupFileTree,
            self.setupActions,
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

        # init mod table
        self.mod_table = ModTable_TreeView(parent=self,
                                           manager=self.Manager)
        self.toggle_cmd = lambda:None

        #########################
        ## connect the buttons ##

        # use a dialog-button-box for save/cancel
        # have to specify by standard button type
        self.save_cancel_btnbox.button(
            QDialogButtonBox.Apply).clicked.connect(
                self.saveModsList)
        self.save_cancel_btnbox.button(
            QDialogButtonBox.Reset).clicked.connect(
                self.revertTable)

        #########################
        ## connect the actions ##
        self.action_Quit.triggered.connect(
                self.safeQuitApp)
        self.action_Install_Fomod.triggered.connect(
                self.loadFomod)
        self.actionChoose_Mod_Folder.triggered.connect(
                self.chooseModFolder)

        # keep track of changes made to mod list
        self.file_tree_modified = False

        # set placeholder fields
        self.loaded_fomod = None

        # make some UI adjustments
        self.manager_tabs.setCurrentIndex(0)
        self.installerpages.setCurrentIndex(0)

        # connect other signals
        self.manager_tabs.currentChanged.connect(
                self.updateUI)

        # Let sub-widgets know the main window is initialized
        self.windowInitialized.emit()

    @property
    def Manager(self):
        return self._manager

    ###################
    # ACTION HANDLERS #
    ###################
    # <editor-fold desc="...">

    def updateUI(self, *args):
        if self.loaded_fomod is None:
            self.fomod_tab.setEnabled(False)

        curtab = self.manager_tabs.currentIndex()

        self.save_cancel_btnbox.setVisible(
            curtab in [TAB.MODLIST, TAB.FILETREE])

        self.next_button.setVisible(curtab == TAB.INSTALLER)

    def loadFomod(self):

        # mimes = [m for m in QImageReader.supportedMimeTypes()]
        # print(mimes)
        # mimes = ['application/x-7z-compressed']
        mimes = ['application/xml']
        start_locs = QStandardPaths.standardLocations(
            QStandardPaths.HomeLocation)
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
        """
        moddir = QFileDialog.getExistingDirectory(
                self,
                "Choose Directory Containing Installed Mods",
                self.Manager.Config['dir_mods'])

        # update config with new path
        if checkPath(moddir):
            self.Manager.Config.updateConfig(moddir, INIKey.MODDIR,
                                             INISection.GENERAL)

            # reverify and reload the mods.
            if not self.Manager.validateModInstalls():
                self.mod_table.model().reloadErrorsOnly()

    def getTab(self, index: int):
        return self.manager_tabs.widget(index)

    # </editor-fold>


    # ===================================
    # FILETREE TAB FUNCTIONS
    # ===================================
    # <editor-fold desc="...">
    def setupFileTree(self):
        """
        Create and populate the list of mod-folders shown on the filetree tab, as well as prepare the fileviewer pane to show files when a mod is selected
        """
        ##################################
        ## Mods List
        ##################################

        #setup filter proxy for active mods list
        mod_filter = self.filters[F.mod_list] = ActiveModsListFilter(
            self.filetree_modlist)
        mod_filter.setSourceModel(self.models[M.mod_table])
        mod_filter.setFilterCaseSensitivity(Qt.CaseInsensitive)
        # tell filter to read mod name
        mod_filter.setFilterKeyColumn(Column.NAME.value)
        mod_filter.onlyShowActive = \
            self.filetree_activeonlytoggle.checkState() == Qt.Checked

        # connect the checkbox directly to the filter property
        self.filetree_activeonlytoggle.toggled['bool'].connect(mod_filter.setOnlyShowActive)
        self.filetree_activeonlytoggle.toggled['bool'].connect(self.update_modlistlabel)

        # and setup label text for first display
        self.update_modlistlabel(mod_filter.onlyShowActive)

        # connect proxy to textchanged of filter box
        self.filetree_modfilter.textChanged.connect(
            self.on_modlist_filterbox_textchanged)

        # finally, set the filter as the model for the modlist
        self.filetree_modlist.setModel(mod_filter)
        # make sure we're just showing the mod name
        self.filetree_modlist.setModelColumn(Column.NAME.value)

        self.splitter.setSizes(
                [1, 500])  # just make the left one smaller ok?

        ##################################
        ## File Viewer
        ##################################
        ## model for tree view of files
        fileviewer_model = self.models[
            M.file_viewer] = ModFileTreeModel(manager=self._manager,
                                              parent=self.filetree_fileviewer)

        ## filter
        fileviewer_filter = self.filters[
            F.file_viewer] = QSortFilterProxyModel(
                                self.filetree_fileviewer)
        fileviewer_filter.setSourceModel(fileviewer_model)
        fileviewer_filter.setFilterCaseSensitivity(Qt.CaseInsensitive)

        ## connect proxy to textchanged of filter box
        self.filetree_filefilter.textChanged.connect(
            fileviewer_filter.setFilterWildcard)

        ## set model
        self.filetree_fileviewer.setModel(fileviewer_filter)

        ## resize 'name' column to be larger at first than 'path' column
        self.filetree_fileviewer.header().resizeSection(0,400)
        # todo: remember user column resizes
        # self.models[M.file_viewer].rootPathChanged.connect(self.on_filetree_fileviewer_rootpathchanged)

        ## show new files when mod selection in list
        proxy2source = lambda c, p: self.showModFiles(
                mod_filter.mapToSource(c), mod_filter.mapToSource(p))
        self.filetree_modlist.selectionModel().currentChanged.connect(
            # self.showModFiles)
            proxy2source)

        # let setup know we're done here
        self.SetupDone()

    def on_modlist_filterbox_textchanged(self, text):
        # Updates the proxy filtering, and notifies the label
        # to change its 'mods shown' count.
        filt = self.filters[F.mod_list]
        filt.setFilterWildcard(text)
        self.update_modlistlabel(filt.onlyShowActive)


    def update_modlistlabel(self, inactive_hidden):
        if inactive_hidden:
            text = "Active Mods ({shown}/{total})"
        else:
            text = "All Installed Mods ({shown}/{total})"
        self.filetree_listlabel.setText(
                text.format(
                        shown=self.filters[F.mod_list].rowCount(),
                        total=self.models[M.mod_list].rowCount()))

    # todo: change window title (or something) to reflect current folder
    # def on_filetree_fileviewer_rootpathchanged(self, newpath):
    #     self.filetree_fileviewer.resizeColumnToContents(0)

    def showModFiles(self, indexCur, indexPre):
        """
        When the currently selected item changes in the modlist, change the fileviewer to show the files from the new mod's folder.

        :param QModelIndex indexCur: Currently selected index
        :param QModelIndex indexPre: Previously selected index
        """
        if not indexCur.isValid(): return

        modname = self.models[M.mod_list].data(indexCur)

        p = self.Manager.Config.paths.dir_mods / \
            self.Manager.getModDir(modname)

        self.models[M.file_viewer].setRootPath(str(p))

    # </editor-fold>

    # ===================================
    # TABLE OF INSTALLED MODS FUNCTIONS
    # ===================================
    # <editor-fold desc="...">

    def setupTable(self):
        self.Manager.loadActiveProfileData()
        self.mod_table.initUI(self.installed_mods_layout)

        self.models[M.mod_table] = self.mod_table.model()

        self.mod_table.loadData()

        # when the list of modified rows changes from empty to
        # non-empty or v.v., enabled/disable the save/cancel btns
        self.models[M.mod_table
            ].tablehaschanges.connect(
                self.markTableUnsaved)

        self.mod_table.enableModActions.connect(self.on_makeOrClearModSelection)
        self.mod_table.canMoveItems.connect(self.setMoveButtonsEnabled)

        # connect the move up/down by 1 signals
        # to the appropriate slot on view
        self.moveMods.connect(self.mod_table.onMoveModsAction)
        # same for the move to top/button signals
        self.movemodstobottom.connect(
            self.mod_table.onMoveModsToBottomAction)
        self.movemodstotop.connect(
            self.mod_table.onMoveModsToTopAction)

        # connect undo/redo actions to table model
        self.actionUndo.triggered.connect(self.mod_table.undo)
        self.actionRedo.triggered.connect(self.mod_table.redo)

        self.models[M.mod_table].undoevent.connect(self.afterUndoRedo)

        self.SetupDone()

    def on_makeOrClearModSelection(self, has_selection):
        """
        Enable or disable buttons and actions that rely on having a selection in the mod table.
        """
        self.setMoveButtonsEnabled(has_selection, has_selection)

        self.action_togglemod.setEnabled(has_selection)

    def setMoveButtonsEnabled(self, enable_moveup, enable_movedown):
        for action in [self.actionMove_Mod_To_Bottom,
                       self.actionMove_Mod_Down]:
            action.setEnabled(enable_movedown)

        for action in [self.actionMove_Mod_To_Top,
                       self.actionMove_Mod_Up]:
            action.setEnabled(enable_moveup)

    def afterUndoRedo(self, undo_text, redo_text):
        """Update the undo/redo text to reflect the passed text.  If an argument is passed as ``None``, that button will instead be disabled."""
        for action, text, default_text in [
            (self.actionUndo, undo_text, "Undo"),
            (self.actionRedo, redo_text, "Redo")]:
            if text:
                action.setText(text)
                action.setEnabled(True)
            else:
                action.setText(default_text)
                action.setEnabled(False)

    def markTableUnsaved(self, unsaved_changes_present):
        self.save_cancel_btnbox.setEnabled(unsaved_changes_present)
        self.actionSave_Changes.setEnabled(unsaved_changes_present)

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

        # self.modListSaved.emit()
        # self.updateUI()

    # </editor-fold>

    # ===============================
    #  Profile-handling UI
    # ==============================
    # <editor-fold desc="...">

    def setupProfileSelector(self):
        """
        Initialize the dropdown list for selecting profiles with the names of the profiles found on disk
        """
        model = ProfileListModel()

        start_idx = 0
        for name, profile in self.Manager.getProfiles(
                names_only=False):
            # self.LOGGER.debug("{}: {}".format(name, profile))
            model.insertRows(data=profile)
            if name == self.Manager.active_profile.name:
                self.logger << "Setting {} as chosen profile".format(name)
                start_idx = model.rowCount() - 1

                # see if we should enable the remove-profile button
                self.checkEnableProfileDelete(name)

        self.profile_selector.setModel(model)
        self.profile_selector.setCurrentIndex(start_idx)
        self.profile_selector.currentIndexChanged.connect(
            self.onProfileChange)
        self.new_profile_button.clicked.connect(
            self.onNewProfileClick)
        self.remove_profile_button.clicked.connect(
            self.onRemoveProfileClick)

        # let setup know we're done here
        self.SetupDone()

    def onNewProfileClick(self):
        """
        When the 'add profile' button is clicked, create and show a small dialog for the user to choose a name for the new profile.
        """
        popup = NewProfileDialog(
            combobox_model=self.profile_selector.model())

        # display popup, wait for close and check signal
        if popup.exec_() == popup.Accepted:
            # add new profile if they clicked ok
            new_profile = self.Manager.newProfile(popup.final_name,
                                                  popup.copy_from)

            self.profile_selector.model().addProfile(new_profile)

            # set new profile as active and load data
            self.profile_selector.setCurrentIndex(
                self.profile_selector.findText(new_profile.name,
                                               Qt.MatchFixedString))

    def onRemoveProfileClick(self):
        """
        Show a warning about irreversibly deleting the profile.
        """
        profile = self.Manager.active_profile

        if message('warning', 'Confirm Delete Profile',
                   'Delete "' + profile.name + '"?',
                   'Choosing "Yes" below will remove this profile '
                   'and all saved information within it, including '
                   'customized load-orders, ini-edits, etc. Note '
                   'that installed mods will not be affected. This '
                   'cannot be undone. Do you wish to continue?'):
            self.Manager.deleteProfile(
                self.profile_selector.currentData())
            self.profile_selector.removeItem(
                self.profile_selector.currentIndex())

            # self.deleteProfileAction.emit(profile.name)

    @pyqtSlot('int')
    def onProfileChange(self, index):
        """
        When a new profile is chosen from the dropdown list, load all the appropriate data for that profile and replace the current data with it. Also show a message about unsaved changes to the current profile.
        :param index:
        """
        if index < 0:
            # we have a problem...
            self.LOGGER.error("No profile chosen?!")
        else:
            new_profile = self.profile_selector.currentData(
                Qt.UserRole).name
            if new_profile == self.Manager.active_profile.name:
                # somehow selected the same profile; do nothing
                return

            # check for unsaved changes to the mod-list
            self.checkUnsavedChanges()

            self.LOGGER.info(
                "Activating profile '{}'".format(new_profile))
            self.Manager.active_profile = new_profile

            # if this is the profile 'default', disable the remove button
            self.checkEnableProfileDelete(new_profile)

            self.loadActiveProfile()

    def loadActiveProfile(self):
        """For now, this just repopulates the mod-table. There might be more to it later"""
        self.LOGGER << "About to repopulate table"
        self.mod_table.loadData()
        # self.updateFileTreeModList()

        self.updateUI()

    def checkEnableProfileDelete(self, profile_name):
        """
        If the profile name is anything other than the default profile
        (likely 'default') enable the remove_profile button
        :param profile_name:
        """
        if profile_name.lower() == 'default':
            self.remove_profile_button.setEnabled(False)
            self.remove_profile_button.setToolTip(
                'Cannot Remove Default Profile')
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
                             'Your mod install-order has unsaved changes. '
                             'Would you like to save them before continuing?',
                             QMessageBox.No | QMessageBox.Yes).exec_()

            if ok == QMessageBox.Yes:
                self.saveModsList()
            else:
                # don't bother reverting, mods list is getting reset;
                # just disable the buttons
                self.markTableUnsaved(False)

    def safeQuitApp(self):
        """
        Show a prompt if there are any unsaved changes, then close the program.
        """
        self.checkUnsavedChanges()
        self.Manager.DB.shutdown()

        quit_app()

    def _toggleCurrentMod(self, index):
        pass

    def setupActions(self):
        """Create additional actions, and make some tweaks to pre-existing ones"""

        self.actionUndo.setShortcut(QKeySequence.Undo)
        self.actionRedo.setShortcut(QKeySequence.Redo)

        self.action_togglemod.triggered.connect(self.mod_table.toggleSelectionCheckstate)

        self.actionSave_Changes.setShortcut(QKeySequence.Save)
        self.actionSave_Changes.triggered.connect(self.saveModsList)


        self.actionMove_Mod_Up.triggered.connect(partial(self.moveMods.emit, -1))
        self.actionMove_Mod_Down.triggered.connect(partial(self.moveMods.emit,  1))

        self.actionMove_Mod_To_Top.triggered.connect(self.movemodstotop.emit)
        self.actionMove_Mod_To_Bottom.triggered.connect(self.movemodstobottom.emit)

        self.action_Quit.triggered.connect(self.safeQuitApp)

        self.action_Install_Fomod.triggered.connect(
                self.loadFomod)
        self.actionChoose_Mod_Folder.triggered.connect(
                self.chooseModFolder)


        self.SetupDone()




def quit_app():
    skylog.stop_listener()
    QApplication.quit()


# <editor-fold desc="__main__">
if __name__ == '__main__':
    from skymodman import managers
    from skymodman.qt_interface.models.modtable_tree import \
        ModTable_TreeModel

    app = QApplication(sys.argv)

    MM = managers.ModManager()

    w = ModManagerWindow(manager=MM)
    w.resize(QGuiApplication.primaryScreen().availableSize() * 3 / 5)
    w.show()

    sys.exit(app.exec_())
# </editor-fold>
