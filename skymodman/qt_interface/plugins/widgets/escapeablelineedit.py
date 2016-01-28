from PyQt5.QtWidgets import QLineEdit
from PyQt5.QtCore import Qt, pyqtSignal

class EscapeableLineEdit(QLineEdit):

    escapeLineEdit = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)

    def keyPressEvent(self, event):
        """

        :param QKeyEvent event:
        :return:
        """

        if event.key() == Qt.Key_Escape:
            self.escapeLineEdit.emit()

        super().keyPressEvent(event)
