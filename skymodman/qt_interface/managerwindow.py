from functools import partial

from PyQt5.QtCore import (Qt,
                          pyqtSignal,
                          pyqtSlot,
                          QModelIndex,
                          QDir,
                          # QStandardPaths,
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
from skymodman.qt_interface.models import (
    ProfileListModel,
    ModFileTreeModel,
    ActiveModsListFilter)
from skymodman.qt_interface.views import ModTable_TreeView
from skymodman.utils import withlogger, Notifier, checkPath


@withlogger
class ModManagerWindow(QMainWindow, Ui_MainWindow):
    modListModified     = pyqtSignal()
    modListSaved        = pyqtSignal()

    windowInitialized   = pyqtSignal()
    modNameBeingEdited  = pyqtSignal(str)

    deleteProfileAction = pyqtSignal(str)

    moveMods            = pyqtSignal(int)
    moveModsToTop       = pyqtSignal()
    moveModsToBottom    = pyqtSignal()

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
        self.models  = {} #type: dict[M,QAbstractItemModel]
        self.filters = {} #type: dict[F,QSortFilterProxyModel]

        # slots (methods) to be called after __init__ is finished
        setupSlots = [
            self._setup_profile_selector,
            self._setup_table,
            self._setup_file_tree,
            self._setup_actions,
            self._connect_buttons,
        ]

        ## Notifier object for the above 'setup...' slots to
        ## call when they've completed their setup process.
        ## After the final call, the UI will updated and
        ## presented to the user
        self.SetupDone = Notifier(len(setupSlots), self.update_UI)

        # connect the windowinit signal to the setup slots, and pass
        # them the notifier so they know who to call (...the 'Busters, of course)
        for s in setupSlots:
            self.windowInitialized.connect(partial(s, self.SetupDone))

        # setup the base ui
        self.setupUi(self)

        # init mod table (since it is not included in the base ui file)
        self.mod_table = ModTable_TreeView(parent=self,
                                           manager=self.Manager)

        # keep track of changes made to mod list
        # self.file_tree_modified = False

        # set placeholder fields
        self.loaded_fomod = None

        # make sure the correct initial pages are showing
        self.manager_tabs.setCurrentIndex(0)
        self.installerpages.setCurrentIndex(0)

        # ensure the UI is properly updated when the tab changes
        self.manager_tabs.currentChanged.connect(
                self.update_UI)

        # Let sub-widgets know the main window is initialized
        self.windowInitialized.emit()

    @property
    def Manager(self):
        return self._manager


    ##===============================================
    ## Setup UI Functionality (called once on first load)
    ##===============================================

    # <editor-fold desc="setup">
    def _setup_table(self, notify_done):
        """
        This is where we finally tell the manager to load all the actual data for the profile.

        :param notify_done:
        """
        self.Manager.loadActiveProfileData()
        self.mod_table.initUI(self.installed_mods_layout)

        self.models[M.mod_table] = self.mod_table.model()

        self.mod_table.loadData()

        # when the user first makes changes to the table or reverts to a saved state from a modified state,  enable/disable the save/cancel btns
        self.models[M.mod_table
        ].tablehaschanges.connect(
                self.on_table_unsaved_change)

        self.mod_table.enableModActions.connect(
            self.on_make_or_clear_mod_selection)
        self.mod_table.canMoveItems.connect(
            self.enable_move_buttons)

        # connect the move up/down signals
        # to the appropriate slot on view
        self.moveMods.connect(self.mod_table.onMoveModsAction)
        # same for the move to top/button signals
        self.moveModsToBottom.connect(
                self.mod_table.onMoveModsToBottomAction)
        self.moveModsToTop.connect(
                self.mod_table.onMoveModsToTopAction)

        self.models[M.mod_table].undoevent.connect(
            self.on_undo_redo_event)

        notify_done()

    def _setup_profile_selector(self, notify_done):
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
                self.logger << "Setting {} as chosen profile".format(
                    name)
                start_idx = model.rowCount() - 1

                # see if we should enable the remove-profile button
                self.enable_profile_delete(name)

        self.profile_selector.setModel(model)
        self.profile_selector.setCurrentIndex(start_idx)
        self.profile_selector.currentIndexChanged.connect(
                self.on_profile_change)
        self.new_profile_button.clicked.connect(
                self.on_new_profile_click)
        self.remove_profile_button.clicked.connect(
                self.on_remove_profile_click)

        # let setup know we're done here
        notify_done()


    def _setup_file_tree(self, notify_done):
        """
        Create and populate the list of mod-folders shown on the filetree tab, as well as prepare the fileviewer pane to show files when a mod is selected
        """
        ##################################
        ## Mods List
        ##################################

        #setup filter proxy for active mods list
        mod_filter = self.filters[
            F.mod_list] = ActiveModsListFilter(
                self.filetree_modlist)

        mod_filter.setSourceModel(self.models[M.mod_table])

        mod_filter.setFilterCaseSensitivity(Qt.CaseInsensitive)

        # tell filter to read mod name
        mod_filter.setFilterKeyColumn(Column.NAME.value)

        # load saved setting for 'activeonly' toggle

        _activeonly=self.Manager.getProfileSetting('File Viewer','activeonly')
        mod_filter.onlyShowActive = _activeonly

        # apply setting to box
        self.filetree_activeonlytoggle.setCheckState(Qt.Checked if _activeonly else Qt.Unchecked)

        # and setup label text for first display
        self.update_modlist_label(_activeonly)

        # connect the checkbox directly to the filter property
        self.filetree_activeonlytoggle.toggled[
            'bool'].connect(
                self.on_modlist_activeonly_toggle)

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
        proxy2source = lambda c, p: self.viewer_show_file_tree(
                mod_filter.mapToSource(c), mod_filter.mapToSource(p))
        self.filetree_modlist.selectionModel().currentChanged.connect(
            # self.viewer_show_file_tree)
            proxy2source)



        # let setup know we're done here
        notify_done()

    def _setup_actions(self, notify_done):
        """Create additional actions, and make some tweaks to pre-existing ones

        Actions:
            * action_install_fomod
            * action_choose_mod_folder
            * action_quit
            * action_load_profile
            * action_new_profile
            * action_delete_profile
            * action_edit_skyrim_ini
            * action_edit_skyrimprefs_ini
            * action_undo
            * action_redo
            * action_toggle_mod
            * action_save_changes
            * action_move_mod_up
            * action_move_mod_down
            * action_move_mod_to_top
            * action_move_mod_to_bottom
            * action_move_mod_up
        """

        # * action_undo
        # * action_redo
        self.action_undo.setShortcut(QKeySequence.Undo)
        self.action_redo.setShortcut(QKeySequence.Redo)
        # connect undo/redo actions to table model
        self.action_undo.triggered.connect(self.mod_table.undo)
        self.action_redo.triggered.connect(self.mod_table.redo)

        # action_toggle_mod
        self.action_toggle_mod.triggered.connect(
                self.mod_table.toggleSelectionCheckstate)

        # action_save_changes
        self.action_save_changes.setShortcut(
                QKeySequence.Save)
        self.action_save_changes.triggered.connect(
                self.mod_table.saveChanges)

        # action_move_mod_up
        # action_move_mod_down
        self.action_move_mod_up.triggered.connect(
                partial(self.moveMods.emit, -1))
        self.action_move_mod_down.triggered.connect(
                partial(self.moveMods.emit, 1))

        # action_move_mod_to_top
        # action_move_mod_to_bottom
        self.action_move_mod_to_top.triggered.connect(
                self.moveModsToTop.emit)
        self.action_move_mod_to_bottom.triggered.connect(
                self.moveModsToBottom.emit)

        # action_quit
        self.action_quit.triggered.connect(self.safe_quit)

        # action_install_fomod
        self.action_install_fomod.triggered.connect(
                self.load_fomod)
        # action_choose_mod_folder
        self.action_choose_mod_folder.triggered.connect(
                self.choose_mod_folder)

        notify_done()

    def _connect_buttons(self, notify_done):
        """ Make the buttons do stuff
        """
        # use a dialog-button-box for save/cancel
        # have to specify by standard button type
        self.save_cancel_btnbox.button(
                QDialogButtonBox.Apply).clicked.connect(
                self.mod_table.saveChanges)
        self.save_cancel_btnbox.button(
                QDialogButtonBox.Reset).clicked.connect(
                self.mod_table.revertChanges)

        notify_done()

    # </editor-fold>

    ##===============================================
    ## UI Helper Functions
    ##===============================================

    # def update_UI(self, *args):
    def update_UI(self):
        if self.loaded_fomod is None:
            self.fomod_tab.setEnabled(False)

        curtab = self.manager_tabs.currentIndex()

        self.save_cancel_btnbox.setVisible(
                curtab in [TAB.MODLIST, TAB.FILETREE])

        self.next_button.setVisible(curtab == TAB.INSTALLER)

    def enable_move_buttons(self, enable_moveup, enable_movedown):
        for action in [self.action_move_mod_to_bottom,
                       self.action_move_mod_down]:
            action.setEnabled(enable_movedown)

        for action in [self.action_move_mod_to_top,
                       self.action_move_mod_up]:
            action.setEnabled(enable_moveup)

    def update_modlist_label(self, inactive_hidden):
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

    # noinspection PyUnusedLocal
    def viewer_show_file_tree(self, indexCur, indexPre):
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


    def table_prompt_if_unsaved(self):
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
                self.table_save_mod_list()
            else:
                # don't bother reverting, mods list is getting reset;
                # just disable the buttons
                self.on_table_unsaved_change(False)


    def enable_profile_delete(self, profile_name):
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


    def reset_views_on_profile_change(self):
        """For now, this just repopulates the mod-table. There might be more to it later"""

        # TODO: send out a signal to when the profile is changed that everything needing to update will be listening to
        self.LOGGER << "About to repopulate table"
        self.mod_table.loadData()

        # self.filters[F.mod_list].

        # self.updateFileTreeModList()

        self.update_UI()


    # <editor-fold desc="EventHandlers">
    @pyqtSlot('int')
    def on_profile_change(self, index):
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
            self.table_prompt_if_unsaved()

            self.LOGGER.info(
                    "Activating profile '{}'".format(new_profile))

            # fixme: change this setter to a method so it's clear how much happens at this point
            self.Manager.active_profile = new_profile

            # if this is the profile 'default', disable the remove button
            self.enable_profile_delete(new_profile)


            self.reset_views_on_profile_change()

    def on_new_profile_click(self):
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

    def on_remove_profile_click(self):
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

    def on_make_or_clear_mod_selection(self, has_selection):
        """
        Enable or disable buttons and actions that rely on having a selection in the mod table.
        """
        self.enable_move_buttons(has_selection, has_selection)

        self.action_toggle_mod.setEnabled(has_selection)

    def on_table_unsaved_change(self, unsaved_changes_present):
        self.save_cancel_btnbox.setEnabled(
            unsaved_changes_present)
        self.action_save_changes.setEnabled(
            unsaved_changes_present)

    def on_modlist_filterbox_textchanged(self, text):
        # Updates the proxy filtering, and notifies the label
        # to change its 'mods shown' count.
        filt = self.filters[F.mod_list]
        filt.setFilterWildcard(text)
        self.update_modlist_label(filt.onlyShowActive)

    def on_modlist_activeonly_toggle(self, checked):
        # self.filetree_activeonlytoggle.toggled[
        #     'bool'].connect(
        #         mod_filter.setOnlyShowActive)
        # self.filetree_activeonlytoggle.toggled[
        #     'bool'].connect(
        #         self.on_modlist_activeonly_toggle)
        # self.update_modlist_label)
        self.filters[F.mod_list].setOnlyShowActive(checked)
        self.update_modlist_label(checked)
        self.Manager.setProfileSetting('File Viewer', 'activeonly', checked)


    def on_undo_redo_event(self, undo_text, redo_text):
        """Update the undo/redo text to reflect the passed text.  If an argument is passed as ``None``, that button will instead be disabled."""
        for action, text, default_text in [
            (self.action_undo, undo_text, "Undo"),
            (self.action_redo, redo_text, "Redo")]:
            if text:
                action.setText(text)
                action.setEnabled(True)
            else:
                action.setText(default_text)
                action.setEnabled(False)


    # </editor-fold>

    ##===============================================
    ## Action Handlers
    ##===============================================

    # noinspection PyArgumentList
    def load_fomod(self):

        # mimes = [m for m in QImageReader.supportedMimeTypes()]
        # print(mimes)
        # mimes = ['application/x-7z-compressed']
        mimes = ['application/xml']
        # start_locs = QStandardPaths.standardLocations(
        #     QStandardPaths.HomeLocation)
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

    def choose_mod_folder(self):
        """
        Show dialog allowing user to choose a mod folder.
        """
        # noinspection PyTypeChecker
        moddir = QFileDialog.getExistingDirectory(
                self,
                "Choose Directory Containing Installed Mods",
                self.Manager.Config['dir_mods'])

        # update config with new path
        if checkPath(moddir):
            self.Manager.Config.updateConfig(moddir,
                                             INIKey.MODDIR,
                                             INISection.GENERAL)

            # reverify and reload the mods.
            if not self.Manager.validateModInstalls():
                self.mod_table.model().reloadErrorsOnly()

                # def get_tab(self, index: int):
                #     return self.manager_tabs.widget(index)

    def safe_quit(self):
        """
        Show a prompt if there are any unsaved changes, then close the program.
        """
        self.table_prompt_if_unsaved()
        self.Manager.DB.shutdown()

        quit_app()


# noinspection PyArgumentList
def quit_app():
    skylog.stop_listener()
    QApplication.quit()


# <editor-fold desc="__main__">
if __name__ == '__main__':
    from skymodman import managers
    # from skymodman.qt_interface.models.modtable_tree import \
    #     ModTable_TreeModel
    from PyQt5.QtCore import QAbstractItemModel, QSortFilterProxyModel
    import sys

    app = QApplication(sys.argv)

    MM = managers.ModManager()

    w = ModManagerWindow(manager=MM)
    # noinspection PyArgumentList
    w.resize(QGuiApplication.primaryScreen().availableSize() * 3 / 5)
    w.show()

    sys.exit(app.exec_())
# </editor-fold>
