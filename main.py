#!/usr/bin/env python3
import os
import sys
import asyncio

from skymodman.managers import modmanager
from skymodman import constants, skylog


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
        from PyQt5.QtGui import QGuiApplication
        from skymodman.interface.managerwindow import ModManagerWindow
        import quamash

        app = QApplication(sys.argv)
        loop = quamash.QEventLoop(app)
        asyncio.set_event_loop(loop)

        #initialize the main ModManager
        modmanager.init()

        w = ModManagerWindow(app)
        # noinspection PyArgumentList
        # w.resize(QGuiApplication.primaryScreen().availableSize()*3/5)
        # w.resize(QGuiApplication.primaryScreen().availableSize()*5/7)
        w.show()

        try:
            with loop:
                loop.run_forever()
        # except:
            # skylog.stop_listener()
            # modmanager.db.shutdown()
            # raise
        finally:
            modmanager.db.shutdown()
            skylog.stop_listener()




            # ret = None
        # try:
        #     ret = app.exec_()
        # except:
        #     skylog.stop_listener()
        #     modmanager.db.shutdown()
        #     raise
        # finally:
        #     if ret is not None:
        #         sys.exit(ret)

    else:
        main()

