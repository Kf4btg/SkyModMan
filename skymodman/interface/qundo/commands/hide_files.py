from PyQt5.QtWidgets import QUndoCommand


class ChangeHiddenFilesCommand(QUndoCommand):

    def __init__(self, hidden_before, hidden_after, text="",  *args, **kwargs):
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

