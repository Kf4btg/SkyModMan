from functools import partial
import asyncio

from PyQt5.QtCore import (Qt,
                          pyqtSignal,
                          pyqtSlot,
                          QModelIndex,
                          QDir,
                          QPropertyAnimation,
                          # QStandardPaths,
                          )
from PyQt5.QtGui import QGuiApplication, QKeySequence
from PyQt5.QtWidgets import (QApplication,
                             QMainWindow,
                             QDialogButtonBox,
                             QMessageBox,
                             QFileDialog, QInputDialog,
                             QAction, QAbstractButton,  # QHeaderView,
                             QActionGroup, QProgressBar, QLabel)

from skymodman import skylog, exceptions
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
from skymodman.interface.widgets import message, NewProfileDialog
from skymodman.utils import withlogger, Notifier, checkPath

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
            self._connect_buttons,
            self._connect_local_signals,
            self._attach_slots,
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

        # set placeholder fields
        self.loaded_fomod = None

        self._currtab = TAB.MODTABLE
        # make sure the correct initial pages are showing
        self.manager_tabs.setCurrentIndex(self._currtab.value)
        self.installerpages.setCurrentIndex(0)

        self._search_text=''

        # Let sub-widgets know the main window is initialized
        self.windowInitialized.emit()

    @property
    def current_tab(self):
        return self._currtab

    @current_tab.setter
    def current_tab(self, tabnum):
        self._currtab = TAB(tabnum)

    ##===============================================
    ## Setup UI Functionality (called once on first load)
    ##===============================================

    # <editor-fold desc="setup">

    def _setup_toolbar(self, notify_done):
        """We've got a few things to add to the toolbar"""

        # Profile selector and add/remove buttons
        self.file_toolBar.addSeparator()
        self.file_toolBar.addWidget(self.profile_group)
        self.file_toolBar.addActions([self.action_new_profile, self.action_delete_profile])

        # Action Group for the mod-movement buttons.
        # this just makes it easier to enable/disable them all at once
        self.file_toolBar.addSeparator()
        mmag = self.mod_movement_group = QActionGroup(self)

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
        # show_busybar_action.triggered.connect(self.show_sb_progress)
        # self.file_toolBar.addAction(show_busybar_action)

        notify_done()

    def _setup_statusbar(self, notify_done):
        """
        Add a progress bar to the status bar. Will be used for showing
        progress or activity of long-running processes.

        :param notify_done:
        :return:
        """

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

    def show_sb_progress(self, text="Working:", minimum=0, maximum=0, show_bar_text=False):
        self.sb_progress_label.setText(text)
        self.sb_progress_bar.reset()
        self.sb_progress_bar.setRange(minimum, maximum)
        self.sb_progress_bar.setTextVisible(show_bar_text)

        self.sb_progress_label.setVisible(True)
        self.sb_progress_bar.setVisible(True)

    def update_sb_progress(self, value, labeltext=None):
        self.sb_progress_bar.setValue(value)
        if labeltext is not None:
            self.sb_progress_label.setText(labeltext)

    def hide_sb_progress(self):
        self.sb_progress_bar.setVisible(False)
        self.sb_progress_label.setVisible(False)

    def _setup_table(self, notify_done):
        """
        This is where we finally tell the manager to load all the actual data for the profile.

        :param notify_done:
        """
        Manager.load_active_profile_data()
        self.mod_table.setModel(
                ModTable_TreeModel(parent=self.mod_table))

        self.models[M.mod_table] = self.mod_table.model()

        self.mod_table.loadData()

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

    def _reset_table(self):
        """
        Called when a new profile is loaded or some other major change occurs
        """
        self.mod_table.loadData()
        self.modtable_search_box.clear() # might be good enough
        # self._show_search_box(ensure_state=0)

    def _setup_profile_selector(self, notify_done):
        """
        Initialize the dropdown list for selecting profiles with the names of the profiles found on disk
        """
        model = ProfileListModel()

        start_idx = 0
        for name, profile in Manager.get_profiles(
                names_only=False):
            model.insertRows(data=profile)
            if name == Manager.active_profile().name:
                self.logger << "Setting {} as chosen profile".format(
                    name)
                start_idx = model.rowCount() - 1

                # see if we should enable the remove-profile button
                self.enable_profile_delete(name)

        self.profile_selector.setModel(model)
        self.profile_selector.setCurrentIndex(start_idx)

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

        # load and apply saved setting for 'activeonly' toggle
        self.__setup_modlist_filter_state(mod_filter)

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
        self.filetree_fileviewer.header().resizeSection(0,400)
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

    def __setup_modlist_filter_state(self, filter_):
        activeonly = Manager.get_profile_setting('File Viewer',
                                                     'activeonly')
        filter_.onlyShowActive = activeonly

        # apply setting to box
        self.filetree_activeonlytoggle.setCheckState(
            Qt.Checked if activeonly else Qt.Unchecked)

        # and setup label text for first display
        self.update_modlist_label(activeonly)

    def _reset_file_tree(self):
        # clear the filter boxes
        self.filetree_modfilter.clear()
        self.filetree_filefilter.clear()

        # clear the file tree view
        self.models[M.file_viewer].setRootPath(None)

        # update the label and checkbox on the modlist
        self.__setup_modlist_filter_state(
                self.filters[F.mod_list])

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

        # action_new_profile
        self.action_new_profile.triggered.connect(
            self.on_new_profile_action)

        # action_delete_profile
        self.action_delete_profile.triggered.connect(
            self.on_remove_profile_action)

        # action_rename_profile
        self.action_rename_profile.triggered.connect(
            self.on_rename_profile_action)

        #--------------------------------------------------

        # action_preferences
        self.action_preferences.triggered.connect(
            self.edit_preferences)


        # action_quit
        self.action_quit.setShortcut(QKeySequence.Quit)
        self.action_quit.triggered.connect(self.safe_quit)

        # --------------------------------------------------

        # action_install_mod
        self.action_install_mod.triggered.connect(
            self.install_mod_archive)
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

        #--------------------------------------------------

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

    def _connect_buttons(self, notify_done):
        """ Make the buttons do stuff
        """
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
        self.action_save_changes.changed.connect(lambda: self.save_cancel_btnbox.setEnabled(self.action_save_changes.isEnabled()))

        # connect reset button to the revert action
        btn_reset.clicked.connect(
                self.action_revert_changes.trigger)

        # using released since 'clicked' sends an extra
        # bool argument (which means nothing in this context
        # but messes up the callback)
        self.modtable_search_button.released.connect(
                self._show_search_box)

        notify_done()

    def _connect_local_signals(self, notify_done):
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

        for slot in [self.enable_profile_delete,
                     self._reset_table,
                    self._reset_file_tree,
                    self._visible_components_for_tab,
            self._enabled_actions_for_tab,
                     ]:
            self.newProfileLoaded.connect(slot)

        # connect the move up/down signal to the appropriate slot on view
        self.moveMods.connect(
                self.mod_table.onMoveModsAction)
        # same for the move to top/button signals
        self.moveModsToBottom.connect(
                self.mod_table.onMoveModsToBottomAction)
        self.moveModsToTop.connect(
                self.mod_table.onMoveModsToTopAction)

        notify_done()

    def _attach_slots(self, notify_done):
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

        ##===================================
        ## General/Main Window
        ##-----------------------------------

        # ensure the UI is properly updated when the tab changes
        self.manager_tabs.currentChanged.connect(
                self.on_tab_changed)

        # when new profile is selected
        self.profile_selector.currentIndexChanged.connect(
                self.on_profile_select)

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

        self.models[M.file_viewer].hasUnsavedChanges.connect(self.on_table_unsaved_change)

        notify_done()

    # </editor-fold>

    ##===============================================
    ## UI Helper Functions
    ##===============================================

    # def update_UI(self, *args):
    def update_UI(self):
        self.fomod_tab.setEnabled(self.loaded_fomod is not None)

        self._visible_components_for_tab()

        # self.save_cancel_btnbox.setVisible(
        #         curtab in [TAB.MODTABLE, TAB.FILETREE])
        #
        # self.next_button.setVisible(curtab == TAB.INSTALLER)
        # self.modtable_search_button.setVisible(curtab == TAB.MODTABLE)
        # self.modtable_search_box.setVisible(curtab == TAB.MODTABLE)

    def _visible_components_for_tab(self):
        """
        Some manager components should be hidden on certain tabs

        :return:
        """
        tab=self.current_tab

        all_components = [
            self.save_cancel_btnbox,      # 0
            self.next_button,             # 1
            self.modtable_search_button,  # 2
            self.modtable_search_box,     # 3
        ]

        visible = {
            TAB.MODTABLE:  [1, 0, 1, 1],
            TAB.FILETREE:  [1, 0, 0, 0],
            TAB.INSTALLER: [0, 1, 0, 0]
        }

        for comp, isvis in zip(all_components, visible[tab]):
            comp.setVisible(isvis)

    def _enabled_actions_for_tab(self):
        """
        Some manager actions should be disabled on certain tabs

        :return:
        """
        tab=self.current_tab

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

        if tab == TAB.MODTABLE:
            tmodel = self.models[M.mod_table]
            s[0] = s[1] = s[8] = self.mod_table.selectionModel().hasSelection()
            s[2] = s[3] = tmodel.isDirty
            s[4],  s[5] = tmodel.canundo, tmodel.canredo
            s[6] = s[7] = bool(self._search_text)
        elif tab == TAB.FILETREE:
            s[2] = s[3] = self.models[M.file_viewer].has_unsaved_changes

        # else: Installer has everything disabled

        for comp, select in zip(all_components, s):
            comp.setEnabled(select)

    def update_button_from_action(self, action, button):
        """

        :param QAction action:
        :param QAbstractButton button:
        :return:
        """
        button.setEnabled(action.isEnabled())
        button.setToolTip(action.toolTip())
        button.setVisible(action.isVisible())

    def _enable_mod_move_actions(self, enable_moveup, enable_movedown):
        for action in [self.action_move_mod_to_bottom,
                       self.action_move_mod_down]:
            action.setEnabled(enable_movedown)

        for action in [self.action_move_mod_to_top,
                       self.action_move_mod_up]:
            action.setEnabled(enable_moveup)

    def _show_search_box(self, ensure_state=None):
        """
        If `ensure_state` is None, expand or collapse the search box
        depending on its current state. Otherwise, only change the
        state of the search box if it differs from `ensure_state.`

        :param int ensure_state: states are 0 (Hidden) or 1 (Shown)
        """

        an = self.animate_show_search
        # if ensure_state is not None and ensure_state in [0,1]:
        #     if ensure_state==1:
        #         if self.modtable_search_box.width() > 0: return
        #     elif self.modtable_search_box.width() == 0 :return
        #
        #     state=ensure_state
        # else:
        #     state = 0 if self.modtable_search_box.width() > 0 else 1
        state = 0 if self.modtable_search_box.width() > 0 else 1

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

        moddir = indexCur.internalPointer().directory

        p = Manager.conf.paths.dir_mods / moddir

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
        (likely 'default') enable the remove and rename actions
        :param profile_name:
        """
        if profile_name.lower() == 'default':
            self.action_delete_profile.setEnabled(False)
            self.action_delete_profile.setToolTip(
                    'Cannot Remove Default Profile')
            self.action_rename_profile.setEnabled(False)
        else:
            self.action_delete_profile.setEnabled(True)
            self.action_delete_profile.setToolTip('Remove Profile')
            self.action_rename_profile.setEnabled(True)

    # <editor-fold desc="EventHandlers">

    def on_tab_changed(self, newindex):
        self.current_tab = TAB(newindex)
        self._visible_components_for_tab()
        self._enabled_actions_for_tab()

    @pyqtSlot('int')
    def on_profile_select(self, index):
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
            if new_profile == Manager.active_profile().name:
                # somehow selected the same profile; do nothing
                return

            # check for unsaved changes to the mod-list
            self.table_prompt_if_unsaved()

            self.LOGGER.info(
                    "Activating profile '{}'".format(new_profile))

            Manager.set_active_profile(new_profile)

            self.logger << "Resetting views for new profile"
            self.newProfileLoaded.emit(new_profile)

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
            self.profile_selector.setCurrentIndex(
                    self.profile_selector.findText(new_profile.name,
                                                   Qt.MatchFixedString))

    def on_remove_profile_action(self):
        """
        Show a warning about irreversibly deleting the profile.
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

    def on_rename_profile_action(self):

        newname = QInputDialog.getText(self, "Rename Profile", "New name")[0]

        if newname:
            try:
                Manager.rename_profile(newname)
            except exceptions.ProfileError as pe:
                message('critical', "Error During Rename Operation", text=str(pe), buttons='ok')


    def on_make_or_clear_mod_selection(self, has_selection):
        """
        Enable or disable buttons and actions that rely on having a selection in the mod table.
        """
        # self.LOGGER << "modtable selection->{}".format(has_selection)

        self.mod_movement_group.setEnabled(has_selection)
        self.action_toggle_mod.setEnabled(has_selection)
        self.action_uninstall_mod.setEnabled(has_selection)

    def on_table_unsaved_change(self, unsaved_changes_present):
        # self.LOGGER << "table status: {}".format("dirty" if unsaved_changes_present else "clean")

        for widgy in [self.save_cancel_btnbox,
                      self.action_save_changes,
                      self.action_revert_changes]:
            widgy.setEnabled(
                    unsaved_changes_present)

    def on_modlist_activeonly_toggle(self, checked):
        # self.LOGGER << "ActiveOnly toggled->{}".format(checked)

        self.filters[F.mod_list].setOnlyShowActive(checked)
        self.update_modlist_label(checked)
        Manager.set_profile_setting('File Viewer', 'activeonly', checked)

    def on_modlist_filterbox_textchanged(self, text):
        # Updates the proxy filtering, and notifies the label
        # to change its 'mods shown' count.
        filt = self.filters[F.mod_list]
        filt.setFilterWildcard(text)
        self.update_modlist_label(filt.onlyShowActive)

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

            sqlexpr = r'%'+text.replace('?','_').replace('*',r'%')+r'%'

            matches = [r[0] for r in db.execute("SELECT filepath FROM modfiles WHERE directory=? AND filepath LIKE ?", (self.models[M.file_viewer].modname, sqlexpr))]

            self.filters[F.file_viewer].setMatchingFiles(matches)

            self.filters[F.file_viewer].setFilterWildcard(text)
            self.filetree_fileviewer.expandAll()

    def on_undo_redo_event(self, undo_text, redo_text):
        """Update the undo/redo text to reflect the passed text.  If an argument is passed as ``None``, that button will instead be disabled."""
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

    def on_save_command(self):
        """
        Save command does different things depending on which
        tab is active.
        :return:
        """
        tab = self.manager_tabs.currentIndex()

        if tab == TAB.MODTABLE:
            self.mod_table.saveChanges()
        elif tab == TAB.FILETREE:
            self.models[M.file_viewer].save()

    def on_revert_command(self):
        tab = self.manager_tabs.currentIndex()

        if tab == TAB.MODTABLE:
            self.mod_table.revertChanges()
        elif tab == TAB.FILETREE:
            self.models[M.file_viewer].revert()

    def on_table_search(self, direction=1):
        """
        Tell the view to search for 'text'; depending on success, we
        will change the appearance of the search text and the status
        bar message

        """

        if self._search_text:
            found = self.mod_table.search(self._search_text, direction)

            if not found:
                if found is None:
                    # this means we DID find the text, but it was the same
                    # row that we started on
                    self.modtable_search_box.setStyleSheet(
                            'QLineEdit { color: gray }')
                    self.status_bar.showMessage("No more results found")
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

    def _on_search_box_return(self):
        """
        Hit return in the search box; update the saved search text and search
        """
        self._search_text = self.modtable_search_box.text()

        e = bool(self._search_text)

        self.action_find_next.setEnabled(e)
        self.action_find_previous.setEnabled(e)

        self.on_table_search()

    def _clear_searchbox_style(self):
        if self.modtable_search_box.styleSheet():
            self.modtable_search_box.setStyleSheet('')
            self.status_bar.clearMessage()


    # </editor-fold>

    ##===============================================
    ## Action Handlers
    ##===============================================

    def edit_preferences(self):
        # todo
        message(text="Preferences?")

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



    # noinspection PyTypeChecker,PyArgumentList
    def install_mod_archive(self):
        # todo: default to home folder or something instead of current dir
        filename=QFileDialog.getOpenFileName(
            self, "Select Mod Archive",
            QDir.currentPath() + "/res",
            "Archives [zip, 7z, rar] (*.zip *.7z *.rar);;All Files(*)")[0]
        if filename:

            # show busy indicator while installer loads
            self.show_sb_progress("Preparing installer:")


            self.task = asyncio.get_event_loop().create_task(
                self._handle_install(filename))

            # todo: add callback to show the new mod if install succeeded
            # self.task.add_done_callback(self.on_new_mod())


    async def _handle_install(self, archive):
        from tempfile import TemporaryDirectory
        with TemporaryDirectory() as tmpdir:
            try:
                # await asyncio.sleep(5)
                installer = await Manager.extract_fomod(archive, tmpdir)

                if installer is not None:
                    self.hide_sb_progress()
                    from skymodman.interface.widgets.fomod_installer_wizard import FomodInstaller

                    wizard = FomodInstaller(installer, tmpdir)

                    wizard.exec_()

                    del FomodInstaller
                else:
                    print("not fomod")
                    # extract_location =  # should extract the archive
                    # if extract_location is None:
                    #     extract_location="The mod structure is incorrect"

                    # message("information", text=extract_location)
            finally:
                self.hide_sb_progress()
                del TemporaryDirectory



    def choose_mod_folder(self):
        """
        Show dialog allowing user to choose a mod folder.
        """
        # noinspection PyTypeChecker
        moddir = QFileDialog.getExistingDirectory(
                self,
                "Choose Directory Containing Installed Mods",
                Manager.conf['dir_mods'])

        # update config with new path
        if checkPath(moddir):
            Manager.conf.updateConfig(moddir,
                                      INIKey.MODDIR,
                                      INISection.GENERAL)

            # reverify and reload the mods.
            if not Manager.validate_mod_installs():
                self.mod_table.model().reloadErrorsOnly()

    # def get_tab(self, index: int):
    #     return self.manager_tabs.widget(index)

    def safe_quit(self):
        """
        Show a prompt if there are any unsaved changes, then close the program.
        """
        self.table_prompt_if_unsaved()
        Manager.db.shutdown()

        quit_app()



# noinspection PyArgumentList
def quit_app():
    skylog.stop_listener()
    QApplication.quit()


# <editor-fold desc="__main__">
if __name__ == '__main__':
    import sys

    app = QApplication(sys.argv)
    Manager.init()

    w = ModManagerWindow()
    # noinspection PyArgumentList
    w.resize(QGuiApplication.primaryScreen().availableSize() * 3 / 5)
    w.show()

    sys.exit(app.exec_())
# </editor-fold>
