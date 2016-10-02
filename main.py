#!/usr/bin/env python3
import os
import sys
import asyncio

# from skymodman.managers import modmanager
from skymodman import constants, log, register_manager

# module-level QApplication reference
app = None




USE_QT_GUI = os.getenv(constants.EnvVars.USE_QT.value, True)

#
# def myexcepthook(type, value, tb):
#     import traceback
#     from pygments import highlight
#     from pygments.lexers import get_lexer_by_name
#     from pygments.formatters.terminal import TerminalFormatter
#
#     tbtext = ''.join(traceback.format_exception(type, value, tb))
#     lexer = get_lexer_by_name("pytb", stripall=True)
#     formatter = TerminalFormatter()
#     sys.stderr.write(highlight(tbtext, lexer, formatter))
#
#     sys.exit()

def main():
    from PyQt5.QtWidgets import QApplication
    # from PyQt5.QtGui import QGuiApplication
    import quamash

    # setup application and quamash event-loop
    ## use module-level application reference to avoid crashes on exit
    ## (see http://pyqt.sourceforge.net/Docs/PyQt5/gotchas.html#crashes-on-exit)
    global app
    app = QApplication(sys.argv)
    loop = quamash.QEventLoop(app)
    asyncio.set_event_loop(loop)

    # initialize the main window
    from skymodman.interface.managerwindow import ModManagerWindow
    w = ModManagerWindow()

    # after creation of the window, create and assign the backend
    from skymodman.interface.qmodmanager import QModManager
    mmanager = QModManager()
    register_manager(mmanager)

    # perform setup of sub-managers
    mmanager.setup()

    # notify main window backend is ready
    w.manager_ready()

    # show the window
    w.show()

    # run the event loop
    try:
        with loop:
            loop.run_forever()
    finally:
        mmanager.DB.shutdown()
        log.stop_listener()
    # from skymodman import skylog
    # MM = ModManager()
    # skylog.stop_listener()

def main_nogui():
    pass

if __name__ == '__main__':
    # sys.excepthook = myexcepthook

    if USE_QT_GUI:
        main()
    else:
        main_nogui()

