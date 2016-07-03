from functools import partial
import asyncio

from PyQt5.QtCore import (Qt,
                          pyqtSignal,
                          pyqtSlot,
                          QModelIndex,
                          # QDir,
                          QPropertyAnimation,
                          QSettings,
                          # QStandardPaths,
                          )
from PyQt5.QtGui import QGuiApplication, QKeySequence #, QFontDatabase
from PyQt5.QtWidgets import (QMainWindow,
                             QDialogButtonBox,
                             QMessageBox,
                             QFileDialog, QInputDialog,
                             QAction, QAbstractButton,  # QHeaderView,
                             QActionGroup, QProgressBar, QLabel)

from skymodman import exceptions
from skymodman.managers import modmanager as Manager
from skymodman.constants import (Tab as TAB,
                                 INIKey,
                                 INISection,
                                 qModels as M,
                                 qFilters as F,
                                 Column)
from skymodman.interface.models import (
    ModTable_TreeModel,
    ProfileListModel,
    ModFileTreeModel,
    ActiveModsListFilter,
    FileViewerTreeFilter)
from skymodman.interface.dialogs import message, NewProfileDialog
from skymodman.utils import withlogger, Notifier
from skymodman.utils.fsutils import checkPath, join_path
from skymodman.interface.install_helpers import InstallerUI

from skymodman.interface.designer.uic.manager_window_ui import Ui_MainWindow


