class Notifier:
    """Creates a callable object that waits to be called `count` number of times, then executes the given `callback` with the given args and kwargs"""

    def __init__(self, count, callback, *cb_args, **cb_kwargs):
        self.count = count
        self.callback = callback
        self.cbargs = cb_args
        self.cbkwargs = cb_kwargs

        self.timer = self.notify_wait(count)

    # def __call__(self, who=None):
    def __call__(self):
        try:
            # print("--call from {}".format(who))
            next(self.timer)
        except StopIteration:
            # print("--done--")
            self.callback(*self.cbargs, **self.cbkwargs)

    @staticmethod
    def notify_wait(count):
        calls = 1
        while calls < count:
            yield
            calls+=1