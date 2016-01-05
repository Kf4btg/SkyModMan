from PyQt5 import Qt, QtCore
from PyQt5.QtCore import Qt as qt
from typing import List

from skymodman.utils import withlogger

@withlogger
class ProfileListModel(QtCore.QAbstractListModel):

    def __init__(self, *args):
        super(ProfileListModel, self).__init__(*args)

        self.profiles = [] # type: List[Profile]

    def addProfile(self, new_profile):
        """
        implement my own API for adding stuff because the QCombobox is STUPID
        :param new_profile:
        :return:
        """
        current_rows = self.rowCount()
        self.beginInsertRows(Qt.QModelIndex(), current_rows, current_rows)
        self.profiles.append(new_profile)
        self.endInsertRows()

        new_index = self.createIndex(current_rows, 0)
        self.dataChanged.emit(new_index, new_index)


    def rowCount(self, index=Qt.QModelIndex(), *args, **kwargs):
        return len(self.profiles)

    def data(self, index: Qt.QModelIndex, role=qt.UserRole):
        if not index.isValid(): # or not (0<index.row()<len(self.profiles)):
            return

        if role==qt.UserRole:
            return self.profiles[index.row()]

        if role==qt.DisplayRole:
            return self.profiles[index.row()].name.capitalize()


    def insertRows(self, row=0, count=1, parent_index = Qt.QModelIndex(), data=None, *args, **kwargs):
        """Always append"""
        # beginInsertRows(self, QModelIndex, first, last)
        # self.LOGGER.debug("begin insert rows")
        self.beginInsertRows(parent_index, self.rowCount(), self.rowCount())
        if data:
            # self.LOGGER.debug("inserting data {}".format(data))
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
            self.endRemoveRows()
            return False
        self.endInsertRows()
        return True

    # def setData(self, index: Qt.QModelIndex, data, role=None):
    #     """
    #     This is called by the combobox's "insertItem" method...though
    #     I'll be damned if I could find a SINGLE place in the documentation
    #     where that is mentioned or hinted at....
    #     :param index:
    #     :param data:
    #     :param role:
    #     """
    #     if role==qt.UserRole:
    #         self.profiles[index.row()] = data
    #         self.LOGGER.debug("    self.profiles[{}] = {}".format(index.row(), data))
    #         self.dataChanged.emit(index, index, [role])
    #         return True
    #     return False

if __name__ == '__main__':
    from skymodman.managers.profiles import Profile
    import skymodman.skylog as log

    model = ProfileListModel()
    model.removeRows(12)

    log.stop_listener()