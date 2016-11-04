from functools import partial
import asyncio

from PyQt5 import QtWidgets, QtGui
# specifically import some frequently used names
from PyQt5.QtCore import Qt, pyqtSignal, pyqtSlot
from PyQt5.QtWidgets import QMessageBox

from skymodman import constants, Manager
from skymodman.constants import qModels as M, Tab as TAB
from skymodman.constants.keystrings import (Dirs as KeyStr_Dirs,
                                            # INI as KeyStr_INI,
                                            UI as KeyStr_UI)

from skymodman.interface import models, app_settings, profile_handler #, ui_utils
# from skymodman.interface.dialogs import message
from skymodman.interface.widgets import alerts_button
from skymodman.interface.install_helpers import InstallerUI
from skymodman.log import withlogger #, icons
from skymodman.utils.fsutils import check_path #, join_path

from skymodman.interface.designer.uic.manager_window_ui import Ui_MainWindow

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

@withlogger
class ModManagerWindow(QtWidgets.QMainWindow, Ui_MainWindow):
    # noinspection PyArgumentList
    modListModified     = pyqtSignal()
    # noinspection PyArgumentList
    modListSaved        = pyqtSignal()

    # noinspection PyArgumentList
    moveMods            = pyqtSignal(int)
    # noinspection PyArgumentList
    moveModsToTop       = pyqtSignal()
    # noinspection PyArgumentList
    moveModsToBottom    = pyqtSignal()

    instance = None # type: ModManagerWindow

    def __init__(self, **kwargs):
        """
        :param kwargs: anything to pass on the the base class constructors
        """
        super().__init__(**kwargs)

        # this field will contain the reference to the main ModManager
        # backend (encapsulated in a QObject wrapper)
        self.Manager = None
        """:type: skymodman.interface.qmodmanager.QModManager"""

        self.LOGGER.info("Initializing ModManager Window")
        ModManagerWindow.instance = self

        # setup the base ui
        self.setupUi(self)

        self.setWindowTitle(constants.APPTITLE)

        # for cancelling asyncio actions
        self.task = None

        # setup trackers for all of our models and proxies
        self.models  = {} #type: dict [M,QtCore.QAbstractItemModel]
        self.filters = {} #type: dict [F,QtCore.QSortFilterProxyModel]

        self._currtab = TAB.MODTABLE

        # get a helping hand...ler
        self.profile_helper = profile_handler.ProfileHandler(self)

        # make sure the correct initial pages are showing
        self.manager_tabs.setCurrentIndex(self._currtab.value)

        ## The undo framework.
        ## Each tab will have its own UndoStack; when the user changes
        ## tabs, the stack for that tab will become the active stack
        ## in the main undoGroup, and the undo/redo actions will thus
        ## only affect that tab.
        self.undoManager = QtWidgets.QUndoGroup(self)
        # initialize a map of the undo stacks
        self.undo_stacks = {
            TAB.MODTABLE: None, # type: QtWidgets.QUndoStack
            TAB.FILETREE: None  # type: QtWidgets.QUndoStack
        }

        # ---------------------------------------------------
        ## Create an action for clearing mods that cannot be found
        ## from the mods list. Will be shown in the right-click menu
        ## of the mods table when the errors column is visible.
        # noinspection PyArgumentList
        self.action_clear_missing = QtWidgets.QAction(
            "Remove Missing Mods",
            self,
            objectName="action_clear_missing",
            icon=QtGui.QIcon().fromTheme("edit-clear"),
            triggered=self.remove_missing)

        # Call the setup methods which do not rely on the data backend
        self._setup_ui_interface()

        # this map is used during 'update_enabled_actions()'
        self._action_components = {
            "mmg": self.mod_movement_group,     # 0
            "atm": self.action_toggle_mod,      # 1
            "asc": self.action_save_changes,    # 2
            "arc": self.action_revert_changes,  # 3
            "afn": self.action_find_next,       # 4
            "afp": self.action_find_previous,   # 5
            "aum": self.action_uninstall_mod,   # 6
            "acm": self.action_clear_missing,
            "asa": self.action_select_all,
            "asn": self.action_select_none,

            # can't use this on the mod table; might be able to use it
            # on the fileview?
            # "asi": self.action_select_inverse,
        }

        # define and read the application settings
        self.init_settings()

        # finally, make sure the right stuff is showing
        self._update_visible_components()

        # self.update_UI()

    @property
    def current_tab(self):
        return self._currtab

    @current_tab.setter
    def current_tab(self, tabnum):
        self._currtab = TAB(tabnum)

    ##=============================================
    ## Application-wide settings management
    ##=============================================

    def init_settings(self):
        """
        Add the necessary properties and callbacks to the AppSettings instance
        """

        ## define the boolean/toggle preferences ##
        app_settings.add(KeyStr_UI.RESTORE_WINSIZE, True)

        app_settings.add(KeyStr_UI.RESTORE_WINPOS, True)

        ## setup window-state prefs ##

        # define some functions to pass as on_read callbacks
        def _resize(size):
            # noinspection PyArgumentList
            self.resize(size
                        if size and app_settings.Get(
                                KeyStr_UI.RESTORE_WINSIZE)
                        else QtGui.QGuiApplication.primaryScreen()
                                .availableSize() * 5 / 7)

        def _move(pos):
            if pos and app_settings.Get(KeyStr_UI.RESTORE_WINPOS):
                self.move(pos)

        # add the properties w/ callbacks
        app_settings.add("size", self.size, apply=_resize)
        app_settings.add("pos", self.pos, apply=_move)

        # TODO: handle and prioritize the SMM_PROFILE env var
        app_settings.add(KeyStr_UI.PROFILE_LOAD_POLICY,
                         constants.ProfileLoadPolicy.last.value, int)

        ## ----------------------------------------------------- ##
        ## Now that we've defined them all, time to read them in ##

        # this will possibly:
        #  a) move the window
        #  b) resize the window
        app_settings.read_and_apply()

    ##===============================================
    ## Setup UI Functionality (called once on first load)
    ##===============================================

    def manager_ready(self):
        """To be called by the app entry point after the modmanager
        has been initialized and registered globally. This starts
        the data-loading part of the program"""

        # make sure that whoever called this isn't lying
        if not Manager():
            self.LOGGER.error("Manager NOT ready!")
            return

        self.LOGGER << "Notified Manager ready"

        # keep local ref
        self.Manager = Manager()

        # connect to signals
        self.Manager.alertsChanged.connect(self.update_alerts)

        # do an initial check of the Manager directories
        self.Manager.check_dirs()

        # perform some setup that requires the manager
        self._setup_data_interface()

        # load the initial profile (or not, depending on profile load policy)
        self.profile_helper.load_initial_profile(
            app_settings.Get(KeyStr_UI.PROFILE_LOAD_POLICY)
        )

    def _setup_ui_interface(self):
        """
        Calls setup methods which don't rely on any data being loaded.
        For convenience, these methods have been prefixed with '_setupui'
        to indicate their data-independence
        """
        self._setupui_alerts_button()
        self._setupui_toolbar()
        self._setupui_statusbar()
        self._setupui_table() # must wait for manager for model

        self._setupui_actions()
        self._setupui_button_connections()
        self._setupui_local_signals_connections()

    def _setup_data_interface(self):
        """
        Called after the mod manager has been assigned; invokes
        setup methods that require the data backend.
        """

        self._setup_profile_selector()
        self._setup_table_model()
        self._setup_files_tab_views()

        # undo manager relies (for now) on the undo stack of both
        # the mod table and file viewer tabs being setup. The fileviewer
        # undostack relies (for now) on a reference to the Mod Manager.
        # Thus, _setup_undo_manager() must be called down here.
        # For now.
        self._setup_undo_manager()

    ##=============================================
    ## Data-independent setup
    ##=============================================
    #<editor-fold desc="interface setup">

    def _setupui_alerts_button(self):
        """
        Adding a drop-down textbox to the toolbar isn't exactly straightforward.
        We need to create a toolbutton that pops up a menu. That menu
        then requires a QWidgetAction added to it that itself has the
        textbox set as its default widget. The toolbutton can then
        be added to the toolbar.
        """

        self.alerts_button = alerts_button.AlertsButton(self.file_toolBar)
        self.alerts_button.setObjectName("alerts_button")

        ## OK...so, since QWidget.setVisible() does not work for items
        ## added to a toolbar with addWidget(?!), we need to save the
        ## action returned by the addWidget() method (who knew?!) and
        ## use its setVisible() &c. methods.
        ## is this returned action the same as "show_popup_action"
        ## of the button?? I have no idea!!!
        self.action_show_alerts = self.file_toolBar.addWidget(
            self.alerts_button)
        self.action_show_alerts.setObjectName("action_show_alerts")

        # initially hide the alerts indicator since there is no manager yet
        self.action_show_alerts.setVisible(False)

    def _setupui_toolbar(self):
        """We've got a few things to add to the toolbar:

        * Profile Selector
        * Add/remove profile buttons
        * change mod-order buttons (up/down/top/bottom)
        """
        self.LOGGER.debug("_setup_toolbar")

        # Profile selector and add/remove buttons

        # since qtoolbars don't allow spacer widgets, we'll "fake" one
        # with a plain old qwidget.
        # noinspection PyArgumentList
        spacer = QtWidgets.QWidget()
        spacer.setSizePolicy(QtWidgets.QSizePolicy.Expanding,
                             QtWidgets.QSizePolicy.Expanding)

        # add it to the toolbar
        self.file_toolBar.addWidget(spacer)

        # now when we add the profile_group box, it will be right-aligned
        self.file_toolBar.addWidget(self.profile_group)
        self.file_toolBar.addActions([self.action_new_profile,
                                      self.action_delete_profile])


        # Action Group for the mod-movement buttons.
        # this just makes it easier to enable/disable them all at once
        # mmag => "Mod Movement Action Group"
        mmag = self.mod_movement_group = QtWidgets.QActionGroup(self)

        # mact => "Movement ACTion"
        macts = [self.action_move_mod_to_top,
                 self.action_move_mod_up,
                 self.action_move_mod_down,
                 self.action_move_mod_to_bottom,
                 ]

        mmag.setExclusive(False)
        for a in macts: mmag.addAction(a)

        # let's actually make a new, vertical toolbar
        # for these and add it to the side of the mods table.
        movement_toolbar = QtWidgets.QToolBar(self.installed_mods_tab)
        movement_toolbar.setOrientation(Qt.Vertical)
        ## Note to : adding it to the left of the table never worked,
        ## for some reason...it always overlapped the table. Managed
        ## to get it placed on the right, though.
        self.installed_mods_layout.addWidget(
            movement_toolbar, 1,
            self.installed_mods_layout.columnCount(), -1, 1)
        movement_toolbar.addActions(macts)

        self.movement_toolbar = movement_toolbar

        ## This is for testing the progress indicator::
        # show_busybar_action = QAction("busy",self)
        # show_busybar_action.triggered.connect(self.show_statusbar_progress)
        # self.file_toolBar.addAction(show_busybar_action)

    def _setupui_statusbar(self):
        """
        Add a progress bar to the status bar. Will be used for showing
        progress or activity of long-running processes.
        """
        self.LOGGER.debug("_setup_statusbar")

        # putting the bar and label together into a container
        # widget caused the 'busy' animation not to play...
        # I never did figure out why, but adding them separately
        # bypasses the issue.
        self.sb_progress_label = QtWidgets.QLabel("Working:", self)
        self.sb_progress_bar = QtWidgets.QProgressBar(self)
        self.sb_progress_bar.setMaximumWidth(100)

        self.status_bar.addPermanentWidget(self.sb_progress_label)
        self.status_bar.addPermanentWidget(self.sb_progress_bar)
        self.sb_progress_label.setVisible(False)
        self.sb_progress_bar.setVisible(False)

    def _setupui_table(self):
        """
        Prepare the mods-display table and related functionality
        """
        self.LOGGER.debug("_setup_table_UI")

        self.mod_table.setupui(self.modtable_search_box)

        # handler for [dis|en]abling the search actions
        def on_enable_searchactions(enable):
            self.action_find_next.setEnabled(enable)
            self.action_find_previous.setEnabled(enable)

        # connect signals from table
        self.mod_table.enableSearchActions.connect(on_enable_searchactions)
        self.mod_table.setStatusMessage.connect(self.on_status_text_change_request)

        # we don't actually use this yet...
        self.filters_dropdown.setVisible(False)

    def _setupui_file_tree(self):
        """
        Setup the sizes of the file-viewer mod selector and tree view.
        Models will be set up later.
        """

        self.LOGGER.debug("_setup_file_tree")

        self._filetreesplitter.setSizes(
            [1, 500])  # just make the left one smaller ok?

        ## resize 'name' column to be larger at first than 'path' column
        self.filetree_fileviewer.header().resizeSection(0, 400)
        # todo: remember user column resizes

    def _setupui_actions(self):
        """
        Connect all the actions to their appropriate slots/whatevers;
        also set some shortcut sequences
        """

        self.LOGGER.debug("_setup_actions")

        # create containers to enable easily setting up connections/
        # shortcuts via simple loops

        # tuple(action, slot_on_trigger)
        connections = [
            (self.action_new_profile        ,
                self.profile_helper.on_new_profile_action),
            (self.action_delete_profile     ,
                self.profile_helper.on_remove_profile_action),
            (self.action_rename_profile     ,
                self.profile_helper.on_rename_profile_action),

            (self.action_preferences        , self.edit_preferences),
            (self.action_quit               , self.close),
            (self.action_install_mod        , self.install_mod_archive),
            (self.action_manual_install     , partial(self.install_mod_archive, True)),
            (self.action_reinstall_mod      , self.reinstall_mod),
            (self.action_uninstall_mod      , self.uninstall_mod),
            (self.action_choose_mod_folder  , self.choose_mod_folder),
            (self.action_toggle_mod         , self.mod_table.toggle_selection_checkstate),
            (self.action_save_changes       , self.on_save_command),
            (self.action_revert_changes     , self.on_revert_command),
            (self.action_move_mod_up        , partial(self.moveMods.emit, -1)),
            (self.action_move_mod_down      , partial(self.moveMods.emit, 1)),
            (self.action_move_mod_to_top    , self.moveModsToTop.emit),
            (self.action_move_mod_to_bottom , self.moveModsToBottom.emit),
            (self.action_find_next          , partial(self.mod_table.on_table_search, 1)),
            (self.action_find_previous      , partial(self.mod_table.on_table_search, -1)),
            (self.action_select_all         , self.on_select_all),
            (self.action_select_none        , self.on_select_none),

        ]

        # tuple(action, shortcut-sequence)
        qks = QtGui.QKeySequence
        shortcuts = [
            (self.action_quit, qks.Quit),
            (self.action_save_changes, qks.Save),
            (self.action_show_search, qks.Find),
            (self.action_find_next, qks.FindNext),
            (self.action_find_previous, qks.FindPrevious),
            (self.action_select_all, qks.SelectAll),
            (self.action_select_none, qks.Deselect),
        ]

        ################################################
        # connect all action triggers
        for action, slot in connections:
            action.triggered.connect(slot)

        # setup shortcuts
        for action, shortcut in shortcuts:
            action.setShortcut(shortcut)

        ################################################

        # # self.action_choose_mod_folder.setIcon(icons.get(
        # # 'folder', color_disabled=QPalette().color(QPalette.Midlight)))

        ## clear missing-from-disk mods
        # add to movement toolbar
        # self.movement_toolbar.addSeparator()
        # self.movement_toolbar.addAction(self.action_clear_missing)

        # should only show when the errors column is visible, but lets
        # make sure its only active when at least one of the
        # mods has a DIR_NOT_FOUND error
        self.mod_table.errorsChanged.connect(
            lambda e: self.action_clear_missing.setEnabled(
                bool(e & constants.ModError.DIR_NOT_FOUND)))


    def _setupui_button_connections(self):
        """ Make the buttons do stuff
        """
        self.LOGGER.debug("_setup_buttons")

        # use a dialog-button-box for save/cancel;
        # have to specify by standard button type
        btn_apply = self.save_cancel_btnbox.button(
            QtWidgets.QDialogButtonBox.Apply)
        btn_reset = self.save_cancel_btnbox.button(
            QtWidgets.QDialogButtonBox.Reset)

        # connect the apply button to the 'save-changes' action
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
            self.mod_table.toggle_search_box)


    # inspector complains about alleged lack of "connect" function
    # noinspection PyUnresolvedReferences
    def _setupui_local_signals_connections(self):
        """
        Connect signals to slots, whether they're local (an attribute
        of the main window) or non-local (part of a sub-component)

        """
        self.LOGGER.debug("_setup_signals_and_slots")

        tbl=self.mod_table
        prof=self.profile_helper

        connections = [

            ## local signals -> local slots ##
            ##-----

            ## local signals -> non-local (on other components) slots ##
            ## -----
            # connect the move up/down signal to the appropriate slot on
            # view; same for the move-to-top/-bottom signals
            (self.moveMods,         tbl.move_selection),
            (self.moveModsToBottom, tbl.move_selection_to_bottom),
            (self.moveModsToTop,    tbl.move_selection_to_top),

            ## non-local signals -> local slots ##
            ## -----

            # listen to profile helper for new profile
            (prof.newProfileLoaded,     self.on_profile_load),
            # enable/disable rename/remove-profile actions as needed
            (prof.enableProfileActions, self.update_profile_actions),

            # ensure the UI is properly updated when the tab changes
            (self.manager_tabs.currentChanged, self.on_tab_changed),

            # depending on selection in table, the movement actions will
            # be enabled or disabled
            (tbl.enableModActions, self.on_make_or_clear_mod_selection),
            (tbl.canMoveItems,     self._enable_mod_move_actions),
        ]

        for signal, slot in connections:
            signal.connect(slot)

    #</editor-fold>

    #<editor-fold desc="data-dependent setup">

    def _setup_profile_selector(self):
        """
        Initialize the dropdown list for selecting profiles with the
        names of the profiles found on disk
        """
        self.LOGGER.debug("_setup_profile_selector")

        self.profile_helper.setup(self.Manager, self.profile_selector)

    def _setup_table_model(self):
        """
        Initialize the model for the mods table
        """
        tbl_model = models.ModTable_TreeModel(parent=self.mod_table,
                                      manager=self.Manager)

        self.mod_table.setModel(tbl_model)

        self.models[M.mod_table] = tbl_model

    def _setup_files_tab_views(self):
        """
        Initialize the models and filters used on the file tree tab
        """
        ## Mods List
        self.filetree_modlist.setup(self.models[M.mod_table],
                                    self.filetree_listlabel,
                                    self.filetree_activeonlytoggle,
                                    self.filetree_modfilter)

        ## File Viewer
        self.filetree_fileviewer.setup(self.filetree_modlist,
                                       self.filetree_filefilter)

    def _setup_undo_manager(self):
        """
        Setup the main QUndoGroup that we will use to manage all the
        undo stacks in the app (all TWO of them so far).

        """
        # create and configure undo action
        self.action_undo = self.undoManager.createUndoAction(self, "Undo")
        self.action_undo.pyqtConfigure(shortcut=QtGui.QKeySequence.Undo,
                                 # icon=icons.get(
                                 #     "undo", scale_factor=0.85,
                                 #     offset=(0, 0.1)),
                                 icon=QtGui.QIcon().fromTheme("edit-undo")
                                 # , triggered=self.on_undo
                                 )

        # it seems it calls undoStack.undo() automatically...no need
        # to connect to something that calls it manually...unless you
        # want every undo/redo action to do that action twice...like
        # it was.

        # create and configure redo action
        self.action_redo = self.undoManager.createRedoAction(self, "Redo")
        self.action_redo.pyqtConfigure(shortcut=QtGui.QKeySequence.Redo,
                                 # icon=icons.get(
                                 #     "redo", scale_factor=0.85,
                                 #     offset=(0, 0.1)),
                                 icon=QtGui.QIcon().fromTheme("edit-redo")
                                 # , triggered=self.on_redo
                                 )

        # insert into the "Edit" menu before the save-changes entry
        self.menu_edit.insertActions(
            self.action_save_changes,
            [self.action_undo, self.action_redo])

        # insert into the toolbar before the preferences entry
        self.file_toolBar.insertActions(
            self.action_preferences,
            [self.action_undo, self.action_redo])
        #now add separator between these and the preferences btn
        self.file_toolBar.insertSeparator(self.action_preferences)

        # add stacks
        self.undoManager.addStack(self.mod_table.undo_stack)
        self.undo_stacks[TAB.MODTABLE] = self.mod_table.undo_stack

        self.undo_stacks[TAB.FILETREE] = self.filetree_fileviewer.undo_stack
        self.undoManager.addStack(self.undo_stacks[TAB.FILETREE])

        # noinspection PyUnresolvedReferences
        self.undoManager.cleanChanged.connect(
            self.on_table_clean_changed)

        # self.undoView = QtWidgets.QUndoView(self.undoManager)
        # self.undoView.show()
        # self.undoView.setAttribute(Qt.WA_QuitOnClose, False)

    # </editor-fold>

    ##=============================================
    ## Event Handlers/Slots
    ##=============================================

    # <editor-fold desc="EventHandlers">

    @pyqtSlot(int)
    def on_tab_changed(self, newindex):
        """
        When the user switches tabs, make sure the proper GUI components
        are visible and active

        :param int newindex:
        """
        self.current_tab = TAB(newindex)

        # ensure proper UI state for current tab
        self.update_UI()

        # self._update_visible_components()
        # self._update_enabled_actions()

        # also change the current undo stack
        # self._update_active_undostack()

    @pyqtSlot('QString')
    def on_profile_load(self, profile_name):
        """
        Call with the name of the selected profile from the profile-
        selector combobox. Update the proper parts of the UI for the
        new information.

        :param str profile_name:
        """
        ## Reset the views
        self.mod_table.reset_view() # this also loads the new data
        self.filetree_modlist.reset_view()
        self.filetree_fileviewer.reset_view()

        # update the UI components for the current tab/profile/data
        self.update_UI()

        # self._update_visible_components()
        # self._update_enabled_actions()

        # also recheck alerts when loading new profile
        # self.update_alerts()

    @pyqtSlot(bool)
    def on_make_or_clear_mod_selection(self, has_selection):
        """
        Enable or disable buttons and actions that rely on having a
        selection in the mod table.
        """
        for a in (self.mod_movement_group,
                  self.action_uninstall_mod,
                  self.action_reinstall_mod,
                  self.action_toggle_mod,
                  self.action_select_none):
            a.setEnabled(has_selection)

    @pyqtSlot(bool)
    def on_table_clean_changed(self, clean):
        """
        When a change is made to the table __that takes it from a
        clean-save-state to a state w/ unsaved changes__, or vice versa,
        enable or disable certain actions depending on it's clean-vs.-
        unsaved status.

        :param bool clean: whether there are unsaved changes
        """

        for widgy in [self.save_cancel_btnbox,
                      self.action_save_changes,
                      self.action_revert_changes]:
            widgy.setEnabled(not clean)

    @pyqtSlot()
    def on_save_command(self):
        """
        Save command does different things depending on which
        tab is active.
        """
        if self.current_tab == TAB.MODTABLE:
            self.mod_table.save_changes()
        elif self.current_tab == TAB.FILETREE:
            self.filetree_fileviewer.save()

    @pyqtSlot()
    def on_revert_command(self):
        """
        Undo all changes made to the table since the last savepoint
        """

        if self.current_tab == TAB.MODTABLE:
            self.mod_table.revert_changes()

        elif self.current_tab == TAB.FILETREE:
            self.filetree_fileviewer.revert()

    @pyqtSlot()
    def on_select_all(self):
        if self.current_tab == TAB.MODTABLE:
            self.mod_table.selectAll()

    @pyqtSlot()
    def on_select_none(self):
        """Deselect"""
        if self.current_tab == TAB.MODTABLE:
            self.mod_table.clearSelection()

    # </editor-fold>

    ##=============================================
    ## Statusbar operations
    ##=============================================

    @pyqtSlot(str)
    def on_status_text_change_request(self, text):
        """Allow other components to request updating the status text"""
        if text:
            self.status_bar.showMessage(text)
        else:
            self.status_bar.clearMessage()

    def show_statusbar_progress(self, text="Working:",
                                minimum=0, maximum=0,
                                show_bar_text=False):
        """
        Set up and display the small progress bar on the bottom right
        of the window (in the status bar). If `minimum` == `maximum`
        == 0, the bar will be in indeterminate ('busy') mode: this is
        useful for indicating to the user that *something* is going on
        in the background during activities that may take a moment or
        two to complete, so the user need not worry that their last
        command had no effect.

        :param text: Text that will be shown to the left of the
            progress bar
        :param minimum: Minumum value for the bar
        :param maximum: Maximum value for the bar
        :param show_bar_text: Whether to show the bar's text
            (% done by default)
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

    ##===============================================
    ## UI Helper Functions
    ##===============================================

    def update_alerts(self):
        """
        Just populates the alerts-dropdown with the contents of the
        main Manager's alerts collection. Does not request any checks.
        """

        # self.LOGGER << "update_alerts"

        # clear the list
        self.alerts_button.clear_widget()

        if self.Manager.has_alerts:

            self.alerts_button.update_widget(self.Manager.alerts)

            self.LOGGER << "Show alerts indicator"
            self.action_show_alerts.setVisible(True)

            # readjust drop-down menu size to fit items
            self.alerts_button.adjust_display_size()

        else:
            self.LOGGER << "Hide alerts indicator"
            # have to hide using action, not button
            # (See docs for qtoolbar.addWidget...)
            self.action_show_alerts.setVisible(False)

    # def update_UI(self, *args):
    def update_UI(self):
        """Ensure the UI has the appropriate parts active/visible for
        the current tab and data state."""
        self._update_visible_components()
        self._update_enabled_actions()

        # also change the current undo stack
        self._update_active_undostack()


    def _update_visible_components(self):
        """
        Some manager components should be hidden on certain tabs
        """
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
        # use pre-constructed mapping of actions we want to consider
        all_components = self._action_components

        # this is a selector that, depending on how it is
        # modified below, will allow us to set every
        # component to its appropriate enabled state
        s = {c:False for c in all_components}

        if self.current_tab == TAB.MODTABLE:
            s["asa"] = self.mod_table.item_count > 0
            s["mmg"] = s["atm"] = s["aum"] = s["asn"] = self.mod_table.has_selection
            s["asc"] = s["arc"] = not self.undoManager.isClean()
            s["afn"] = s["afp"] = bool(self.mod_table.search_text)
            s["acm"] = bool(self.mod_table.errors_present & constants.ModError.DIR_NOT_FOUND)
        elif self.current_tab == TAB.FILETREE:
            s["asc"] = s["arc"] = self.filetree_fileviewer.has_unsaved_changes


        for comp, select in s.items():
            all_components[comp].setEnabled(select)

    def _update_active_undostack(self):
        """Set the active undo stack to the stack associated with
        the current tab"""
        self.undoManager.setActiveStack(
            self.undo_stacks[self.current_tab])

    def _enable_mod_move_actions(self, enable_moveup, enable_movedown):
        """
        Enable or disable the mod-movement actions

        :param bool enable_moveup: whether to enable the
            move-up/move-to-top actions
        :param bool enable_movedown: whether to enable the
            move-down/move-to-bottom actions
        """
        for action in [self.action_move_mod_to_bottom,
                       self.action_move_mod_down]:
            action.setEnabled(enable_movedown)

        for action in [self.action_move_mod_to_top,
                       self.action_move_mod_up]:
            action.setEnabled(enable_moveup)


    # todo: change window title (or something) to reflect current folder
    # def on_filetree_fileviewer_rootpathchanged(self, newpath):
    #     self.filetree_fileviewer.resizeColumnToContents(0)

    def table_prompt_if_unsaved(self):
        """
        Check for unsaved changes to the mods list and show a prompt if
        any are found. Clicking yes will save the changes and mark the
        table clean, while clicking no will simply disable the apply/
        revert buttons as IF the table were clean. This is because
        this is intended to be used right before an action like loading
        a new profile (thus forcing a full table reset) or quitting the
        app.

        :return: the value of the button the user clicked
            (QMessageBox.[Yes/No/Cancel]), or None if the message box
            was not shown
        """
        # check for unsaved changes to the mod-list
        if self.Manager.profile is not None \
                and not self.mod_table.undo_stack.isClean():
            ok = QMessageBox(QMessageBox.Warning, 'Unsaved Changes',
                             'Your mod install-order has unsaved '
                             'changes. Would you like to save them '
                             'before continuing?',
                             QMessageBox.No | QMessageBox.Yes |
                             QMessageBox.Cancel).exec_()

            if ok == QMessageBox.Yes:
                self.mod_table.save_changes()
            return ok
        # if clean, return None to indicate that the calling operation
        # may contine as normal
        return None

    @pyqtSlot(bool, str, bool)
    def update_profile_actions(self, enable_remove, remove_tooltip, enable_rename):
        """

        :param bool enable_remove: whether to enable the 'delete profile' button
        :param str remove_tooltip: tooltip for the delete profile button
        :param bool enable_rename: whether to enable the 'rename profile' button
        """

        self.action_delete_profile.setEnabled(enable_remove)
        self.action_delete_profile.setToolTip(remove_tooltip)
        self.action_rename_profile.setEnabled(enable_rename)

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
        Show a dialog allowing the user to change some application-wide
        preferences
        """
        from skymodman.interface.dialogs.preferences_dialog \
            import PreferencesDialog

        pdialog = PreferencesDialog(self.profile_helper.model,
                                    self.profile_helper.current_index)

        # connect some of the dialog's signals to the data managers

        pdialog.beginModifyPaths.connect(self.Manager.begin_queue_signals)
        pdialog.endModifyPaths.connect(self.Manager.end_queue_signals)

        pdialog.exec_()

        del PreferencesDialog

        # now have the Manager check to see if all the directories
        # are valid, and update the alerts indicator if needed
        ## XXX: this should happen automatically now...hopefully
        # self.Manager.check_dirs()
        # self.update_alerts()

    @pyqtSlot()
    def choose_mod_folder(self):
        """
        Show dialog allowing user to choose a mod folder.

        This updates the default mod folder. If a profile override is
        active, it will be disabled. Use the preferences dialog
        to set up and enable a profile-specific override.

        """

        # noinspection PyTypeChecker, PyArgumentList
        moddir = QtWidgets.QFileDialog.getExistingDirectory(
            self,
            "Choose Directory Containing Installed Mods",
            self.Manager.Folders['mods'].spath
        )

        # update config with new path
        if check_path(moddir):
            mfolder = self.Manager.Folders[KeyStr_Dirs.MODS]

            mfolder.set_path(moddir)

            if mfolder.is_overriden:
                mfolder.remove_override()
                self.Manager.profile.disable_override(KeyStr_Dirs.MODS)

            # reverify and reload the mods.
            if not self.Manager.validate_mod_installs():
                self.mod_table.model().reload_errors_only()

    # noinspection PyTypeChecker,PyArgumentList
    def install_mod_archive(self, manual=False):
        """
        Install a mod from an archive.

        :param bool manual: If false, attempt to use
        the guided FOMOD installer if a fomod config is found, otherwise
        simply unpack the archive. If true, show the file-system view of
        the archive and allow the user to choose which parts to install.

        """
        # fixme: default to home folder or something instead of current dir
        # filename=QFileDialog.getOpenFileName(
        #     self, "Select Mod Archive",
        #     QDir.currentPath() + "/res",
        #     "Archives [zip, 7z, rar] (*.zip *.7z *.rar);;All Files(*)")[0]

        # short-circuit for testing
        filename='res/7ztest.7z'
        if filename:
            installui = InstallerUI(self.Manager) # helper class
            if manual:
                self.show_statusbar_progress("Loading archive:")

                # self.task = asyncio.get_event_loop().create_task(
                #     installui.do_manual_install(
                #         filename, self.hide_statusbar_progress))

            else:
                # show busy indicator while installer loads
                self.show_statusbar_progress("Preparing installer:")

            self.task = asyncio.get_event_loop().create_task(
                installui.do_install(filename,
                                     self.hide_statusbar_progress,
                                     manual))

                # todo: add callback to show the new mod if install succeeded
                # self.task.add_done_callback(self.on_new_mod())

    def reinstall_mod(self):
        """
        Repeat the installation process for the given mod
        """
        # todo: implement re-running the installer
        row = self.mod_table.currentIndex().row()
        if row > -1:
            # mod = self.models[M.mod_table][row]
            self.LOGGER << "Here's where we'd reinstall this mod."

    def uninstall_mod(self):
        """
        Remove the selected mod from the virtual installation directory
        """
        # todo: implement removing the mod
        row = self.mod_table.currentIndex().row()
        if row > -1:
            # mod = self.models[M.mod_table][row]
            self.LOGGER << "Here's where we'd uninstall this mod."

    @pyqtSlot()
    def remove_missing(self):
        """
        Remove all mod entries that were not found on disk from the
        current profile's mod list
        """
        ## FIXME: make sure the mod-count on the file tree mods-list is updated correctly to show the correct new value for the number of known mods
        self.LOGGER << "Clear missing mods"

        self.mod_table.clear_missing_mods()

    #</editor-fold>

    ##=============================================
    ## Qt Overrides
    ##=============================================

    def closeEvent(self, event):
        """
        Override close event to check for unsaved changes and to save
        settings to disk

        :param event:
        """

        # only ignore the close event if the user clicks cancel
        # on the confirm window
        if self.table_prompt_if_unsaved() == QMessageBox.Cancel:
            event.ignore()
        else:
            # self.write_settings()
            # TODO: save profile-specific settings here as well (such
            # as the active-only checkbox) instead of on each change.
            app_settings.write()
            event.accept()

