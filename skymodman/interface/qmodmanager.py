from collections import deque

from PyQt5.QtCore import QObject, pyqtSignal as Signal, pyqtSlot as Slot

from skymodman import exceptions
from skymodman.managers.modmanager import ModManager
from skymodman.interface.ui_utils import blocked_signals
from skymodman.interface.dialogs import message




class QModManager(QObject, ModManager):
    """
    This is a QObject-wrapper around the non-GUI ModManager class that
    allows it to send signals to rest of the Qt interface
    """

    alertsChanged = Signal()
    """emitted when Alerts are added to or removed from the alerts set"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # this is used when a number of changes are
        # being made at once; while it is true, all triggered signals
        # will be put in a queue that will be processed
        # when it is False again.
        self.queue_signals = False

        # a quick, rough implementation of ordered-set:
        # store the items in both a set and a deque;
        # check the set for existence of a new element before
        # adding it to the deque. Just make sure to keep them in sync!
        self._qmembers = set()
        self.sigqueue = deque()


    def add_alert(self, alert):
        if super().add_alert(alert):
            self.emit_signal(self.alertsChanged)

    def remove_alert(self, alert):
        if super().remove_alert(alert):
            self.emit_signal(self.alertsChanged)

    def check_alerts(self):
        # copy current alerts
        prev_alerts = set(self.alerts)

        super().check_alerts()

        # compare old and new
        if self.alerts != prev_alerts:
            self.emit_signal(self.alertsChanged)

    def check_dirs(self):
        # copy current alerts
        prev_alerts = set(self.alerts)

        # block signals on self since remove/add will be called several
        # times
        with blocked_signals(self):
            super().check_dirs()

        # compare old and new
        if self.alerts != prev_alerts:
            self.emit_signal(self.alertsChanged)


    ##=============================================
    ## Config-change slots
    ##=============================================

    @Slot(str, str, bool, bool)
    def move_dir(self, key, new_path, remove_old, override=False):
        """
        Attempt to move the folder for the given key from its current
        location to `new_path`. If successful, update the configured
        path. Show error dialogs if something goes wrong.

        :param key:
        :param new_path:
        :param remove_old:
        :return:
        """
        # prev_path = self.get_directory(key, override)

        try:
            self.Paths.move_dir(key, new_path, remove_old, override)
        except exceptions.FileAccessError as e:
            message('critical',
                    "Cannot perform move operation.",
                    "The following error occurred:",
                    detailed_text=str(e), buttons='ok',
                    default_button='ok')
        except exceptions.MultiFileError as mfe:
            s = ""
            for file, exc in mfe.errors:
                s += "{0}: {1}\n".format(file, exc)
            message('critical',
                    title="Errors during move operation",
                    text="The move operation may not have fully completed. The following errors were encountered: ",
                    buttons='ok', default_button='ok',
                    detailed_text=s)

        # if prev_path != self.get_directory(key, override):

        # no matter what happened, check for valid dir
        self.check_dir(key)


    # XXX: these are largely unnecessary...the only advantage they
    # offer is being decorated with the @pyqtSlot() decorator, which
    # should speed up the connection a bit, but probably not enough
    # to make up for the fact that they are simply another level
    # of redirection and mostly don't do anything other than
    # call a corresponding super() method

    # @Slot(str, str, bool)
    # def set_directory(self, key, path, profile_override=False):
    #     """Handle the user updating the configured path of an
    #     application directory"""
    #
    #     # this will in turn call check_dir(), which may cause
    #     # alertsChanged to be emitted
    #     self.set_directory(dir_key, new_value, profile_override)

    # # FIXME: this third parameter should be something else...whatever the "arbitrary python value" type is called
    # @Slot(str, str, str)
    # def on_setting_changed(self, section, key, new_value):
    #     """
    #     Note: not to be used when directories are changed.
    #
    #     :param section: Currently, should always be GENERAL
    #     :param key: the config key for the setting
    #     :param new_value: the updated value
    #     """
    #     self.set_config_value(key, section, new_value, False)


    # @Slot(str)
    # def on_default_profile_change(self, profile_name):
    #     """
    #
    #     :param profile_name:
    #     """
    #     super().set_default_profile(profile_name)

    ##=============================================
    ## The signal queue
    ##=============================================

    def emit_signal(self, signal, *args):
        """Proxy method for emitting signals. Use this instead of
        a direct signal.emit() to allow queueing the signals"""
        if self.queue_signals:
            self.schedule(signal, *args)
        else:
            signal.emit(*args)

    @Slot()
    def begin_queue_signals(self):
        self.queue_signals = True

    @Slot()
    def end_queue_signals(self):
        self.queue_signals = False
        self.process_queue()

    def schedule(self, signal, *args):
        """Add a signal to the signal queue to be emitted later. If the
        same signal with the same arguments has already been added to
        the queue, it will not be added again."""

        # create tuple of the signal and its arguments
        siginfo=(signal, *args)
        # check if we've already got a sig+args combo that matches
        if siginfo not in self._qmembers:
            # if not, queue it up
            # -- appendleft() so we can just pop() the first items
            #    off the right side later
            self.sigqueue.appendleft(siginfo)
            # and add it to the member set, too
            self._qmembers.add(self.sigqueue[0])


    def process_queue(self):
        """Emit any signals that were queued up"""

        while self.sigqueue:
            # remember: queue elements are tuples of form
            # (signal_object, [arg1, ...])
            # --arguments are optional

            # pop the signal info off the queue
            si=self.sigqueue.pop()
            # if we have args, slice them out
            if len(si) > 1:
                si[0].emit(*si[1:])
            else:
                # otherwise just emit the signal (first elem)
                si[0].emit()

        ## cleanup queue afterwards
        self.sigqueue.clear()
        self._qmembers.clear()

