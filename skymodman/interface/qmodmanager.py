from PyQt5.QtCore import QObject, pyqtSignal as Signal

from skymodman.managers.modmanager import ModManager
from skymodman.interface.ui_utils import blocked_signals




class QModManager(QObject, ModManager):
    """
    This is a QObject-wrapper around the non-GUI ModManager class that
    allows it to send signals to rest of the Qt interface
    """

    alertsChanged = Signal()
    """emitted when Alerts are added to or removed from the alerts set"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


    def add_alert(self, alert):
        if super().add_alert(alert):
            self.alertsChanged.emit()


    def remove_alert(self, alert):
        if super().remove_alert(alert):
            self.alertsChanged.emit()

    def check_alerts(self):
        # copy current alerts
        prev_alerts = set(self.alerts)

        super().check_alerts()

        # compare old and new
        if self.alerts != prev_alerts:
            self.alertsChanged.emit()

    def check_dirs(self):
        # copy current alerts
        prev_alerts = set(self.alerts)

        # block signals on self since remove/add will be called several
        # times
        with blocked_signals(self):
            super().check_dirs()

        # compare old and new
        if self.alerts != prev_alerts:
            self.alertsChanged.emit()