@withlogger
class ModManagerWindow(QMainWindow, Ui_MainWindow):
    modListModified     = pyqtSignal()
    modListSaved        = pyqtSignal()

    windowInitialized   = pyqtSignal()

    newProfileLoaded    = pyqtSignal(str)

    moveMods            = pyqtSignal(int)
    moveModsToTop       = pyqtSignal()
    moveModsToBottom    = pyqtSignal()

    # noinspection PyUnresolvedReferences
    def __init__(self, **kwargs):
        """
        :param kwargs: anything to pass on the the base class constructors
        """
        super().__init__(**kwargs)

        self.LOGGER.info("Initializing ModManager Window")
        ModManagerWindow._this = self

        ## Interestingly, using the icon font as a font works just fine;
        ## One can do things like:
        ##    >>> btn_colview.setIcon(QIcon()) # just unsets current icon
        ##    >>> btn_colview.setText("\uf0db")
        ## and
        ##    >>> btn_colview.setStyleSheet("QToolButton {font-family: FontAwesome;}")
        ## to get the 'icon' for that character to show on the button.
        ## This reduces dependencies, but the qtawesome bindings do make configuring
        ## and tweaking the icon much easier, as well as allowing for stacking and
        ## animation, if desired.
        # _id = QFontDatabase.addApplicationFont("skymodman/thirdparty/qtawesome/fonts/fontawesome-webfont.ttf")

        # verify basic setup
        # self.check_setup()

        # for cancelling asyncio actions
        self.task = None

        # setup trackers for all of our models and proxies
        self.models  = {} #type: dict[M,QAbstractItemModel]
        self.filters = {} #type: dict[F,QSortFilterProxyModel]

        # slots (methods) to be called after __init__ is finished
        setupSlots = [
            self._setup_toolbar,
            self._setup_statusbar,
            self._setup_profile_selector,
            self._setup_table,
            self._setup_file_tree,
            self._setup_actions,
            self._setup_button_connections,
            self._setup_local_signals_connections,
            self._setup_slot_connections,
        ]

        ## Notifier object for the above 'setup...' slots to
        ## call when they've completed their setup process.
        ## After the final call, the UI will updated and
        ## presented to the user
        # TODO: turn the "notify_done" param and call into a decorator
        self.SetupDone = Notifier(len(setupSlots), self.update_UI)

        # connect the windowinit signal to the setup slots, and pass
        # them the notifier so they know who to call
        for s in setupSlots:
            self.windowInitialized.connect(partial(s, self.SetupDone))

        # setup the base ui
        self.setupUi(self)

        self._currtab = TAB.MODTABLE

        self.profile_name = None # type: str
        # track currently selected profile by index as well
        self.profile_selector_index = -1

        # make sure the correct initial pages are showing
        self.manager_tabs.setCurrentIndex(self._currtab.value)

        self._search_text=''

        # Let sub-widgets know the main window is initialized
        self.windowInitialized.emit()

        # default values for global preferences
        self.preferences = {
            "restore_window_size": True,
            "restore_window_pos": True,
            "load_last_profile": True
        }

        # read in prefs and other settings
        self.read_settings()

        # if "load_last_profile" is true, then the last profile will
        # be...um...loaded.
        if self.preferences["load_last_profile"]:
            self.load_profile_by_name(
                Manager.get_config_value(INIKey.LASTPROFILE, INISection.GENERAL)
                # Manager.conf.lastprofile
            )

    @property
    def current_tab(self):
        return self._currtab

    @current_tab.setter
    def current_tab(self, tabnum):
        self._currtab = TAB(tabnum)

    ##=============================================
    ## Application-wide settings management
    ##=============================================

    def read_settings(self):
        settings = QSettings("skymodman", "skymodman")

        settings.beginGroup("ManagerWindow")

        # load boolean prefs
        self.preferences["restore_window_size"] = settings.value(
            "restore_window_size", True)
        self.preferences["restore_window_pos"] = settings.value(
            "restore_window_pos", True)
        self.preferences["load_last_profile"] = settings.value(
            "load_last_profile", True)

        s_size = settings.value("size")
        if self.preferences["restore_window_size"] and s_size is not None:
            self.resize(s_size)
            # toSize() is not necessary as pyQt does the conversion to
            # QSize automagically.
            # self.resize(s_size.toSize())
        else:
            # noinspection PyArgumentList
            self.resize(QGuiApplication.primaryScreen().availableSize() * 5 / 7)

        s_pos = settings.value("pos")
        if self.preferences["restore_window_pos"] and s_pos is not None:
            self.move(s_pos)


    def write_settings(self):
        settings = QSettings("skymodman", "skymodman")

        settings.beginGroup("ManagerWindow")

        settings.setValue("restore_window_size", self.preferences["restore_window_size"])
        settings.setValue("restore_window_pos", self.preferences["restore_window_pos"])
        settings.setValue("load_last_profile", self.preferences["load_last_profile"])

        settings.setValue("size", self.size())
        settings.setValue("pos", self.pos())
        settings.endGroup()

    ##===============================================
    ## Setup UI Functionality (called once on first load)
    ##===============================================

    # <editor-fold desc="setup">

    def _setup_toolbar(self, notify_done):
        """We've got a few things to add to the toolbar:

        * Profile Selector
        * Add/remove profile buttons
        * change mod-order buttons (up/down/top/bottom)
        """
        self.LOGGER.debug("_setup_toolbar")

        # Profile selector and add/remove buttons
        self.file_toolBar.addSeparator()
        self.file_toolBar.addWidget(self.profile_group)
        self.file_toolBar.addActions([self.action_new_profile, self.action_delete_profile])

        # Action Group for the mod-movement buttons.
        # this just makes it easier to enable/disable them all at once
        self.file_toolBar.addSeparator()
        # mmag => "Mod Movement Action Group"
        mmag = self.mod_movement_group = QActionGroup(self)

        # mact => "Movement ACTion"
        macts = [self.action_move_mod_to_top,
                 self.action_move_mod_up,
                 self.action_move_mod_down,
                 self.action_move_mod_to_bottom,
                 ]

        mmag.setExclusive(False)
        for a in macts: mmag.addAction(a)

        self.file_toolBar.addActions(macts)

        ## This is for testing the progress indicator::
        # show_busybar_action = QAction("busy",self)
        # show_busybar_action.triggered.connect(self.show_statusbar_progress)
        # self.file_toolBar.addAction(show_busybar_action)

        notify_done()

    def _setup_statusbar(self, notify_done):
        """
        Add a progress bar to the status bar. Will be used for showing
        progress or activity of long-running processes.

        :param notify_done:
        """
        self.LOGGER.debug("_setup_statusbar")


        # putting the bar and label together into a container
        # widget caused the 'busy' animation not to play...
        # I never did figure out why, but adding them separately
        # bypasses the issue.
        self.sb_progress_label = QLabel("Working:", self)
        self.sb_progress_bar = QProgressBar(self)
        self.sb_progress_bar.setMaximumWidth(100)

        self.status_bar.addPermanentWidget(self.sb_progress_label)
        self.status_bar.addPermanentWidget(self.sb_progress_bar)
        self.sb_progress_label.setVisible(False)
        self.sb_progress_bar.setVisible(False)


        notify_done()

    def _setup_table(self, notify_done):
        """
        This is where we finally tell the manager to load all the actual data for the profile.

        :param notify_done:
        """
        self.LOGGER.debug("_setup_table")

        # Manager.load_active_profile_data()
        self.mod_table.setModel(
            ModTable_TreeModel(parent=self.mod_table))

        self.models[M.mod_table] = self.mod_table.model()

        # self.mod_table.loadData()

        # setup the animation to show/hide the search bar
        self.animate_show_search = QPropertyAnimation(
            self.modtable_search_box, b"maximumWidth")
        self.animate_show_search.setDuration(300)
        self.modtable_search_box.setMaximumWidth(0)

        self.modtable_search_box.textChanged.connect(
            self._clear_searchbox_style)

        def on_search_box_return():
            self._search_text = self.modtable_search_box.text()
            e = bool(self._search_text)
            self.action_find_next.setEnabled(e)
            self.action_find_previous.setEnabled(e)
            self.on_table_search()

        # i prefer searching only when i'm ready
        self.modtable_search_box.returnPressed.connect(
            on_search_box_return)

        # we don't actually use this yet...
        self.filters_dropdown.setVisible(False)

        notify_done()

    def _setup_profile_selector(self, notify_done):
        """
        Initialize the dropdown list for selecting profiles with the names of the profiles found on disk
        """
        self.LOGGER.debug("_setup_profile_selector")

        model = ProfileListModel()

        for name, profile in Manager.get_profiles(
                names_only=False):
            model.insertRows(data=profile)
        #     if name == Manager.active_profile().name:
        #         self.logger << "Setting {} as chosen profile".format(
        #             name)
        #         start_idx = model.rowCount() - 1
        #
        #         # see if we should enable the remove-profile button
        #         self.check_enable_profile_delete(name)

        self.profile_selector.setModel(model)

        # self.populate_profile_selector()

        # start with no selection
        self.profile_selector.setCurrentIndex(-1)
        # call this to make sure the delete button is inactive
        self.check_enable_profile_delete()

        # can't activate this signal until after the selector is populated
        self.profile_selector.currentIndexChanged.connect(
            self.on_profile_select)

        # let setup know we're done here
        notify_done()

    def _setup_file_tree(self, notify_done):
        """
        Create and populate the list of mod-folders shown on the
        filetree tab, as well as prepare the fileviewer pane to show
        files when a mod is selected
        """

        self.LOGGER.debug("_setup_file_tree")


        ##################################
        ## Mods List
        ##################################

        # setup filter proxy for active mods list
        mod_filter = self.filters[
            F.mod_list] = ActiveModsListFilter(
            self.filetree_modlist)

        mod_filter.setSourceModel(self.models[M.mod_table])
        mod_filter.setFilterCaseSensitivity(Qt.CaseInsensitive)

        # tell filter to read mod name
        mod_filter.setFilterKeyColumn(Column.NAME.value)

        # load and apply saved setting for 'activeonly' toggle
        self.__init_modlist_filter_state(mod_filter)

        # finally, set the filter as the model for the modlist
        self.filetree_modlist.setModel(mod_filter)
        # make sure we're just showing the mod name
        self.filetree_modlist.setModelColumn(Column.NAME.value)

        self._filetreesplitter.setSizes(
            [1, 500])  # just make the left one smaller ok?

        ##################################
        ## File Viewer
        ##################################
        ## model for tree view of files
        fileviewer_model = self.models[
            M.file_viewer] = ModFileTreeModel(
            parent=self.filetree_fileviewer)

        ## filter
        fileviewer_filter = self.filters[
            F.file_viewer] = FileViewerTreeFilter(
            self.filetree_fileviewer)

        fileviewer_filter.setSourceModel(fileviewer_model)
        fileviewer_filter.setFilterCaseSensitivity(Qt.CaseInsensitive)

        ## set model
        self.filetree_fileviewer.setModel(fileviewer_filter)

        ## resize 'name' column to be larger at first than 'path' column
        self.filetree_fileviewer.header().resizeSection(0, 400)
        # todo: remember user column resizes
        # self.models[M.file_viewer].rootPathChanged.connect(self.on_filetree_fileviewer_rootpathchanged)

        ## show new files when mod selection in list
        self.filetree_modlist.selectionModel().currentChanged.connect(
            lambda c, p: self.viewer_show_file_tree(
                mod_filter.mapToSource(c),
                mod_filter.mapToSource(p)))

        ## have escape key unfocus the filter boxes
        for f in [self.filetree_modfilter, self.filetree_filefilter]:
            f.escapeLineEdit.connect(f.clearFocus)

        # let setup know we're done here
        notify_done()

    def __init_modlist_filter_state(self, filter_):
        activeonly = Manager.get_profile_setting('activeonly', 'File Viewer')

        if activeonly is None:
            # if no profile loaded, set it unchecked and disable it
            activeonly=False
            self.filetree_activeonlytoggle.setEnabled(False)
        else:
            self.filetree_activeonlytoggle.setEnabled(True)

        # if activeonly is not None:
        # self.filetree_activeonlytoggle.setEnabled(True)
        filter_.onlyShowActive = activeonly

        # apply setting to box
        self.filetree_activeonlytoggle.setCheckState(
            Qt.Checked if activeonly else Qt.Unchecked)

        # and setup label text for first display
        self.update_modlist_label(activeonly)
        # else:
        #     # if no profile loaded, set it unchecked and disable it
        #     self.filetree_activeonlytoggle.setCheckState(Qt.Unchecked)
        #     filter_.onlyShowActive = False
        #
        #     self.update_modlist_label(False)
        #     self.filetree_activeonlytoggle.setEnabled(False)

    def _setup_actions(self, notify_done):
        """Connect all the actions to their appropriate slots/whatevers

        Actions:
            * action_load_profile
            * action_new_profile
            * action_delete_profile
            * action_rename_profile

            * action_preferences
            * action_quit

            * action_install_mod
            * action_reinstall_mod
            * action_manual_install
            * action_uninstall_mod
            * action_choose_mod_folder

            * action_edit_skyrim_ini
            * action_edit_skyrimprefs_ini

            * action_toggle_mod

            * action_undo
            * action_redo
            * action_save_changes
            * action_revert_changes

            * action_move_mod_up
            * action_move_mod_down
            * action_move_mod_to_top
            * action_move_mod_to_bottom
            * action_move_mod_up

            * action_show_search
            * action_find_next
            * action_find_previous
        """

        self.LOGGER.debug("_setup_actions")


        # action_new_profile
        self.action_new_profile.triggered.connect(
            self.on_new_profile_action)

        # action_delete_profile
        self.action_delete_profile.triggered.connect(
            self.on_remove_profile_action)

        # action_rename_profile
        self.action_rename_profile.triggered.connect(
            self.on_rename_profile_action)

        # --------------------------------------------------

        # action_preferences
        self.action_preferences.triggered.connect(
            self.edit_preferences)

        # action_quit
        self.action_quit.setShortcut(QKeySequence.Quit)
        # self.action_quit.triggered.connect(self.safe_quit)
        # connect quit action to close event
        self.action_quit.triggered.connect(self.close)

        # --------------------------------------------------

        # action_install_mod
        self.action_install_mod.triggered.connect(
            self.install_mod_archive)

        self.action_manual_install.triggered.connect(
            self.manual_install)

        # action_reinstall_mod
        self.action_reinstall_mod.triggered.connect(
            self.reinstall_mod)

        # action_uninstall_mod
        self.action_uninstall_mod.triggered.connect(
            self.uninstall_mod)

        # action_choose_mod_folder
        self.action_choose_mod_folder.triggered.connect(
            self.choose_mod_folder)

        # --------------------------------------------------

        # action edit ... ini

        # --------------------------------------------------

        # action_toggle_mod
        self.action_toggle_mod.triggered.connect(
            self.mod_table.toggleSelectionCheckstate)

        # --------------------------------------------------

        # * action_undo
        # * action_redo
        self.action_undo.setShortcut(QKeySequence.Undo)
        self.action_redo.setShortcut(QKeySequence.Redo)
        # connect undo/redo actions to table model
        self.action_undo.triggered.connect(self.mod_table.undo)
        self.action_redo.triggered.connect(self.mod_table.redo)

        # --------------------------------------------------

        # action_save_changes
        self.action_save_changes.setShortcut(
            QKeySequence.Save)
        self.action_save_changes.triggered.connect(
            self.on_save_command)

        self.action_revert_changes.triggered.connect(
            self.on_revert_command)

        # --------------------------------------------------

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

        # --------------------------------------------------

        # show search bar
        self.action_show_search.setShortcut(QKeySequence.Find)

        # find next
        self.action_find_next.setShortcut(QKeySequence.FindNext)
        self.action_find_next.triggered.connect(
            partial(self.on_table_search, 1))
        # find prev
        self.action_find_previous.setShortcut(QKeySequence.FindPrevious)
        self.action_find_previous.triggered.connect(
            partial(self.on_table_search, -1))

        notify_done()

    def _setup_button_connections(self, notify_done):
        """ Make the buttons do stuff
        """
        self.LOGGER.debug("_setup_buttons")

        # use a dialog-button-box for save/cancel;
        # have to specify by standard button type
        btn_apply = self.save_cancel_btnbox.button(
            QDialogButtonBox.Apply)
        btn_reset = self.save_cancel_btnbox.button(
            QDialogButtonBox.Reset)

        btn_apply.clicked.connect(
            self.action_save_changes.trigger)

        # enabled/disable the save/cancel buttons based
        # on the status of the save-changes action
        self.action_save_changes.changed.connect(
            lambda: self.save_cancel_btnbox.setEnabled(
                self.action_save_changes.isEnabled()))

        # connect reset button to the revert action
        btn_reset.clicked.connect(
            self.action_revert_changes.trigger)

        # using released since 'clicked' sends an extra
        # bool argument (which means nothing in this context
        # but messes up the callback)
        self.modtable_search_button.released.connect(
            self.toggle_search_box)

        notify_done()

    # inspector complains about alleged lack of "connect" function
    # noinspection PyUnresolvedReferences
    def _setup_local_signals_connections(self, notify_done):
        """
        SIGNALS:

        modListModified
        modListSaved

        windowInitialized

        newProfileLoaded

        moveMods
        moveModsToTop
        moveModsToBottom

        """
        self.LOGGER.debug("_setup_signals")

        self.newProfileLoaded.connect(self.on_profile_load)

        # connect the move up/down signal to the appropriate slot on view
        self.moveMods.connect(
            self.mod_table.onMoveModsAction)
        # same for the move to top/button signals
        self.moveModsToBottom.connect(
            self.mod_table.onMoveModsToBottomAction)
        self.moveModsToTop.connect(
            self.mod_table.onMoveModsToTopAction)

        notify_done()

    def _setup_slot_connections(self, notify_done):
        """
        SLOTS:



        self._enable_mod_move_actions

        on_new_profile_action
        on_remove_profile_action
        on_profile_select

        on_modlist_activeonly_toggle
        on_modlist_filterbox_textchanged

        self.on_table_unsaved_change
        self.on_make_or_clear_mod_selection
        self.on_undo_redo_event
        """
        self.LOGGER.debug("_setup_slots")


        ##===================================
        ## General/Main Window
        ##-----------------------------------

        # ensure the UI is properly updated when the tab changes
        self.manager_tabs.currentChanged.connect(
            self.on_tab_changed)

        # when new profile is selected
        # self.profile_selector.currentIndexChanged.connect(
        #     self.on_profile_select)

        # connect the undo event handler
        self.models[M.mod_table].undoevent.connect(
            self.on_undo_redo_event)

        ##===================================
        ## Mod Table Tab
        ##-----------------------------------

        # when the user first makes changes to the table or reverts
        # to a saved state from a modified state,  enable/disable
        # the save/cancel btns
        self.models[M.mod_table
        ].tablehaschanges.connect(
            self.on_table_unsaved_change)

        # depending on selection in table, the movement actions will be enabled
        # or disabled
        self.mod_table.enableModActions.connect(
            self.on_make_or_clear_mod_selection)
        self.mod_table.canMoveItems.connect(
            self._enable_mod_move_actions)

        ##===================================
        ## File Tree Tab
        ##-----------------------------------

        # connect the checkbox directly to the filter property
        self.filetree_activeonlytoggle.toggled[
            'bool'].connect(
            self.on_modlist_activeonly_toggle)

        # connect proxy to textchanged of filter box on listview
        self.filetree_modfilter.textChanged.connect(
            self.on_modlist_filterbox_textchanged)

        ## same for file tree
        self.filetree_filefilter.textChanged.connect(
            self.on_fileviewer_filter_textchanged)
        # self.filters[F.file_viewer].setFilterWildcard)

        # left the selectionModel() changed connection in the _setup function;
        # it's just easier to handle it there

        self.models[M.file_viewer].hasUnsavedChanges.connect(
            self.on_table_unsaved_change)

        notify_done()

    # </editor-fold>

    ##=============================================
    ## Event Handlers/Slots
    ##=============================================

    # <editor-fold desc="EventHandlers">

    @pyqtSlot(int)
    def on_tab_changed(self, newindex):
        """
        When the user switches tabs, make sure the proper GUI components are visible and active

        :param int newindex:
        """
        self.current_tab = TAB(newindex)
        self._update_visible_components()
        self._update_enabled_actions()

    @pyqtSlot(int)
    def on_profile_select(self, index):
        """
        When a new profile is chosen from the dropdown list, load all
        the appropriate data for that profile and replace the current
        data with it. Also show a message about unsaved changes to the
        current profile.

        :param index:
        """

        old_index = self.profile_selector_index

        if index == old_index:
            # ignore this; it just means that the user clicked cancel
            # in the "save changes" dialog and we're resetting the
            # displayed profile name.
            self.LOGGER.debug("Resetting profile name")
            return

        if index < 0:
            # we have a problem...
            self.LOGGER.error("No profile chosen?!")
        else:
            new_profile = self.profile_selector.currentData(
                Qt.UserRole).name

            # if no active profile, just load the selected one.
            # if somehow selected the same profile, do nothing
            if Manager.active_profile() is None or \
                            new_profile != Manager.active_profile().name:
                # check for unsaved changes to the mod-list
                reply = self.table_prompt_if_unsaved()

                # only continue to change profile if user does NOT click cancel
                # (or if there are no changes to save)
                if reply == QMessageBox.Cancel:
                    # reset the text in the profile selector;
                    # this SHOULDn't enter an infinite loop because,
                    # since we haven't yet changed self.profile_selector_index,
                    # now 'index' will be the same as 'old_index' at the top
                    # of this function and nothing else in the program will change
                    # (just the name shown in the profile selector)
                    self.profile_selector.setCurrentIndex(old_index)
                # if reply != QMessageBox.Cancel:
                else:
                    # update our variable which tracks the current index
                    self.profile_selector_index = index
                    # No => "Don't save changes, drop them"
                    if reply == QMessageBox.No:
                        # don't bother reverting, mods list is getting reset;
                        # just disable the buttons
                        self.on_table_unsaved_change(False)

                    self.LOGGER.info(
                        "Activating profile '{}'".format(
                            new_profile))

                    Manager.set_active_profile(new_profile)

                    self.logger << "Resetting views for new profile"

                    self.newProfileLoaded.emit(new_profile)

    @pyqtSlot('QString')
    def on_profile_load(self, profile_name):
        """
        Call with the name of the selected profile from the profile-
        selector combobox. Update the proper parts of the UI for the
        new information.

        :param str profile_name:
        """
        self.profile_name = profile_name

        self.check_enable_profile_delete()

        self._reset_table()  # this also loads the new data
        self._reset_file_tree()
        self._update_visible_components()
        self._update_enabled_actions()

    @pyqtSlot()
    def on_new_profile_action(self):
        """
        When the 'add profile' button is clicked, create and show a small dialog for the user to choose a name for the new profile.
        """
        popup = NewProfileDialog(
            combobox_model=self.profile_selector.model())

        # display popup, wait for close and check signal
        if popup.exec_() == popup.Accepted:
            # add new profile if they clicked ok
            new_profile = Manager.new_profile(popup.final_name,
                                              popup.copy_from)

            self.profile_selector.model().addProfile(new_profile)

            # set new profile as active and load data
            self.load_profile_by_name(new_profile.name)

            # self.profile_selector.setCurrentIndex(
            #     self.profile_selector.findText(new_profile.name,
            #                                    Qt.MatchFixedString))

    @pyqtSlot()
    def on_remove_profile_action(self):
        """
        Show a warning about irreversibly deleting the profile, then, if the user accept the warning, proceed to delete the profile from disk and remove its entry from the profile selector.
        """
        profile = Manager.active_profile()

        if message('warning', 'Confirm Delete Profile',
                   'Delete "' + profile.name + '"?',
                   'Choosing "Yes" below will remove this profile '
                   'and all saved information within it, including '
                   'customized load-orders, ini-edits, etc. Note '
                   'that installed mods will not be affected. This '
                   'cannot be undone. Do you wish to continue?'):
            Manager.delete_profile(
                self.profile_selector.currentData())
            self.profile_selector.removeItem(
                self.profile_selector.currentIndex())

    @pyqtSlot()
    def on_rename_profile_action(self):
        """
        Query the user for a new name, then ask the mod-manager backend to rename the profile folder.
        """

        newname = \
        QInputDialog.getText(self, "Rename Profile", "New name")[0]

        if newname:
            try:
                Manager.rename_profile(newname)
            except exceptions.ProfileError as pe:
                message('critical', "Error During Rename Operation",
                        text=str(pe), buttons='ok')

    @pyqtSlot(bool)
    def on_make_or_clear_mod_selection(self, has_selection):
        """
        Enable or disable buttons and actions that rely on having a selection in the mod table.
        """
        # self.LOGGER << "modtable selection->{}".format(has_selection)
        for a in (self.mod_movement_group,
                  self.action_uninstall_mod,
                  self.action_reinstall_mod,
                  self.action_toggle_mod):
            a.setEnabled(has_selection)

    @pyqtSlot(bool)
    def on_table_unsaved_change(self, unsaved_changes_present):
        """
        When a change is made to the table, enable or disable certain actions depending on whether the table's current state matches the last savepoint or not.

        :param unsaved_changes_present:
        """
        # self.LOGGER << "table status: {}".format("dirty" if unsaved_changes_present else "clean")

        for widgy in [self.save_cancel_btnbox,
                      self.action_save_changes,
                      self.action_revert_changes]:
            widgy.setEnabled(
                unsaved_changes_present)

    @pyqtSlot(bool)
    def on_modlist_activeonly_toggle(self, checked):
        """
        Toggle showing/hiding inactive mods in the Mods list on the file-tree tab
        :param checked: state of the checkbox
        """
        # self.LOGGER << "ActiveOnly toggled->{}".format(checked)

        self.filters[F.mod_list].setOnlyShowActive(checked)
        self.update_modlist_label(checked)
        Manager.set_profile_setting(INIKey.ACTIVEONLY,
                                    INISection.FILEVIEWER,
                                    checked)

    @pyqtSlot('QString')
    def on_modlist_filterbox_textchanged(self, text):
        """
        Updates the proxy filtering, and notifies the label
        to change its 'mods shown' count.
        :param text:
        """

        filt = self.filters[F.mod_list]
        filt.setFilterWildcard(text)
        self.update_modlist_label(filt.onlyShowActive)

    @pyqtSlot('QString')
    def on_fileviewer_filter_textchanged(self, text):
        """
        Query the modfiles table in the db for files matching the filter
        string given by `text`. The resulting matches are fed to the proxy
        filter on the file viewer which uses them to make sure that matching
        files are shown in the tree regardless of whether their parent
        directories match the filter or not.

        :param str text:
        """
        # don't bother querying db for empty string,
        # the filter will ignore the matched files anyway
        if not text:
            self.filters[F.file_viewer].setFilterWildcard(text)
        else:
            db = Manager.db._con

            sqlexpr = r'%' + text.replace('?', '_').replace('*',
                                                            r'%') + r'%'

            matches = [r[0] for r in db.execute(
                "SELECT filepath FROM modfiles WHERE directory=? AND filepath LIKE ?",
                (self.models[M.file_viewer].modname, sqlexpr))]

            self.filters[F.file_viewer].setMatchingFiles(matches)

            self.filters[F.file_viewer].setFilterWildcard(text)
            self.filetree_fileviewer.expandAll()

    @pyqtSlot(str, str)
    def on_undo_redo_event(self, undo_text, redo_text):
        """Update the undo/redo text to reflect the passed text.  If an argument is passed as ``None`` or an empty string, that button will instead be disabled."""
        # self.LOGGER << "Undoevent({}, {})".format(undo_text, redo_text)

        for action, text, default_text in [
            (self.action_undo, undo_text, "Undo"),
            (self.action_redo, redo_text, "Redo")]:
            if text:
                action.setText(text)
                action.setEnabled(True)
            else:
                action.setText(default_text)
                action.setEnabled(False)

    @pyqtSlot()
    def on_save_command(self):
        """
        Save command does different things depending on which
        tab is active.
        :return:
        """
        if self.current_tab == TAB.MODTABLE:
            self.mod_table.saveChanges()
        elif self.current_tab == TAB.FILETREE:
            self.models[M.file_viewer].save()

    @pyqtSlot()
    def on_revert_command(self):
        """
        Undo all changes made to the table since the last savepoint
        """
        if self.current_tab == TAB.MODTABLE:
            self.mod_table.revertChanges()
        elif self.current_tab == TAB.FILETREE:
            self.models[M.file_viewer].revert()

    def on_table_search(self, direction=1):
        """
        Tell the view to search for 'text'; depending on success, we
        will change the appearance of the search text and the status
        bar message
        """

        if self._search_text:
            found = self.mod_table.search(self._search_text,
                                          direction)

            if not found:
                if found is None:
                    # this means we DID find the text, but it was the same
                    # row that we started on
                    self.modtable_search_box.setStyleSheet(
                        'QLineEdit { color: gray }')
                    self.status_bar.showMessage(
                        "No more results found")
                else:
                    # found was False
                    self.modtable_search_box.setStyleSheet(
                        'QLineEdit { color: tomato }')
                    self.status_bar.showMessage("No results found")
                return

        # text was found or was '': reset style sheet if one is present
        if self.modtable_search_box.styleSheet():
            self.modtable_search_box.setStyleSheet('')
            self.status_bar.clearMessage()

    def _clear_searchbox_style(self):
        if self.modtable_search_box.styleSheet():
            self.modtable_search_box.setStyleSheet('')
            self.status_bar.clearMessage()

    # </editor-fold>

    ##=============================================
    ## Statusbar operations
    ##=============================================

    def show_statusbar_progress(self, text="Working:", minimum=0, maximum=0, show_bar_text=False):
        """
        Set up and display the small progress bar on the bottom right of the window
        (in the status bar). If `minimum` == `maximum` == 0, the bar will be in
        indeterminate ('busy') mode: this is useful for indicating to the user
        that *something* is going on on the background during activities that may
        take a moment or two to complete, so the user need not worry
        that their last command had no effect.

        :param text: Text that will be shown to the left of the progress bar
        :param minimum: Minumum value for the bar
        :param maximum: Maximum value for the bar
        :param show_bar_text: Whether to show the bar's text (% done by default)
        """
        self.sb_progress_label.setText(text)
        self.sb_progress_bar.reset()
        self.sb_progress_bar.setRange(minimum, maximum)
        self.sb_progress_bar.setTextVisible(show_bar_text)

        self.sb_progress_label.setVisible(True)
        self.sb_progress_bar.setVisible(True)

    def update_statusbar_progress(self, value, labeltext=None):
        """
        Set the status-progress-bar's value to `value`. If provided,
        also change the label to `labeltext`; otherwise leave the
        label as is. This method can be used as a callback.

        :param value:
        :param labeltext:
        :return:
        """
        self.sb_progress_bar.setValue(value)
        if labeltext is not None:
            self.sb_progress_label.setText(labeltext)

    def hide_statusbar_progress(self):
        """
        Make the statusbar-progress go away.
        """
        self.sb_progress_bar.setVisible(False)
        self.sb_progress_label.setVisible(False)

    ##=============================================
    ## Reset UI components
    ##=============================================

    def _reset_table(self):
        """
        Called when a new profile is loaded or some other major change occurs
        """
        self.mod_table.loadData()
        self.modtable_search_box.clear() # might be good enough
        # self.toggle_search_box(ensure_state=0)



    def _reset_file_tree(self):
        # clear the filter boxes
        self.filetree_modfilter.clear()
        self.filetree_filefilter.clear()

        # clear the file tree view
        self.models[M.file_viewer].setRootPath(None)

        # update the label and checkbox on the modlist
        self.__init_modlist_filter_state(
            self.filters[F.mod_list])




    ##===============================================
    ## UI Helper Functions
    ##===============================================

    def check_setup(self):
        """
        Make sure that every absolutely required piece of config
        information is available before everything gets fully loaded.
        So far, this means:
                * Skyrim-installation directory
        """

        # must have a configured skyrim installation folder
        skydir = Manager.get_directory(INIKey.SKYRIMDIR)
        # skydir = Manager.get_config_value(INIKey.SKYRIMDIR, INISection.DIRECTORIES)
        # if not Manager.conf["dir_skyrim"]:
        if not skydir:
            if message("information", "Select Skyrim Installation", 'Before the manager runs, please take a moment to specify the folder where Skyrim itself is installed. Click "OK" to show the folder selection dialog.', buttons=('ok', 'cancel'), default_button='ok'):
                self.select_skyrim_dir()
            # else:
            #     self.safe_quit()

    # def update_UI(self, *args):
    def update_UI(self):
        self._update_visible_components()

    def _update_visible_components(self):
        """
        Some manager components should be hidden on certain tabs
        """
        # tab=self.current_tab

        all_components = [
            self.save_cancel_btnbox,      # 0
            self.next_button,             # 1
            self.modtable_search_button,  # 2
            self.modtable_search_box,     # 3
        ]

        # selector defining the visible components for each tab
        visible = {
            TAB.MODTABLE:  [1, 0, 1, 1],
            TAB.FILETREE:  [1, 0, 0, 0],
        }

        for comp, isvis in zip(all_components, visible[self.current_tab]):
            comp.setVisible(isvis)


    def _update_enabled_actions(self):
        """
        Some manager actions should be disabled on certain tabs
        """
        # tab=self.current_tab

        all_components = [
            self.mod_movement_group,     # 0
            self.action_toggle_mod,      # 1
            self.action_save_changes,    # 2
            self.action_revert_changes,  # 3
            self.action_undo,            # 4
            self.action_redo,            # 5
            self.action_find_next,       # 6
            self.action_find_previous,   # 7
            self.action_uninstall_mod,   # 8
        ]

        # this is a selector that, depending on how it is
        # modified below, will allow us to set every
        # component to its appropriate enabled state
        s = [False]*len(all_components)

        if self.current_tab == TAB.MODTABLE:
            tmodel = self.models[M.mod_table]
            s[0] = s[1] = s[8] = self.mod_table.selectionModel().hasSelection()
            s[2] = s[3] = tmodel.isDirty
            s[4],  s[5] = tmodel.canundo, tmodel.canredo
            s[6] = s[7] = bool(self._search_text)
        elif self.current_tab == TAB.FILETREE:
            s[2] = s[3] = self.models[M.file_viewer].has_unsaved_changes


        for comp, select in zip(all_components, s):
            comp.setEnabled(select)

    def update_button_from_action(self, action, button):
        """
        Synchronize a button's state with that of a given QAction

        :param QAction action:
        :param QAbstractButton button:
        :return:
        """
        button.setEnabled(action.isEnabled())
        button.setToolTip(action.toolTip())
        button.setVisible(action.isVisible())

    def _enable_mod_move_actions(self, enable_moveup, enable_movedown):
        """
        Enable or disable the mod-movement actions

        :param bool enable_moveup: whether to enable the move-up/move-to-top actions
        :param bool enable_movedown: whether to enable the move-down/move-to-bottom actions
        """
        for action in [self.action_move_mod_to_bottom,
                       self.action_move_mod_down]:
            action.setEnabled(enable_movedown)

        for action in [self.action_move_mod_to_top,
                       self.action_move_mod_up]:
            action.setEnabled(enable_moveup)

    def toggle_search_box(self):
        """
        Show or hide the search box based on its current state.
        """
        # 0=hidden, 1=shown
        state = 0 if self.modtable_search_box.width() > 0 else 1

        # ref to QAnimationProperty
        an = self.animate_show_search

        # animate expansion from 0px -> 300px width when showing;
        # animate collapse from 300->0 when hiding
        an.setStartValue([300,0][state])
        an.setEndValue([0,300][state])
        an.start()

        # also, focus the text field if we're showing it
        if state:
            self.modtable_search_box.setFocus()
        else:
            # or clear the focus and styling if we're hiding
            self.modtable_search_box.clearFocus()
            self.modtable_search_box.clear()

    def update_modlist_label(self, inactive_hidden):
        """
        Change the label beside the "hide inactive mods" check box to reflect its current state.

        :param inactive_hidden:
        """
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
        When the currently selected item changes in the modlist, change
        the fileviewer to show the files from the new mod's folder.

        :param QModelIndex indexCur: Currently selected index
        :param QModelIndex indexPre: Previously selected index
        """
        if not indexCur.isValid(): return

        moddir = indexCur.internalPointer().directory

        # p = Manager.conf.paths.dir_mods / moddir

        # add the name of the mod directory to the path of the
        # main mods folder
        p = join_path(Manager.get_config_value(INIKey.MODDIR, INISection.DIRECTORIES), moddir)

        # self.models[M.file_viewer].setRootPath(str(p))
        self.models[M.file_viewer].setRootPath(p)

    def table_prompt_if_unsaved(self):
        """
        Check for unsaved changes to the mods list and show a prompt if
        any are found. Clicking yes will save the changes and mark the
        table clean, while clicking no will simply disable the apply/
        revert buttons as IF the table were clean. This is because
        this is intended to be used right before an action like loading
        a new profile (thus forcing a full table reset) or quitting the
        app.

        :return: the value of the button the user clicked (QMessageBox.[Yes/No/Cancel]),
        or None if the message box was not shown
        """
        # check for unsaved changes to the mod-list
        if Manager.active_profile() is not None and self.mod_table.model().isDirty:
            ok = QMessageBox(QMessageBox.Warning, 'Unsaved Changes',
                             'Your mod install-order has unsaved changes. '
                             'Would you like to save them before continuing?',
                             QMessageBox.No | QMessageBox.Yes | QMessageBox.Cancel).exec_()

            if ok == QMessageBox.Yes:
                self.mod_table.saveChanges()
            return ok
        # if clean, return None to indicate that the calling operation
        # may contine as normal
        return None

    def check_enable_profile_delete(self):
        """
        enable the remove and rename actions unless there is no profile
        loaded or the profile name matches that of the default profile
        (likely 'default')
        """

        if self.profile_name is None:
            self.action_delete_profile.setEnabled(False)
            self.action_delete_profile.setToolTip('Remove Profile')
            self.action_rename_profile.setEnabled(False)


        elif self.profile_name.lower() == 'default':
            self.action_delete_profile.setEnabled(False)
            self.action_delete_profile.setToolTip(
                'Cannot Remove Default Profile')
            self.action_rename_profile.setEnabled(False)
        else:
            self.action_delete_profile.setEnabled(True)
            self.action_delete_profile.setToolTip('Remove Profile')
            self.action_rename_profile.setEnabled(True)

    def load_profile_by_name(self, name):
        """
        Have the profile selector show and activate the profile with the given name
        :param name:
        """
        # set new profile as active and load data;
        # search the selector's model for a name that matches the arg
        self.profile_selector.setCurrentIndex(
            self.profile_selector.findText(name,
                                           Qt.MatchFixedString))

    ###=============================================
    ## Actions
    ## ---------------------------------------------
    ## stuff the user can do; available as slots for
    ## signals to connect to
    ###=============================================

    #<editor-fold desc="actions">

    @pyqtSlot()
    def edit_preferences(self):
        """
        Show a dialog allowing the user to change some application-wide preferences
        """
        # todo
        message(text="Preferences?")

    @pyqtSlot()
    def choose_mod_folder(self):
        """
        Show dialog allowing user to choose a mod folder.

        If a profile is currently loaded, this will set a directory override for the mods folder that applies to this profile only. The default directory can be set in the preferences dialog. When no profile is loaded, this will instead set the default directory.
        """
        # noinspection PyTypeChecker
        moddir = QFileDialog.getExistingDirectory(
            self,
            "Choose Directory Containing Installed Mods",
            Manager.get_directory(INIKey.MODDIR)
            # Manager.get_config_value(INIKey.MODDIR, INISection.DIRECTORIES)
            # Manager.conf['dir_mods']
        )

        # update config with new path
        if checkPath(moddir):
            Manager.set_directory(INIKey.MODDIR, moddir)
            # Manager.set_config_value(INIKey.MODDIR,
            #                          INISection.DIRECTORIES,
            #                          moddir)
            # Manager.conf.updateConfig(INIKey.MODDIR,
            #                           INISection.GENERAL,
            #                           moddir)

            # reverify and reload the mods.
            if not Manager.validate_mod_installs():
                self.mod_table.model().reloadErrorsOnly()

    @pyqtSlot()
    def select_skyrim_dir(self):
        """
        Show file selection dialog for user to select the directory
        where Skyrim is installed
        """
        skydir = QFileDialog.getExistingDirectory(
            self,
            "Select Skyrim Installation",
            Manager.get_directory(INIKey.SKYRIMDIR) or "")

        # update config with new path
        if checkPath(skydir):
            Manager.set_directory(INIKey.SKYRIMDIR, skydir)
            # Manager.set_config_value(INIKey.SKYRIMDIR,
            #                           INISection.DIRECTORIES,
            #                           skydir)
            # Manager.conf.updateConfig(INIKey.SKYRIMDIR,
            #                           INISection.GENERAL,
            #                           skydir)
        else:
            self.safe_quit()

    # noinspection PyTypeChecker,PyArgumentList
    def install_mod_archive(self, manual=False):
        """
        Install a mod from an archive.

        :param bool manual: If false, attempt to use
        the guided FOMOD installer if a fomod config is found, otherwise
        simply unpack the archive. If true, show the file-system view of
        the archive and allow the user to choose which parts to install.

        """
        # todo: default to home folder or something instead of current dir
        # filename=QFileDialog.getOpenFileName(
        #     self, "Select Mod Archive",
        #     QDir.currentPath() + "/res",
        #     "Archives [zip, 7z, rar] (*.zip *.7z *.rar);;All Files(*)")[0]

        # short-circuit for testing
        filename='res/7ztest.7z'
        if filename:
            self.installui = InstallerUI() # helper class
            if manual:
                self.show_statusbar_progress("Loading archive:")

                self.task = asyncio.get_event_loop().create_task(
                    self.installui.do_manual_install(filename,
                                                     self.hide_statusbar_progress))

            else:
                # show busy indicator while installer loads
                self.show_statusbar_progress("Preparing installer:")

                self.task = asyncio.get_event_loop().create_task(
                    self.installui.do_install(filename, self.hide_statusbar_progress))

                # todo: add callback to show the new mod if install succeeded
                # self.task.add_done_callback(self.on_new_mod())


    def manual_install(self):
        """
        Activate a non-guided install
        """
        self.install_mod_archive(manual=True)

    def reinstall_mod(self):
        """
        Repeat the installation process for the given mod
        """
        # todo: implement re-running the installer
        row = self.mod_table.currentIndex().row()
        if row > -1:
            mod = self.models[M.mod_table][row]
            self.LOGGER << "Here's where we'd reinstall this mod."

    def uninstall_mod(self):
        """
        Remove the selected mod from the virtual installation directory
        """
        # todo: implement removing the mod
        row = self.mod_table.currentIndex().row()
        if row > -1:
            mod = self.models[M.mod_table][row]
            self.LOGGER << "Here's where we'd uninstall this mod."

    #</editor-fold>

    ##=============================================
    ## Qt Overrides
    ##=============================================

    def closeEvent(self, event):
        """
        Override close event to check for unsaved changes and to save settings to disk
        :param event:
        """

        # only ignore the close event if the user clicks cancel
        # on the confirm window
        if self.table_prompt_if_unsaved() == QMessageBox.Cancel:
            event.ignore()
        else:
            self.write_settings()
            event.accept()


# <editor-fold desc="__main__">
# if __name__ == '__main__':
#     import sys
#
#     app = QApplication(sys.argv)
#     Manager.init()
#
#     w = ModManagerWindow()
#     # noinspection PyArgumentList
#     w.resize(QGuiApplication.primaryScreen().availableSize() * 3 / 5)
#     w.show()
#
#     sys.exit(app.exec_())
# </editor-fold>
