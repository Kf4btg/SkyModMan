from PyQt5.QtWidgets import QUndoCommand


class ModifyHiddenFilesCommand(QUndoCommand):

    def __init__(self, item_clicked,
                 hidden_before, hidden_after,
                 model, text="", *args, **kwargs):
        """

        hb: { 12, 16, 34, 56, 67 }

        ha: { 12, 17, 56, 60 }

        =: { 12i, 16u, 17h, 34u, 56i, 60h, 67s }

        i={12, 56} => hb & ha
        h={17, 60} => ha - hb
        u={16, 34} => hb - ha


        :param hidden_before: list of hidden indices before the
            change event
        :param hidden_after: list of hidden indices after the change
            event
        :param text: undo-command text
        """

        if text:
            super().__init__(text, *args, **kwargs)
        else:
            super().__init__(*args, **kwargs)


        sha = set(hidden_after)
        shb = set(hidden_before)

        # get sorted lists of the indices we'll be operating on
        self._to_hide = sorted(sha - shb)
        self._to_unhide = sorted(shb - sha)

        self.model = model

        self._first_do = True


    def redo(self):

        # skip first redo
        if self._first_do:
            self._first_do = False
        else:
            # setDataResult() is a helper method on the model that
            # deletes the undo command if setData() returns False from the
            # model; it also calls dataChanged.emit()
            self.model.setDataResult(self.model.setData())
