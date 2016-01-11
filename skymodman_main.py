#!/usr/bin/env python3
import os
import sys

from skymodman.managers import ModManager


def main():
    pass
    # from skymodman import skylog
    # MM = ModManager()
    # skylog.stop_listener()


USE_QT_GUI = os.getenv("USE_QT_GUI", True)


def myexcepthook(type, value, tb):
    import traceback
    from pygments import highlight
    from pygments.lexers import get_lexer_by_name
    from pygments.formatters.terminal import TerminalFormatter

    tbtext = ''.join(traceback.format_exception(type, value, tb))
    lexer = get_lexer_by_name("pytb", stripall=True)
    formatter = TerminalFormatter()
    sys.stderr.write(highlight(tbtext, lexer, formatter))

    sys.exit()


if __name__ == '__main__':
    # sys.excepthook = myexcepthook

    if USE_QT_GUI:
        from PyQt5.QtWidgets import QApplication
        from PyQt5.QtGui import QGuiApplication
        from skymodman.qt_interface.qt_launch import ModManagerWindow

        app = QApplication(sys.argv)

        #init our ModManager instance
        MM = ModManager()

        w = ModManagerWindow(manager=MM)
        w.resize(QGuiApplication.primaryScreen().availableSize()*3/5)
        w.show()

        sys.exit(app.exec_())
    else:
        main()

