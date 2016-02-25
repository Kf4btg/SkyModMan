import re

from PyQt5.QtCore import QRegularExpression
from PyQt5.QtGui import QRegularExpressionValidator
from PyQt5.QtWidgets import QDialog, QDialogButtonBox
from PyQt5.QtWidgets import QPushButton

from skymodman.interface.designer.uic.file_exists_dialog_ui import Ui_FileExistsDialog

class FileExistsDialog(QDialog, Ui_FileExistsDialog):

    def __init__(self, path, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setupUi(self)

        self.overwrite = False
        self.path = path
        self._oname = self.new_name = path.name

        self.label.setText(self.label.text().format(path=path))

        self.okbutton = self.btnbox.button(QDialogButtonBox.Ok) # type: QPushButton
        self.okbutton.setText("Rename")
        self.okbutton.setEnabled(False)

        self.btn_new_name.clicked.connect(self.on_suggest_new_name)

        self.btn_overwrite.setEnabled(True)
        self.btn_overwrite.clicked.connect(self.on_overwrite_clicked)

        self.name_edit.setText(self._oname)
        self.name_edit.textChanged.connect(self.on_name_changed)

        self._dirnames = self.path.sparent.ls(conv=str.lower)

        # any char other than / or : or NUL (not sure how to specify that one...)
        # ; also exclude \
        vre_str = r"[^/:\\]+"
        self.vre = QRegularExpression(vre_str)
        self.validator = QRegularExpressionValidator(self.vre)
        self.name_edit.setValidator(self.validator)

        # Also can't start with - or be . or ..
        # This one doesn't prevent entry, but disables the buttons
        # if the entered string matches
        self.reinvalid = re.compile(r"^(-.*|\.\.?$)")


    def on_name_changed(self, text):
        text = text.strip()

        valid = text and not self.reinvalid.match(text)

        if valid:
            exists = text.lower() in self._dirnames
            self.okbutton.setEnabled(not exists)
            self.btn_overwrite.setEnabled(exists)
        else:
            self.okbutton.setEnabled(False)
            self.btn_overwrite.setEnabled(False)

    def on_overwrite_clicked(self):
        self.overwrite=True
        self.accept()

    def on_suggest_new_name(self):
        suffix = 1

        getname = (self._oname+" {}").format
        newname = getname(suffix)
        while newname.lower() in self._dirnames:
            suffix+=1
            newname = getname(suffix)

        self.name_edit.setText(newname)

    def accept(self):
        """Qt override"""

        # name input by user
        self.new_name = self.name_edit.text()
        
        super().accept()


if __name__ == '__main__':
    # from PyQt5.QtGui import QGuiApplication
    from PyQt5.QtWidgets import QApplication
    from skymodman.utils.archivefs import ArchiveFS
    import sys

    app = QApplication(sys.argv)

    fs = ArchiveFS()
    fs.touch("/test/best/rest")

    d = FileExistsDialog(fs.CIPath("/test/best"))

    d.show()

    app.exec_()

    print(d.new_name)
    print(d.overwrite)