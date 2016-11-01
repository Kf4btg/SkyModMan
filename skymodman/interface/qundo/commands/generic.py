from PyQt5.QtWidgets import QUndoCommand

class UndoCommand(QUndoCommand):
    """
    An extremely generic QUndoCommand that supports passing the
    redo and undo methods as parameters to the constructor
    """

    # __slots__ = ("_preredo", "_postredo", "_preundo", "_postundo")
    __slots__ = ()

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
                _ = redo
        else:
            def _(): pass

        self.redo=_

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
                _ = undo
        else:
            def _(): pass

        self.undo=_

    # def redo(self):
    #     pass
    #
    # def undo(self):
    #     pass


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