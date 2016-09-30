from collections import deque

from PyQt5.QtCore import QObject, pyqtSignal as Signal, pyqtSlot as Slot

from skymodman.managers.modmanager import ModManager
# from skymodman.interface.ui_utils import blocked_signals

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
        # prev_alerts = set(self.alerts)

        # block signals on self since remove/add will be called several
        # times
        # with blocked_signals(self):
        #     super().check_dirs()

        # rather than blocking signals, queue them up
        self.begin_queue_signals()
        super().check_dirs()
        # this will emit any queued signals (once per type)
        self.end_queue_signals()

        # compare old and new
        # if self.alerts != prev_alerts:
        #     self.emit_signal(self.alertsChanged)

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

        ## create tuple of the signal and its arguments
        siginfo=(signal, *args)
        ## and of the signature of the signal
        # -- the 'signal' property is the 'signature of the signal that
        # would be returned by SIGNAL()'; it is a string that appears
        # like '2alertsChanged()' or '2newProfileLoaded(QString)' (and
        # no, I don't know why there's a 2 on the front). It should serve
        # as a unique string that can identify whether 2 signals represent
        # the same class attr
        sigsig = (signal.signal, *args)

        # check if we've already got a sig+args combo that matches
        if sigsig not in self._qmembers:
            # if not, queue it up
            # -- appendleft() so we can just pop() the first items
            #    off the right side later
            self.sigqueue.appendleft(siginfo)

            # and add it to the member set, too
            ## Use signal signatures names to track membership because
            # (apparently) two bound signals of the same type do not
            # compare equal
            self._qmembers.add(sigsig)

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

