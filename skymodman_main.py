#!/usr/bin/env python3
import os
import sys

from skymodman import skylog
from skymodman.managers import ModManager


def main():

    MM = ModManager()


USE_QT_GUI = os.getenv("USE_QT_GUI", True)

if __name__ == '__main__':

    if USE_QT_GUI:
        from PyQt5.QtWidgets import QApplication
        from PyQt5.QtGui import QGuiApplication
        from skymodman.qt_interface.qt_launch import ModManagerWindow

        app = QApplication(sys.argv)

        #init our ModManager instance
        MM = ModManager()

        w = ModManagerWindow(MM)
        w.resize(QGuiApplication.primaryScreen().availableSize()*3/5)
        w.show()

        sys.exit(app.exec_())
    else:
        main()

    skylog.stop_listener()
