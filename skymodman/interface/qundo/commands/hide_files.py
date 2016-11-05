from PyQt5.QtWidgets import QUndoCommand


class ChangeHiddenFilesCommand(QUndoCommand):

    def __init__(self, hidden_before, hidden_after, text="",  *args, **kwargs):
        """

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
