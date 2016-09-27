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

    dirChanged = Signal(str, str)

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

    ##=============================================
    ## Alert Handling
    ##=============================================

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
    ## Profile proxy
    ##=============================================

    # def set_profile_override(self, profile, key, ovrd_path):
    #
    #     # if we just got the name
    #     if isinstance(profile, str):
    #         profile = self.Profiler[profile]
    #
    #     profile.set_override_path(key, ovrd_path)


    ##=============================================
    ## Config-change slots
    ##=============================================

    # def set_directory(self, key, path, profile_override=False):
    #     super().set_directory(key, path, profile_override)
    #
    #     if not profile_override:
    #         self.dirChanged.emit(key, path)


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

        # do_update = False

        try:
            self.Folders[key].move(new_path, remove_old, override)
            # fsutils.move_dir_contents(self.Paths.path(key, override),
            #                           new_path,
            #                           remove_old)

            # self.Paths.move_dir(key, new_path, remove_old, override)
        except exceptions.FileDeletionError as e:
            # this means the movement operation succeeded, but for some
            # reason the original folder could not be deleted. Go ahead
            # and update the configured path in this case.
            message('warning',
                    "Could not remove original folder.",
                    "The following error occurred:",
                    detailed_text=str(e), buttons='ok',
                    default_button='ok')
            # do_update = True
        except exceptions.FileAccessError as e:
            message('critical',
                    "Cannot perform move operation.",
                    "The following error occurred:",
                    detailed_text=str(e), buttons='ok',
                    default_button='ok')
        except exceptions.MultiFileError as mfe:
            s = ""
            for file, exc in mfe.errors:
                self.LOGGER.exception(exc)
                s += "{0}: {1}\n".format(file, exc)
            message('critical',
                    title="Errors during move operation",
                    text="The move operation may not have fully completed. The following errors were encountered: ",
                    buttons='ok', default_button='ok',
                    detailed_text=s)
        # else:
        #     do_update = True
        #
        # if do_update:
        #     self.set_directory(key, new_path, override)

        # if prev_path != self.get_directory(key, override):

        # no matter what happened, check for valid dir
        # self.check_dir(key)


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

