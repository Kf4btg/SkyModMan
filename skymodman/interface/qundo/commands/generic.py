from PyQt5.QtWidgets import QUndoCommand

class UndoCommand(QUndoCommand):
    """
    An extremely generic QUndoCommand that supports passing the
    redo and undo methods as parameters to the constructor
    """

    # __slots__ = ()
    # __slots__ = ("_preredo", "_postredo", "_preundo", "_postundo", "_undo", "_redo")

    __slots__ = ("_undo", "_redo")

    def __init__(self, text="", *args,
                 redo=None, undo=None,
                 pre_redo=None, post_redo=None,
                 pre_undo=None, post_undo=None):

        if text:
            super().__init__(text, *args)
        else:
            super().__init__(*args)

        # It may look like a mess, but we explicitly build functions
        # for each possible combination of provided arguments so that
        # we aren't making a lot of no-op method calls

        if redo is not None:
            if pre_redo is not None:
                # note:: have to assign to class attr since the C++
                # bindings will cause the pre_redo to be deleted if it's
                # "unbound" when __init__() (or the method that called
                # this constructor) finishes

                # .... or maybe not?

                # self._preredo=pre_redo

                if post_redo is not None:
                    # self._postredo = post_redo
                    def _():
                        pre_redo()
                        redo()
                        post_redo()
                else:
                    def _():
                        pre_redo()
                        redo()

            elif post_redo is not None:
                # self._postredo = post_redo
                def _():
                    redo()
                    post_redo()
            else:
                # _ = redo
                def _(): redo()
        else:
            def _(): pass

        self.redo=_
        # self._redo=_

        if undo is not None:
            if pre_undo is not None:
                # self._preundo=pre_undo
                if post_undo is not None:
                    # self._postundo = post_undo
                    def _():
                        pre_undo()
                        undo()
                        post_undo()
                else:
                    def _():
                        pre_undo()
                        undo()
            elif post_undo is not None:
                # self._postundo = post_undo
                def _():
                    undo()
                    post_undo()
            else:
                def _(): undo()
                # _ = undo
        else:
            def _(): pass

        self.undo=_
        # self._undo=_

    # so, unlike a pure python class, this qt/c++ derived subclass
    # can't just reassign methods like variables (e.g. "self.redo=_"),
    # at least not for overridden methods.
    # If we want the definition of the method to vary at runtime, we
    # have to make a placeholder method and call it within the
    # override. (Although, I admit, it actually SEEMED to work
    # the first way for one of the situations in which I make and
    # push an UndoCommand, but crashed hard a different time...but
    # this ensures that it'll work no matter what).

    # ...but wait! there's ...something else.
    # Seems it was just the part in init() where I used e.g.
    # "_ = undo" (effectively just assigning the passed callable to the
    # instance as the redo()/undo() methods. And that seems to be what
    # the problem was; I guess, in some instances, the callable
    # was getting deleted by Qt (but it hung around the other times?
    # hmmm...hope there's no memory leak there...). Actually
    # wrapping the callable in a proper "def _:" block fixed the
    # problem.

    # def redo(self): pass
        # self._redo()

    # def undo(self): pass
        # self._undo()

    # tried to prevent the spurious command grouping by explicitly
    # returning -1 from id()...but it didn't work. still don't
    # know why that happens, but it makes the whole system effectively
    # useless!!!

    # def id(self):
    #     return -1


# def test():
#     from functools import partial
#
#     preredo_=partial(print, "pre redo")
#     redo_=partial(print, "redo")
#     postredo_ = partial(print, "post redo")
#
#     preundo_ = partial(print, "pre undo")
#     undo_ = partial(print, "undo")
#     postundo_ = partial(print, "post undo")
#
#
#     return UndoCommand("testing",
#                           redo=redo_,
#                           undo=undo_,
#                           pre_redo=preredo_,
#                           post_redo=postredo_,
#                           pre_undo=preundo_,
#                           post_undo=postundo_
#                           )
#
# if __name__ == '__main__':
#
#     testcmd = test()
#
#     testcmd.redo()
#     testcmd.undo()

    # print("-----------")
    #
    # testcmd = UndoCommand("testing",
    #                       redo=redo_,
    #                       undo=undo_,
    #                       pre_redo=preredo_,
    #                       post_undo=postundo_
    #                       )
    #
    # testcmd.redo()
    # testcmd.undo()
    #
    # print("-----------")
    #
    # testcmd = UndoCommand("testing",
    #                       redo=redo_,
    #                       undo=undo_,
    #                       )
    #
    # testcmd.redo()
    # testcmd.undo()
    #
    # print("-----------")
    #
    # testcmd = UndoCommand("testing"
    #                       )
    #
    # testcmd.redo()
    # testcmd.undo()