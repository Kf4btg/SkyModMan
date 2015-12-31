from . import IModInstaller, InstallerBase
from PyQt5.QtWidgets import QApplication, QMainWindow, QListWidgetItem
from PyQt5.QtWidgets import QAbstractItemView as SelectionMode
from PyQt5.QtCore import Qt, QThread, QObject, pyqtSignal, pyqtSlot, QCoreApplication
from queue import Queue


from .qtinstaller_ui import Ui_MainWindow

# Extension Method
def toggleCheckState(self: QListWidgetItem):
    self.setCheckState(Qt.Checked if self.checkState() is Qt.Unchecked else Qt.Unchecked)

#monkey patch the method in
QListWidgetItem.toggleCheckState = toggleCheckState
del toggleCheckState #clean up namespace


class installProxy(QObject):
    begin_install = pyqtSignal(object, IModInstaller)

    def __init__(self, installer:'QTInstaller', **kwargs):
        super(installProxy, self).__init__(**kwargs)
        self.installer = installer

    def run(self):
        self.begin_install.emit(self.installer.mod, self.installer)



class QTInstaller(InstallerBase, QMainWindow, Ui_MainWindow):

    begin_install = pyqtSignal(object, IModInstaller)


    def __init__(self, mod, **kwargs):
        super(QTInstaller, self).__init__(mod, **kwargs)

        # self.mod = mod

        # Set up the user interface from Designer.
        self.setupUi(self)

        # Connect up the buttons.
        # self.next_button.clicked.connect(self.next)
        self.quit_button.clicked.connect(self.quitInstaller)

        # create the thread that will handle showing plugin pages
        # self.plugin_worker = PluginWorker()
        # self.plugin_thread = QThread()
        # self.plugin_worker.moveToThread(self.plugin_thread)

        # connect signals
        # self.plugin_worker.resultsReady.connect()

        # item-click tracking
        self.previousItem = self.currentItem = None # type: QListWidgetItem

        # place to store results
        self.results_list = []

        # list of plugins that met requirements to be displayed
        self.shown_plugins = []

        # queue for communication with backend
        # self.queue = Queue()

        # workers
        # self.writer = ResultWriter(self.queue)
        # self.writer_thread = QThread()
        # self.writer.moveToThread(self.writer_thread)
        # self.writer_thread.started.connect(self.writer.run)
        # self.writer_thread.start()



        # self.listener = ResultListener(self.queue)

        # listener thread
        # self.listener_thread = QThread()
        # self.listener.moveToThread(self.listener_thread)
        # self.listener_thread.started.connect(self.listener.listen)
        # self.listener_thread.start()

        # begin install
        # self.next_button.clicked.connect(self.beginInstall)
        # self.begin_install(mod, self)
        # self.install_thread = QThread()
        # self.install_process = installProxy(self)
        self.next_button.clicked.connect(self.submitSelection)


    @pyqtSlot()
    def beginInstall(self):
        self.install_process.moveToThread(self.install_thread)
        self.install_thread.started.connect(self.install_process.run)
        self.install_thread.start()

        #change next button function
        self.next_button.clicked.connect(self.submitSelection)




    def addListItem(self, item, selected, flags) -> int:
        listitem = QListWidgetItem(item, self.plugin_list)
        listitem.setFlags(flags)
        if selected:
            listitem.setCheckState(Qt.Checked)
        else:
            listitem.setCheckState(Qt.Unchecked)

        self.plugin_list.addItem(listitem)
        # return the row-index of the newly-added item
        return self.plugin_list.row(listitem)

    def submitSelection(self):
        # print(self.results_list)
        self.appendResultToQueue(self.results_list)

    def appendResultToQueue(self, item):
        # self.results_list.append(item)
        self.queue.put(item)

    async def selectAll(self, plugin_list):
        return

    async def selectAny(self, plugin_list):
        self.resetState()
        choices = []
        self.plugin_list.setSelectionMode(SelectionMode.MultiSelection)


        # self.shown_plugins.clear()

        for plugin in plugin_list:
            if not self.shouldShowPlugin(plugin):
                continue
            choices.append(plugin.name)
        for c in choices:
            row = self.addListItem(c, True,
                             Qt.ItemIsEnabled |
                             Qt.ItemIsUserCheckable)
            self.shown_plugins.insert(row, [p for p in plugin_list if p.name == c][0])

        # self.listener.results_received.connect(self.getResults)

        # manage clicking items in the listview
        self.plugin_list.itemClicked.connect(self.onMultiSelectClick)

        # block and wait for results from queue
        return await self.queue.get()



    async def selectAtMostOne(self, plugin_list):
        self.resetState()
        self.plugin_list.setSelectionMode(SelectionMode.SingleSelection)


        # self.shown_plugins.clear()

        choices = []
        for plugin in plugin_list:
            if not self.shouldShowPlugin(plugin):
                continue
            choices.append(plugin.name)
        for c in choices:
            row = self.addListItem(c, False,
                             Qt.ItemIsEnabled |
                             Qt.ItemIsUserCheckable)
            self.shown_plugins.insert(row, [p for p in plugin_list if p.name == c][0])

        # manage clicking items in the listview
        self.plugin_list.itemClicked.connect(self.onSingleSelectClick)

        return await self.queue.get()

    async def selectExactlyOne(self, plugin_list):
        self.resetState()

        self.plugin_list.setSelectionMode(SelectionMode.SingleSelection)
        print (plugin_list)
        choices = []
        for plugin in plugin_list:
            if not self.shouldShowPlugin(plugin):
                continue
            choices.append(plugin.name)

        # here's an array for easy access to the plugin
        # referenced by a certain list-item
        # self.shown_plugins.clear()

        first = True
        for c in choices:
            row = self.addListItem(c, first,
                             Qt.ItemIsEnabled |
                             Qt.ItemIsUserCheckable)
            self.shown_plugins.insert(row, [p for p in plugin_list if p.name == c][0])
            first = False

        return await self.queue.get()
        # return self.plugin_list

    def plugin_handler(self, selection_type, plugin_list):
        self.resetState()
        super(QTInstaller, self).plugin_handler(selection_type, plugin_list)

    def resetState(self):
        self.previousItem = self.currentItem = None
        self.results_list.clear()
        self.shown_plugins.clear()

        self.plugin_list.clear()

    def trackClickState(self, clicked_item:QListWidgetItem):
        self.previousItem =  self.currentItem
        self.currentItem = clicked_item


    async def onMultiSelectClick(self, item:QListWidgetItem):
        item.toggleCheckState()

        self.addOrRemoveFromResults(item)

    async def onSingleSelectClick(self, item:QListWidgetItem):

        self.trackClickState(item)

        if self.previousItem is not None:
            if self.previousItem == item:
                # just clicked on the same item
                item.toggleCheckState()
                self.addOrRemoveFromResults(item)
            else:
                # assume that clicked item is unchecked
                self.previousItem.setCheckState(Qt.Unchecked)
                item.setCheckState(Qt.Checked)
                self.addOrRemoveFromResults(self.previousItem)
                self.addOrRemoveFromResults(item)
        else:
            item.setCheckState(Qt.Checked)
            self.addOrRemoveFromResults(item)

    def addOrRemoveFromResults(self, item):
        plugin = self.shown_plugins[self.plugin_list.row(item)]
        if item.checkState() is Qt.Unchecked:
            if plugin in self.results_list:
                self.results_list.remove(plugin)
        else:
            if plugin not in self.results_list:
                self.results_list.append(plugin)

    def quitInstaller(self):
        QApplication.instance().quit()





