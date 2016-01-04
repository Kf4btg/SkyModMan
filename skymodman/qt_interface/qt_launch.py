import sys

from PyQt5.QtCore import Qt, QStandardPaths, QDir, pyqtSignal, pyqtSlot, QAbstractItemModel
from PyQt5.QtGui import QGuiApplication
from PyQt5.QtWidgets import QApplication, QMainWindow, QTableWidgetItem, \
    QFileDialog, QFileSystemModel, QDialogButtonBox

import skymodman.constants as const
from skymodman.qt_interface.qt_manager_ui import Ui_MainWindow
# from skymodman.qt_interface.widgets.new_profile_dialog_ui import Ui_NewProfileDialog
from skymodman.qt_interface.widgets import custom_widgets
from skymodman.qt_interface.models import ProfileListModel
from skymodman.utils import withlogger, Notifier
# from collections import OrderedDict
from skymodman import skylog

@withlogger
class ModManagerWindow(QMainWindow, Ui_MainWindow):

    modListModified = pyqtSignal()
    modListSaved = pyqtSignal()
    changesCanceled = pyqtSignal()

    windowInitialized = pyqtSignal()
    

    def __init__(self, manager: 'managers.ModManager', *args, **kwargs):
        super(ModManagerWindow, self).__init__(*args, **kwargs)
        self.LOGGER.info("Initializing ModManager Window")

        # reference to the Mod Manager
        self._manager = manager

        self.setupSlots = [self.setupTable,
                      self.setupFileTree,
                      self.setupProfileSelector]

        # connect the windowinit signal to the setup slots
        for s in self.setupSlots:
            self.windowInitialized.connect(s)

        ## Notifier object for the above 'setup...' slots to
        ## call when they've completed their setup process.
        ## After the final call, the UI will updated and
        ## presented to the user
        self.SetupDone = Notifier(len(self.setupSlots), self.updateUI)

        # setup the base ui
        self.setupUi(self)

        # connect the buttons

        # use a dialog-button-box
        # no helper signal (like accepted()) for these,
        # so have to specify it by standard button type
        self.save_cancel_btnbox.button(QDialogButtonBox.Apply).clicked.connect(self.saveModsList)
        self.save_cancel_btnbox.button(QDialogButtonBox.Reset).clicked.connect(self.resetTable)

        # connect up profile box
        # self.setupProfileSelector()

        # connect the actions
        self.action_Quit.triggered.connect(quit_app)
        self.action_Install_Fomod.triggered.connect(self.loadFomod)

        # keep track of changes made to mod list
        # self.mod_list_modified = False
        self.file_tree_modified = False
        # tracking modified rows; using list or ordered dict might allow for an "undo" function later
        self._modified_cells = []  # list of point-tuples (row, column) for fields in table

        # set placeholder fields
        self.loaded_fomod = None
        
        # make some UI adjustments
        self.manager_tabs.setCurrentIndex(0)
        self.installerpages.setCurrentIndex(0)

        # these should be disabled until a change is made,
        # self.modListModified.connect(self.enableSaveCancelButtons)
        # self.modListSaved.connect(self.disableSaveCancelButtons)



        # connect other signals
        self.manager_tabs.currentChanged.connect(self.updateUI)
        # self.mod_table.cellChanged.connect(self.onTableModified)



        # update UI
        # self.updateUI()


        self.windowInitialized.emit()


    @property
    def Manager(self):
        return self._manager

    def updateUI(self, *args):
        if self.loaded_fomod is None:
            self.fomod_tab.setEnabled(False)

        curtab = self.manager_tabs.currentIndex()

        self.save_cancel_btnbox.setVisible(curtab in [const.TAB_MODLIST, const.TAB_FILETREE])

        if self.save_cancel_btnbox.isVisible():
            self.save_cancel_btnbox.setEnabled(
                (curtab == const.TAB_MODLIST and len(self._modified_cells)>0)
            or  (curtab == const.TAB_FILETREE and self.file_tree_modified)
            )

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
        # populate database with data from disk
        self.Manager.loadActiveProfileData()

        # setup table dimensions & header
        self.mod_table.setColumnCount(4)
        self.mod_table.setHorizontalHeaderLabels(
                ["", "Mod ID", "Version", "Name",])

        # populate from mod-info database
        self.populateModTable()
        # enable sorting AFTER population
        # self.mod_table.setSortingEnabled(True) # no sorting! b/c install order matters

        # let double clicking toggle the checkbox
        self.mod_table.cellDoubleClicked.connect(self.toggleModState)

        # make columns fit their contents
        self.mod_table.resizeColumnsToContents()

        # setup action to handle user-changes to table
        self.mod_table.cellChanged.connect(self.onCellChanged)

        # connect cancel action to reset method
        self.changesCanceled.connect(self.resetTable)

        # let setup know we're done here
        self.SetupDone("setupTable")






    def populateModTable(self):
        self.mod_table.blockSignals(True)
        r=0

        #clear placeholder values
        self.mod_table.clearContents()
        self.mod_table.setRowCount(0)

        # for m in self.Manager.allmods():
        # for m in self.Manager.DB.conn.execute("SELECT name, modid, version, enabled FROM mods"):
        for m in self.Manager.basicModInfo():
            self.mod_table.insertRow(r)
            _enabled, _id, _ver, _name = m
            # self.LOGGER.debug("{} {} {} {}".format(_name, _id, _ver, _enabled))

            items = (QTableWidgetItem(), # first column is empty, is for the checkbox
                QTableWidgetItem(str(_id)),
                    QTableWidgetItem(_ver),
                    QTableWidgetItem(_name),
                     )

            # 1st column has checkbox indicating whether or not the mod is active
            items[const.COL_ENABLED].setFlags(Qt.ItemIsUserCheckable
                                              | Qt.ItemIsEnabled
                                              # | Qt.ItemIsDragEnabled
                                              # | Qt.ItemIsDropEnabled
                                              # | Qt.DragMoveCursor
                                              )
            # set check state from saved state
            items[const.COL_ENABLED].setCheckState(Qt.Checked if _enabled else Qt.Unchecked)

            items[const.COL_MODID].setFlags(Qt.ItemIsSelectable
                                            | Qt.ItemIsEnabled
                                            # | Qt.ItemIsDragEnabled
                                            # | Qt.ItemIsDropEnabled
                                            # | Qt.DragMoveCursor
                                            )

            # Version can just be selected
            items[const.COL_VERSION].setFlags(Qt.ItemIsSelectable
                                              | Qt.ItemIsEnabled
                                              # | Qt.ItemIsDragEnabled
                                              # | Qt.ItemIsDropEnabled
                                              # | Qt.DragMoveCursor
                                              )
            # name can be edited
            # todo: save changes to name
            items[const.COL_NAME].setFlags(Qt.ItemIsSelectable
                                           | Qt.ItemIsEditable
                                           | Qt.ItemIsEnabled
                                           # | Qt.ItemIsDragEnabled
                                           # | Qt.ItemIsDropEnabled
                                           # | Qt.DragMoveCursor
                                           )

            for i in range(4):
                self.mod_table.setItem(r,i,items[i])

            r+=1
        self.mod_table.blockSignals(False)

    def syncModListWithStates(self):

        for cell in self._modified_cells:
            row, col = cell   # get parts of tuple

            #TODO: remember! that db numbers start at 1!
            modinfo = self.Manager.DB.getOne("SELECT enabled, name FROM mods WHERE iorder = ?", row+1)

            if col == const.COL_ENABLED:
                self.mod_table.item(row,
                                    const.COL_ENABLED)\
                    .setCheckState(Qt.Checked if modinfo[0]   ## these should sync up...unless i'm bad at math
                                                   else Qt.Unchecked)
            elif col == const.COL_NAME:
                self.mod_table.item(row, const.COL_NAME).setText(modinfo[1])

    def toggleModState(self, row, column):
        if column > 2: return  # only the first 3 columns (box, id, ver)

        # grab the first column ( the checkable one)
        item = self.mod_table.item(row, const.COL_ENABLED)
        item.setCheckState(Qt.Unchecked if item.checkState() == Qt.Checked else Qt.Checked)

    def onCellChanged(self, row, col):
        self.LOGGER.debug("Cell ({}, {}) changed".format(row, col))

        # only enable on first change
        # if not self.mod_list_modified:

        # if the list of changes is empty:
        if not self._modified_cells:
            # self.mod_list_modified = True
            self.save_cancel_btnbox.setEnabled(True)

        self._modified_cells.append((row, col))

    def resetTable(self):
        self.mod_table.blockSignals(True)
        self.syncModListWithStates()
        self._modified_cells.clear()

        # self.mod_list_modified = False
        # self.disableSaveCancelButtons(
        self.mod_table.blockSignals(False)
        self.updateUI()

    @pyqtSlot()
    def saveModsList(self):
        """
        If the list of installed mods has been modified (e.g.
        some mods marked inactive, names changed, etc.), save
        the modified status of the mods to a file
        :return:
        """
        # self.Manager.saveModList(self.modsByState())


        ## TODO: delegate this process to the mod manager
        for cell in self._modified_cells:
            if cell[1] == const.COL_NAME:
                ## NOTE: XXX: FIXME: TODO: remember that the "install order" (db primary key) starts at one
                self.Manager.DB.updateField(cell[0] + 1, cell[1], self.mod_table.item(cell[0], cell[1]).text())
            else:
                self.Manager.DB.updateField(cell[0] + 1, cell[1],
                                            bool(self.mod_table.item(cell[0], cell[1]).checkState()))

        self.Manager.saveModList()

        self._modified_cells.clear()
        # self.modListSaved.emit()
        self.updateUI()

    #===============================
    #  Profile-handling UI
    #==============================

    def setupProfileSelector(self):
        # ps = self.profile_selector

        model = ProfileListModel()
        # ps.clear() # clear placeholder data

        start_idx = 0
        for name, profile in self.Manager.getProfiles(names_only=False):
            # self.LOGGER.debug("{}: {}".format(name, profile))
            # ps.insertItem(0, name, profile)
            model.insertRows(data=profile)
            if name==self.Manager.active_profile.name:
                self.logger.debug("Setting {} as chosen profile".format(name))
                start_idx=model.rowCount()-1

        self.profile_selector.setModel(model)
        self.profile_selector.setCurrentIndex(start_idx)
        self.profile_selector.currentIndexChanged.connect(self.onProfileChange)
        self.new_profile_button.clicked.connect(self.onNewProfileClick)

        # let setup know we're done here
        self.SetupDone("ProfileSelector")



    def onNewProfileClick(self):
        popup = custom_widgets.NewProfileDialog()
        popup.comboBox.setModel(self.profile_selector.model())
        # popup.dataReady.connect(self.newProfileData)

        # display popup, wait for close and check signal
        if popup.exec_() == popup.Accepted:
            # add new profile if they clicked ok
            new_profile = self.Manager.newUserProfile(popup.final_name, popup.copy_from)

            self.profile_selector.model().addProfile(new_profile)

            #todo: set new profile as active

    @pyqtSlot('int')
    def onProfileChange(self, index):
        if index<0:
            # we have a problem...
            self.LOGGER.error("No profile chosen?!")
        else:
            self.Manager.active_profile = self.profile_selector.currentData(Qt.UserRole).name
            self.loadActiveProfile()

    def loadActiveProfile(self):
        # self.mod_table.reset()
        pass

    # SLOTS


    # def enableSaveCancelButtons(self):
    #     if not self.save_button.isEnabled():
    #         self.LOGGER.debug("Save/Cancel buttons enabled")
    #         self.save_button.setEnabled(True)
    #         self.cancel_button.setEnabled(True)
    #
    # def disableSaveCancelButtons(self):
    #     self.LOGGER.debug("Save/Cancel buttons disabled")
    #     self.save_button.setEnabled(False)
    #     self.cancel_button.setEnabled(False)

    # def onTableModified(self, row:int , col: int):
    #     if col in [const.COL_ENABLED, const.COL_NAME]: # checkbox or name
    #         self.mod_list_modified = True
    #         # self.updateUI()
    #         self.modListModified.emit()



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
