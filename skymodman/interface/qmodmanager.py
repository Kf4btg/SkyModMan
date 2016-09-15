from PyQt5.QtCore import QObject, pyqtSignal as Signal, pyqtSlot as Slot

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


    ##=============================================
    ## Config-change slots
    ##=============================================

    @Slot(str, str, bool)
    def on_directory_changed(self, dir_key, new_value, profile_override):
        """Handle the user updating the configured path of an
        application directory"""

        # this will in turn call check_dir(), which may cause
        # alertsChanged to be emitted
        self.set_directory(dir_key, new_value, profile_override)

    # FIXME: this third parameter should be something else...whatever the "arbitrary python value" type is called
    @Slot(str, str, str)
    def on_setting_changed(self, section, key, new_value):
        """
        Note: not to be used when directories are changed. Use
        ``on_directory_changed`` for that.

        :param section: Currently, should always be GENERAL
        :param key: the config key for the setting
        :param new_value: the updated value
        """

        self.set_config_value(key, section, new_value, False)
