from PyQt5 import Qt, QtCore
from PyQt5.QtCore import Qt as qt
from typing import List

from skymodman.utils import withlogger

@withlogger
class ProfileListModel(QtCore.QAbstractListModel):

    def __init__(self, *args):
        super(ProfileListModel, self).__init__(*args)

        self.profiles = [] # type: List[Profile]

    def rowCount(self, index=Qt.QModelIndex(), *args, **kwargs):
        return len(self.profiles)

    def data(self, index: Qt.QModelIndex, role=qt.UserRole):
        if not index.isValid(): # or not (0<index.row()<len(self.profiles)):
            return

        if role==qt.UserRole:
            return self.profiles[index.row()]

        if role==qt.DisplayRole:
            return self.profiles[index.row()].name.capitalize()


    def insertRows(self, row=0, count=1, parent_index = None, data=None, *args, **kwargs):
        """Always append"""
        # beginInsertRows(self, QModelIndex, first, last)
        # self.beginInsertRows(Qt.QModelIndex(), position, position+rows-1)
        self.beginInsertRows(Qt.QModelIndex(), self.rowCount(), self.rowCount())
        if data:
            # self.LOGGER.debug("inserting item")
            self.profiles.append(data)
        self.endInsertRows()
        return True

    def removeRows(self, row, *args, **kwargs):
        self.beginRemoveRows(Qt.QModelIndex(), row, row)
        try:
            self.profiles.pop(row)
        except IndexError as e:
            # TODO: handle w/ messagebox
            self.LOGGER.error(str(e))
            return False

        return True

if __name__ == '__main__':
    from skymodman.managers.profiles import Profile
    import skymodman.skylog as log

    model = ProfileListModel()
    model.removeRows(12)

    log.stop_listener()