class ResultWriter(object):
    """
    Adds the list of results from the user's choices in the gui
    to the queue to be consumed by the listener
    """
    def __init__(self, queue:Queue): #, **kwargs):
        # super(ResultWriter, self).__init__(**kwargs)
        self.queue = queue

    def write(self, result):
        self.queue.put(result)

class ResultListener(QObject):
    """Listens for items to be added to the result queue
    and notifies the installer thread"""

    results_received = pyqtSignal(list)

    def __init__(self, queue, **kwargs):
        super(ResultListener, self).__init__(**kwargs)
        self.queue = queue

    @pyqtSlot()
    def listen(self):
        while True:
            result = self.queue.get()
            self.results_received.emit(result)






class PluginWorker(QObject):
    resultsReady = pyqtSignal(list)

    def __init__(self):
        super(PluginWorker, self).__init__()

        self.results_queue = Queue()

    @pyqtSlot(list)
    def selectAll(self, plugin_list, result_queue):
        pass

    @pyqtSlot(list)
    def selectAny(self, plugin_list, result_queue):
        pass

    @pyqtSlot(list)
    def selectAtMostOne(self, plugin_list, result_queue):
        pass

    @pyqtSlot(list)
    def selectExactlyOne(self, plugin_list, result_queue):
        pass





#
# if __name__ == '__main__':
#     import sys
#     app = QApplication(sys.argv)
#     main = QTInstaller()
#     main.show()
#     sys.exc_info(app.exec_())

