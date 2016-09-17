#!/usr/bin/env python3
import os
import sys
import asyncio

# from skymodman.managers import modmanager
from skymodman import constants, log, register_manager


def main():
    pass
    # from skymodman import skylog
    # MM = ModManager()
    # skylog.stop_listener()


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


if __name__ == '__main__':
    # sys.excepthook = myexcepthook

    if USE_QT_GUI:
        from PyQt5.QtWidgets import QApplication
        # from PyQt5.QtGui import QGuiApplication
        import quamash

        app = QApplication(sys.argv)
        loop = quamash.QEventLoop(app)
        asyncio.set_event_loop(loop)

        # initialize the main ModManager; this causes the Manager()
        # method to return the same instance everytime it is invoked
        # for the rest of the program's run
        # mmanager = modmanager.Manager()

        # import this after the manager invokation to ensure that
        # the manager is already created at the time the managerwindow
        # module obtains a reference to it.
        from skymodman.interface.managerwindow import ModManagerWindow


        w = ModManagerWindow()

        # after creation of the window, create and assign the backend
        from skymodman.interface.qmodmanager import QModManager
        mmanager = QModManager()
        register_manager(mmanager)

        w.manager_ready()
        # w.assign_modmanager(mmanager)

        w.show()

        try:
            with loop:
                loop.run_forever()
        finally:
            mmanager.DB.shutdown()
            log.stop_listener()
    else:
        main()

