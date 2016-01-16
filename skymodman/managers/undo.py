from collections import namedtuple

ActionDelta = namedtuple("ActionDelta", "action diff undo_callback")
                                    # str, tuple, callable(callable, tuple)


class ActionTracker:

    def __init__(self, target, *slots):
        self._target = target
        self._slots = slots

        # container of actionDelta stacks for each registered action slot
        self._actions = {s:[] for s in slots} # type: dict[str, list[ActionDelta]]

        # most recently used action
        self.mru_action = None


    @property
    def target(self):
        return self._target


    def add(self, delta: ActionDelta):
        self._actions[delta.action].append(delta)
        return self

    def __sub__(self, number):
        try: steps = int(number)
        except TypeError: return NotImplemented

        self.undo(self.mru_action, max(1,steps))

    def undo(self, action_slot, steps=1):
        slot = self._actions[action_slot]
        for s in range(min(steps, len(slot))):
            delta=slot.pop()
            a=getattr(self._target, delta.action)
            delta.undo_callback(a, delta.diff)


