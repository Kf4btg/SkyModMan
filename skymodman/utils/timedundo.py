"""
An extension to David Townshend's undo.py module that allows
grouping repeated commands based on time elapsed since the previous command.
"""
from threading import Timer
from contextlib import contextmanager

from skymodman.thirdparty.undo import undo

# class Printer:
#
#     def __lshift__(self, other):
#         print(other, end=" ")
#         return self
#
#     def __del__(self):
#         print()

_action = undo._Action
_undoable = undo.undoable

class TGroup:
    def __init__(self, desc=''):
        self._desc = desc
        self._stack = []

    @property
    def desc(self):
        return self._desc

    @desc.setter
    def desc(self, value):
        self._desc = value

    def append(self, action):
        self._stack.append(action)

    def undo(self):
        for undoable in reversed(self._stack):
            undoable.undo()

    def do(self):
        for undoable in self._stack:
            undoable.do()

    def clear(self):
        self._stack.clear()

    def __len__(self):
        return len(self._stack)

    def __getitem__(self, item):
        return self._stack[item]

    def text(self):
        return self._desc.format(count=len(self._stack))



class TimeStack(undo.Stack):
    """
    An extension to undo.Stack that adds timer handling. When the
    first undoable action is appended to the stack, a timer will be
    started; everything that is added to the stack before it runs
    out will go to a 'holding group,' which is much like a regular
    undo group, but groups actions that occur in quick succession.
    If the timer is already running when an append happens, it
    will be restarted at 0 and the holding group will continue to
    collect the actions.  When enough time has elapsed since the
    previous append--or when the user issues an undo command--the
    holding group is added to main undo stack as a single undoable,
    and the timer is disabled until the next append action occurs.
    """
    def __init__(self, dtmax=0.4):
        super().__init__()
        self._holding_group = TGroup()
        self._diverted_receiver = False
        self._receiver_paused = False

        self.timer = None #Timer(dtmax, self.ontimeout)
        self.timer_running = False
        self._timer_paused = False
        self.dtmax = dtmax

    def _resetTimer(self):
        self.timer = Timer(self.dtmax, self.ontimeout)
        self.timer_running = False
        self._timer_paused = False

    def ontimeout(self, *args, **kwargs):
        self.resetreceiver()  # set receiver back to undos
        if len(self._holding_group) > 1:
            # set the description to that of the most recently added item
            self._holding_group.desc = self._holding_group[-1].text()
            super().append(self._holding_group)
        else:
            super().append(self._holding_group[0])

        self._holding_group = TGroup() # get a new holding group
        self._resetTimer()

    def undo(self):
        if self.timer_running:
            # receiver is not currently set to the undostack;
            # So first, we'll stop the timer
            self.timer.cancel()
            # and the timeout function takes care of getting the undo
            # stack ready: we want to make sure that the actions
            # currently being held in the holding stack are properly
            # added to the undos before the undo is called
            self.ontimeout()

        super().undo()

    def append(self, action):

        if self._receiver_paused:
            # we're in an undo/redo call in the base class.
            # we don't need to handle anything here, so just
            # redirect to super
            super().append(action)

        elif self._diverted_receiver:
            # receiver is elsewhere

            # If our timer isn't running, then the receiver was diverted
            # before the previous append call (if any). We don't want to
            # mess up where the actions go, so we won't do anything in
            # this case

            # if timer IS running...
            if self.timer_running:

                # turn it off. But...
                self.timer.cancel()

                # we'll mark it as PAUSED to indicate that we should set
                # the receiver back to the holding group and restart
                # the timer once the receiver is reset
                self._timer_paused = True

            super().append(action)

        elif self._timer_paused:
            # receiver is back here, but when it was gone, we marked
            # our timer paused to make sure we knew to reset the
            # receiver to the holding group when we got it back
            self._timer_paused = False

            # this should have been done in reset
            # self._receiver = self._holding_group

            self.timer = Timer(self.dtmax, self.ontimeout)
            self.timer_running = True

            super().append(action)
            self.timer.start()

        elif self.timer_running:
            # If the timer is running, and the rec. is not diverted,
            # we just want to reset the timer to 0 to continue
            # grabbing actions

            # which first requires a cancel
            self.timer.cancel()
            # then back to original
            self.timer = Timer(self.dtmax, self.ontimeout)

            super().append(action)
            self.timer.start()

        else:
            # receiver not paused or diverted, timer not running
            # and not paused. this is a fresh start, so we'll want to
            # set up the timer and set our holding group as receiver
            self._receiver = self._holding_group
            self.timer = Timer(self.dtmax, self.ontimeout)
            self.timer_running = True

            super().append(action)
            self.timer.start()

    @contextmanager
    def _pausereceiver(self):
        """Had to reimplement this to only call the baseclass version so as to avoid mass hysteria down in setreceiver()"""
        super().setreceiver([])

        # this is only called during the undo()/redo() of
        # the base class, so we don't want it interacting with all the
        # special jazz down in our re/setreceiver overrides

        self._receiver_paused = True
        yield
        super().resetreceiver()
        self._receiver_paused = False


    def setreceiver(self, receiver=None):
        try:
            super().setreceiver(receiver)
            # this should only get called from outside the class, so we
            # can always consider the receiver diverted at this point
            self._diverted_receiver = True
        except AssertionError:
            # ... unless somebody passed None of course, so we'll
            # ignore that
            pass

    def resetreceiver(self):
        if self._diverted_receiver:
            # someone is returning the receiver.

            # that's nice. Let's note that.
            self._diverted_receiver = False

            # we should reset it to our holding group to catch any
            # appends that come immediately after this
            self._receiver = self._holding_group

        else:
            # the receiver is currently the holding group,
            # so we need to set it to _undos
            self._receiver = self._undos


_stack = None
def stack():
    global _stack
    if _stack is None:
        _stack = TimeStack()
        undo.setstack(_stack)
    return _stack

def setstack(stack):
    global _stack
    _stack = stack
    undo.setstack(_stack)

