from PyQt5.QtWidgets import QTreeWidget
from PyQt5.QtCore import pyqtSignal


class MyTreeWidget(QTreeWidget):

    tree_structure_changed = pyqtSignal()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def dropEvent(self, event):
        super().dropEvent(event)

        self.tree_structure_changed.emit()
