from functools import partial
import asyncio

from PyQt5 import QtWidgets, QtGui, QtCore
# specifically import some frequently used names
from PyQt5.QtCore import Qt, pyqtSignal, pyqtSlot
from PyQt5.QtWidgets import QMessageBox, QTreeWidgetItem, QLabel

from skymodman import exceptions, constants, Manager
from skymodman.constants import qModels as M, qFilters as F, Tab as TAB
from skymodman.constants.keystrings import (Section as KeyStr_Section,
                                            Dirs as KeyStr_Dirs,
                                            INI as KeyStr_INI,
                                            UI as KeyStr_UI)
# from skymodman.managers import modmanager
from skymodman.interface import models, app_settings #, ui_utils
from skymodman.interface.dialogs import message
from skymodman.interface.install_helpers import InstallerUI
from skymodman.log import withlogger #, icons
from skymodman.utils.fsutils import check_path, join_path

from skymodman.interface.designer.uic.manager_window_ui import Ui_MainWindow

# M = constants.qModels
# F = constants.qFilters
# TAB = constants.Tab

# Manager = None # type: modmanager.ModManager

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
    modListModified     = pyqtSignal()
    modListSaved        = pyqtSignal()

    newProfileLoaded    = pyqtSignal(str)

    moveMods            = pyqtSignal(int)
    moveModsToTop       = pyqtSignal()
    moveModsToBottom    = pyqtSignal()

    instance = None # type: ModManagerWindow

    def __init__(self, **kwargs):
        """
        :param kwargs: anything to pass on the the base class constructors
        """
        super().__init__(**kwargs)

        # global Manager
        # Manager = modmanager.Manager()
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

        self.profile_name = None # type: str
        # track currently selected profile by index as well
        self.profile_selector_index = -1

        # make sure the correct initial pages are showing
        self.manager_tabs.setCurrentIndex(self._currtab.value)

        self._search_text=''

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

        PLP = constants.ProfileLoadPolicy
        # load profile as indicated by settings
        pload_policy = app_settings.Get(KeyStr_UI.PROFILE_LOAD_POLICY)

        if pload_policy:
            # convert to enum type from int
            pload_policy = PLP(pload_policy)
            to_load = {
                PLP.last: KeyStr_INI.LAST_PROFILE,
                PLP.default: KeyStr_INI.DEFAULT_PROFILE
            }[pload_policy]
            # get the name of the default/last profile and load its data
            self.load_profile_by_name(
                self.Manager.get_config_value(to_load))


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
        self._setupui_slot_connections()

    def _setup_data_interface(self):
        """
        Called after the mod manager has been assigned; invokes
        setup methods that require the data backend.
        """

        self._setup_profile_selector()
        self._setup_table_model()
        self._setup_file_tree_models()

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

        self.alerts_button = QtWidgets.QToolButton(self.file_toolBar)
        self.alerts_button.setObjectName("alerts_button")

        # noinspection PyTypeChecker,PyArgumentList
        self.alerts_button.setIcon(QtGui.QIcon.fromTheme("dialog-warning"))
        self.alerts_button.setText("Alerts")
        self.alerts_button.setToolButtonStyle(Qt.ToolButtonFollowStyle)
        self.alerts_button.setToolTip("View Alerts")
        self.alerts_button.setStatusTip(
            "There are issues which require your attention!")
        self.alerts_button.setPopupMode(QtWidgets.QToolButton.InstantPopup)

        self.alerts_button.setMenu(QtWidgets.QMenu(self.alerts_button))

        # use a tree widget to make collapsible items
        self.alerts_view_widget = QtWidgets.QTreeWidget(self.alerts_button)
        # AbstractItemView.SelectionMode.NoSelection == 0
        self.alerts_view_widget.setSelectionMode(0)
        self.alerts_view_widget.setMinimumWidth(400)
        self.alerts_view_widget.setColumnCount(2)
        self.alerts_view_widget.setObjectName("alerts_view_widget")
        self.alerts_view_widget.setHeaderHidden(True)

        # hide the sub-itembranches that don't line up correctly with the
        # top-aligned labels (note:: setting background: transparent
        # on every ::branch makes the expansion arrow disappear
        # for some reason. There may be a better way around that, but
        # this is acceptable for now)
        self.alerts_view_widget.setStyleSheet(
            """
            QTreeWidget::branch:!has-children {
                background: transparent;
            }
            """
            )
        self.alerts_view_widget.setSizeAdjustPolicy(
            self.alerts_view_widget.AdjustToContents)

        # create the action that contains the popup
        action_show_alerts = QtWidgets.QWidgetAction(self.alerts_button)

        # set popup view as default widget
        action_show_alerts.setDefaultWidget(self.alerts_view_widget)

        # add the action to the menu of the alerts button;
        # this causes the "menu" to consist wholly of the display widget
        self.alerts_button.menu().addAction(action_show_alerts)

        ## OK...so, since QWidget.setVisible() does not work for items
        ## added to a toolbar with addWidget(?!), we need to save the
        ## action returned by the addWidget() method (who knew?!) and
        ## use its setVisible() &c. methods.
        ## is this returned action the same as "action_show_alerts"
        ## above? I have no idea!!
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


        # self.profile_group.addActions([self.action_new_profile,
        #                               self.action_delete_profile])

        # Action Group for the mod-movement buttons.
        # this just makes it easier to enable/disable them all at once
        # self.file_toolBar.addSeparator()
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

        # setup the animation to show/hide the search bar
        self.animate_show_search = QtCore.QPropertyAnimation(
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
        self.action_quit.setShortcut(QtGui.QKeySequence.Quit)
        # connect quit action to close event
        self.action_quit.triggered.connect(self.close)

        # --------------------------------------------------

        # action_install_mod
        self.action_install_mod.triggered.connect(
            self.install_mod_archive)

        self.action_manual_install.triggered.connect(
            partial(self.install_mod_archive, True))

        # action_reinstall_mod
        self.action_reinstall_mod.triggered.connect(
            self.reinstall_mod)

        # action_uninstall_mod
        self.action_uninstall_mod.triggered.connect(
            self.uninstall_mod)

        # action_choose_mod_folder
        self.action_choose_mod_folder.triggered.connect(
            self.choose_mod_folder)
        # self.action_choose_mod_folder.setIcon(icons.get(
        # 'folder', color_disabled=QPalette().color(QPalette.Midlight)))

        # --------------------------------------------------

        # action edit ... ini

        # --------------------------------------------------

        # action_toggle_mod
        self.action_toggle_mod.triggered.connect(
            self.mod_table.toggle_selection_checkstate)


        # --------------------------------------------------

        # action_save_changes
        self.action_save_changes.setShortcut(
            QtGui.QKeySequence.Save)
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
        self.action_show_search.setShortcut(QtGui.QKeySequence.Find)

        # find next
        self.action_find_next.setShortcut(QtGui.QKeySequence.FindNext)
        self.action_find_next.triggered.connect(
            partial(self.on_table_search, 1))
        # find prev
        self.action_find_previous.setShortcut(QtGui.QKeySequence.FindPrevious)
        self.action_find_previous.triggered.connect(
            partial(self.on_table_search, -1))


       # --------------------------

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


    # inspector complains about alleged lack of "connect" function
    # noinspection PyUnresolvedReferences
    def _setupui_local_signals_connections(self):
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
            self.mod_table.move_selection)
        # same for the move to top/button signals
        self.moveModsToBottom.connect(
            self.mod_table.move_selection_to_bottom)
        self.moveModsToTop.connect(
            self.mod_table.move_selection_to_top)


    def _setupui_slot_connections(self):
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

        ##===================================
        ## Mod Table Tab
        ##-----------------------------------

        # depending on selection in table, the movement actions will be
        # enabled or disabled
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

        # left the selectionModel() changed connection in the _setup
        # function; it's just easier to handle it there

        # self.models[M.file_viewer].hasUnsavedChanges.connect(
        #     self.on_table_unsaved_change)

    #</editor-fold>

    #<editor-fold desc="data-dependent setup">

    def _setup_profile_selector(self):
        """
        Initialize the dropdown list for selecting profiles with the
        names of the profiles found on disk
        """
        self.LOGGER.debug("_setup_profile_selector")

        model = models.ProfileListModel()

        # Only store names in profile selector
        for profile in self.Manager.get_profiles():
            model.insertRows(data=profile)

        self.profile_selector.setModel(model)

        # start with no selection
        self.profile_selector.setCurrentIndex(-1)
        # call this to make sure the delete button is inactive
        self.check_enable_profile_delete()

        # can't activate this signal until after the selector is populated
        self.profile_selector.currentIndexChanged.connect(
            self.on_profile_select)

    def _setup_table_model(self):
        """
        Initialize the model for the mods table
        """
        tbl_model = models.ModTable_TreeModel(parent=self.mod_table,
                                      manager=self.Manager)

        self.mod_table.setModel(tbl_model)

        self.models[M.mod_table] = tbl_model

    def _setup_file_tree_models(self):
        """
        Initialize the models and filters used on the file tree tab
        """

        ##################################
        ## Mods List
        ##################################

        # setup filter proxy for active mods list
        mod_filter = self.filters[
            F.mod_list] = models.ActiveModsListFilter(
            self.filetree_modlist)

        # use the main mod-table model as the source
        mod_filter.setSourceModel(self.models[M.mod_table])
        # ignore case when filtering
        mod_filter.setFilterCaseSensitivity(Qt.CaseInsensitive)

        # tell filter to read mod name column
        mod_filter.setFilterKeyColumn(constants.Column.NAME.value)

        # load and apply saved setting for 'activeonly' toggle
        self._update_modlist_filter_state()

        # finally, set the filter as the model for the modlist
        self.filetree_modlist.setModel(mod_filter)
        # make sure we're just showing the mod name
        self.filetree_modlist.setModelColumn(
            constants.Column.NAME.value)

        ##################################
        ## File Viewer
        ##################################
        ## model for tree view of files
        fileviewer_model = self.models[
            M.file_viewer] = models.ModFileTreeModel(
            parent=self.filetree_fileviewer,
            manager=self.Manager)

        ## filter
        fileviewer_filter = self.filters[
            F.file_viewer] = models.FileViewerTreeFilter(
            self.filetree_fileviewer)

        fileviewer_filter.setSourceModel(fileviewer_model)
        fileviewer_filter.setFilterCaseSensitivity(Qt.CaseInsensitive)

        ## set model
        self.filetree_fileviewer.setModel(fileviewer_filter)

        ## show new files when mod selection in list
        self.filetree_modlist.selectionModel().currentChanged.connect(
            lambda curr, prev: self.viewer_show_file_tree(
                mod_filter.mapToSource(curr),
                mod_filter.mapToSource(prev)))

        ## have escape key unfocus the filter boxes
        for f in [self.filetree_modfilter, self.filetree_filefilter]:
            f.escapeLineEdit.connect(f.clearFocus)

    def _update_modlist_filter_state(self):

        filter_=self.filters[F.mod_list]

        activeonly = self.Manager.get_profile_setting(
            KeyStr_INI.ACTIVE_ONLY,
            KeyStr_Section.FILEVIEWER)

        if activeonly is None:
            # if no profile loaded, set it unchecked and disable it
            activeonly=False
            self.filetree_activeonlytoggle.setEnabled(False)
        else:
            self.filetree_activeonlytoggle.setEnabled(True)

        filter_.onlyShowActive = activeonly

        # apply setting to box
        self.filetree_activeonlytoggle.setCheckState(
            Qt.Checked if activeonly else Qt.Unchecked)

        # and setup label text for first display
        self.update_modlist_label(activeonly)



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
                                 , triggered=self.on_undo
                                 )

        # create and configure redo action
        self.action_redo = self.undoManager.createRedoAction(self, "Redo")
        self.action_redo.pyqtConfigure(shortcut=QtGui.QKeySequence.Redo,
                                 # icon=icons.get(
                                 #     "redo", scale_factor=0.85,
                                 #     offset=(0, 0.1)),
                                 icon=QtGui.QIcon().fromTheme("edit-redo")
                                 , triggered=self.on_redo
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

        self.undo_stacks[TAB.FILETREE] = self.models[M.file_viewer].undostack
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
        self._update_visible_components()
        self._update_enabled_actions()

        # also change the current undo stack
        self.undoManager.setActiveStack(
            self.undo_stacks[self.current_tab])

    @pyqtSlot(int)
    def on_profile_select(self, index):
        """
        When a new profile is chosen from the dropdown list, load all
        the appropriate data for that profile and replace the current
        data with it. Also show a message about unsaved changes to the
        current profile.

        :param int index:
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
            # use userRole to get the 'on-disk' name of the profile
            new_profile = self.profile_selector.currentData(
                Qt.UserRole)

            # if no active profile, just load the selected one.
            # if somehow selected the same profile, do nothing

            if self.Manager.profile and self.Manager.profile.name == new_profile:
                return

            # check for unsaved changes to the mod-list
            reply = self.table_prompt_if_unsaved()

            # only continue to change profile if user does NOT
            # click cancel (or if there are no changes to save)
            if reply == QtWidgets.QMessageBox.Cancel:
                # reset the text in the profile selector;
                # this SHOULDn't enter an infinite loop because,
                # since we haven't yet changed
                # self.profile_selector_index, now 'index' will be
                # the same as 'old_index' at the top of this
                # function and nothing else in the program will
                # change (just the name shown in the profile
                # selector)
                self.profile_selector.setCurrentIndex(old_index)
            else:
                self.LOGGER.info(
                    "Activating profile '{}'".format(
                        new_profile))

                if self.Manager.activate_profile(new_profile):

                    self.logger << "Resetting views for new profile"

                    # update our variable which tracks the current index
                    self.profile_selector_index = index

                    # No => "Don't save changes, drop them"
                    # if reply == QtWidgets.QMessageBox.No:

                    # Whether they clicked "no" or not, we
                    # don't bother reverting, mods list is getting
                    # reset; just disable the buttons
                    self.mod_table.undo_stack.clear()
                    # for s in self.undo_stacks:
                    #     s.clear()

                    self.newProfileLoaded.emit(new_profile)
                else:
                    self.LOGGER.error("Profile Activation failed.")
                    self.profile_selector.setCurrentIndex(old_index)

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

        # also recheck alerts when loading new profile
        # self.update_alerts()

    @pyqtSlot()
    def on_new_profile_action(self):
        """
        When the 'add profile' button is clicked, create and show a
        small dialog for the user to choose a name for the new profile.
        """

        from skymodman.interface.dialogs.new_profile_dialog \
            import NewProfileDialog

        popup = NewProfileDialog(
            combobox_model=self.profile_selector.model())

        # display popup, wait for close and check signal
        if popup.exec_() == popup.Accepted:
            # add new profile if they clicked ok
            new_profile = self.Manager.new_profile(popup.final_name,
                                              popup.copy_from)

            self.profile_selector.model().addProfile(new_profile)

            # set new profile as active and load data
            self.load_profile_by_name(new_profile.name)

        del NewProfileDialog

    @pyqtSlot()
    def on_remove_profile_action(self):
        """
        Show a warning about irreversibly deleting the profile, then, if
        the user accept the warning, proceed to delete the profile from
        disk and remove its entry from the profile selector.
        """
        profile = self.Manager.profile

        if message('warning', 'Confirm Delete Profile',
                   'Delete "' + profile.name + '"?',
                   'Choosing "Yes" below will remove this profile '
                   'and all saved information within it, including '
                   'customized load-orders, ini-edits, etc. Note '
                   'that installed mods will not be affected. This '
                   'cannot be undone. Do you wish to continue?'):
            self.Manager.delete_profile(
                self.profile_selector.currentData())
            self.profile_selector.removeItem(
                self.profile_selector.currentIndex())

    @pyqtSlot()
    def on_rename_profile_action(self):
        """
        Query the user for a new name, then ask the mod-manager backend
        to rename the profile folder.
        """

        # noinspection PyTypeChecker,PyArgumentList
        newname = QtWidgets.QInputDialog.getText(self,
                                       "Rename Profile",
                                       "New name")[0]

        if newname:
            try:
                self.Manager.rename_profile(newname)
            except exceptions.ProfileError as pe:
                message('critical', "Error During Rename Operation",
                        text=str(pe), buttons='ok')

    @pyqtSlot(bool)
    def on_make_or_clear_mod_selection(self, has_selection):
        """
        Enable or disable buttons and actions that rely on having a
        selection in the mod table.
        """
        for a in (self.mod_movement_group,
                  self.action_uninstall_mod,
                  self.action_reinstall_mod,
                  self.action_toggle_mod):
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

    @pyqtSlot(bool)
    def on_modlist_activeonly_toggle(self, checked):
        """
        Toggle showing/hiding inactive mods in the Mods list on the
        file-tree tab

        :param checked: state of the checkbox
        """
        # self.LOGGER << "ActiveOnly toggled->{}".format(checked)

        self.filters[F.mod_list].setOnlyShowActive(checked)
        self.update_modlist_label(checked)
        self.Manager.set_profile_setting(KeyStr_INI.ACTIVE_ONLY,
                                    KeyStr_Section.FILEVIEWER,
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
        string given by `text`. The resulting matches are fed to the
        proxy filter on the file viewer which uses them to make sure
        that matching files are shown in the tree regardless of whether
        their parent directories match the filter or not.

        :param str text:
        """
        # don't bother querying db for empty string,
        # the filter will ignore the matched files anyway
        if not text:
            self.filters[F.file_viewer].setFilterWildcard(text)
        else:
            # db = self.Manager.DB.conn
            db = self.Manager.getdbcursor()

            sqlexpr = r'%' + text.replace('?', '_').replace('*',
                                                            r'%') + r'%'

            matches = [r[0] for r in db.execute(
                "SELECT filepath FROM modfiles WHERE directory=? AND filepath LIKE ?",
                (self.models[M.file_viewer].modname, sqlexpr))]

            self.filters[F.file_viewer].setMatchingFiles(matches)

            self.filters[F.file_viewer].setFilterWildcard(text)
            self.filetree_fileviewer.expandAll()

    @pyqtSlot()
    def on_save_command(self):
        """
        Save command does different things depending on which
        tab is active.
        """
        if self.current_tab == TAB.MODTABLE:
            self.mod_table.save_changes()
        elif self.current_tab == TAB.FILETREE:
            self.models[M.file_viewer].save()

    @pyqtSlot()
    def on_revert_command(self):
        """
        Undo all changes made to the table since the last savepoint
        """

        if self.current_tab == TAB.MODTABLE:
            self.mod_table.revert_changes()

        elif self.current_tab == TAB.FILETREE:
            self.models[M.file_viewer].revert()

    @pyqtSlot()
    def on_undo(self):
        """calls undo() on the current undoStack"""
        self.undoManager.undo()

    @pyqtSlot()
    def on_redo(self):
        self.undoManager.redo()

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
        self._clear_searchbox_style()

    @pyqtSlot()
    def _clear_searchbox_style(self):
        if self.modtable_search_box.styleSheet():
            self.modtable_search_box.setStyleSheet('')
            self.status_bar.clearMessage()

    # </editor-fold>

    ##=============================================
    ## Statusbar operations
    ##=============================================

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

    ##=============================================
    ## Reset UI components
    ##=============================================

    def _reset_table(self):
        """
        Called when a new profile is loaded or some other major
        change occurs
        """
        self.mod_table.load_data()
        self.modtable_search_box.clear() # might be good enough


    def _reset_file_tree(self):
        # clear the filter boxes
        self.filetree_modfilter.clear()
        self.filetree_filefilter.clear()

        # clear the file tree view
        # self.models[M.file_viewer].setRootPath(None)
        self.models[M.file_viewer].setMod(None)

        # if the main mods directory is unset, just disable the list
        # until the user corrects this
        if not self.Manager.Folders['mods']:
            self.filetree_modlist.setEnabled(False)
            self.filetree_modlist.setToolTip(
                "Mods directory is currently invalid")
        else:
            self.filetree_modlist.setEnabled(True)
            self.filetree_modlist.setToolTip(None)

        # update the label and checkbox on the modlist
        self._update_modlist_filter_state()

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
        self.alerts_view_widget.clear()

        if self.Manager.has_alerts:

            # get a bold font to use for labels
            bfont = QtGui.QFont()
            bfont.setBold(True)
            for a in sorted(self.Manager.alerts, key=lambda al: al.label):
                # the label/title as top-level item
                alert_title = QTreeWidgetItem(self.alerts_view_widget,
                                              [a.label])
                alert_title.setFirstColumnSpanned(True)

                # underneath the label, one can expand the item
                # to view the description and suggested fix
                desc = QTreeWidgetItem(alert_title, ["Desc:"])
                desc.setFont(0, bfont)
                desc.setTextAlignment(0, Qt.AlignTop)

                # some QLabel shenanigans to work around the lack of
                # word wrap in QTreeWidget
                # FIXME: the label still only seems to 2 lines of text at most; a long-ish description can have its last few words cut off, depending on font size and width of the menu widget.
                # ...update: setting the text interaction flags to
                #    TextSelectableByMouse makes all the text visible...
                #    and adds a bunch of empty space at the bottom of the
                #    label. Just can't win.
                lbl_desc = QLabel(a.desc)
                lbl_desc.setWordWrap(True)
                lbl_desc.setAlignment(Qt.AlignTop)
                lbl_desc.setTextInteractionFlags(Qt.TextSelectableByMouse)
                self.alerts_view_widget.setItemWidget(desc, 1, lbl_desc)

                # ditto
                fix = QTreeWidgetItem(alert_title, ["Fix:"])
                fix.setTextAlignment(0, Qt.AlignTop)
                fix.setFont(0, bfont)

                lbl_fix = QLabel(a.fix)
                lbl_fix.setWordWrap(True)
                lbl_fix.setAlignment(Qt.AlignTop)
                lbl_fix.setTextInteractionFlags(Qt.TextSelectableByMouse)


                self.alerts_view_widget.setItemWidget(fix, 1, lbl_fix)
                alert_title.setExpanded(True)

            self.LOGGER << "Show alerts indicator"
            self.action_show_alerts.setVisible(True)

            # adjust size of display treewidget and containing menu;
            # have to set both Min and Max on the menu to get it to
            # resize correctly
            self.alerts_view_widget.adjustSize()
            h = self.alerts_view_widget.size().height()
            m = self.alerts_button.menu()
            m.setMinimumHeight(h)
            m.setMaximumHeight(h)
        else:
            self.LOGGER << "Hide alerts indicator"
            # have to hide using action, not button
            # (See docs for qtoolbar.addWidget...)
            self.action_show_alerts.setVisible(False)

    # def update_UI(self, *args):
    def update_UI(self):
        self._update_visible_components()
        self.undoManager.setActiveStack(self.undo_stacks[self.current_tab])

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
        # tab=self.current_tab

        # use pre-constructed mapping of actions we want to consider
        all_components = self._action_components

        # this is a selector that, depending on how it is
        # modified below, will allow us to set every
        # component to its appropriate enabled state
        s = {c:False for c in all_components.keys()}

        if self.current_tab == TAB.MODTABLE:
            s["mmg"] = s["atm"] = s["aum"] = self.mod_table.selectionModel().hasSelection()
            s["asc"] = s["arc"] = not self.undoManager.isClean()
            s["afn"] = s["afp"] = bool(self._search_text)
            s["acm"] = bool(self.mod_table.errors_present & constants.ModError.DIR_NOT_FOUND)
        elif self.current_tab == TAB.FILETREE:
            s["asc"] = s["arc"] = self.models[M.file_viewer].has_unsaved_changes


        for comp, select in s.items():
            all_components[comp].setEnabled(select)

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
        Change the label beside the "hide inactive mods" check box to
        reflect its current state.

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

        mod = indexCur.internalPointer()
        self.models[M.file_viewer].setMod(mod)

        # moddir = indexCur.internalPointer().directory

        # add the name of the mod directory to the path of the
        # main mods folder

        # modstorage = self.Manager.Folders['mods']
        # if modstorage:
        #     p = join_path(modstorage.spath, moddir)

            # self.models[M.file_viewer].setRootPath(p)
        # if the main mods-storage directory is unset, don't attempt
        # to show anything

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
        Programatically update the profile selector to select the
        profile given by `name`, triggering the ``on_profile_select``
        slot.

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
        Show a dialog allowing the user to change some application-wide
        preferences
        """
        from skymodman.interface.dialogs.preferences_dialog \
            import PreferencesDialog

        pdialog = PreferencesDialog(self.profile_selector.model(),
                                    self.profile_selector.currentIndex())

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
        # If a profile is currently loaded, this will set a directory
        # override for the mods folder that applies to this profile only.
        # The default directory can be set in the preferences dialog.
        # When no profile is loaded, this will instead set the default
        # directory.


        # noinspection PyTypeChecker
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
        ## FIXME: make this undoable. Also, make sure the mod-count on the file tree mods-list is updated correctly to show the correct new value for the number of known mods
        self.LOGGER << "Clear missing mods"

        self.models[M.mod_table].clear_missing()

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

