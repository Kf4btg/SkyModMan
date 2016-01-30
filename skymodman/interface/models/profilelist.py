from PyQt5.Qt import QModelIndex
from PyQt5.QtCore import Qt, QAbstractListModel

from skymodman.utils import withlogger

@withlogger
class ProfileListModel(QAbstractListModel):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.profiles = []
        """:type: list[Profile]"""

    # noinspection PyUnresolvedReferences
    def addProfile(self, new_profile):
        """
        implement my own API for adding stuff because the QCombobox is STUPID

        :param Profile new_profile: A Profile object to add to the model.
        """
        current_rows = self.rowCount()
        self.beginInsertRows(QModelIndex(), current_rows, current_rows)
        self.profiles.append(new_profile)
        self.endInsertRows()

        new_index = self.createIndex(current_rows, 0)
        self.dataChanged.emit(new_index, new_index)


    def rowCount(self, *args, **kwargs) -> int:
        return len(self.profiles)

    def data(self, index, role=Qt.UserRole):
        """
        Return name for DisplayRole, whole Profile object for UserRole

        :param QModelIndex index:
        :param role:
        :return:
        """
        if not index.isValid(): # or not (0<index.row()<len(self.profiles)):
            return

        if role==Qt.UserRole:
            return self.profiles[index.row()]

        if role==Qt.DisplayRole:
            return self.profiles[index.row()].name.capitalize()


    def insertRows(self, row=0, count=1, parent_index=QModelIndex(), data=None, *args, **kwargs):
        """
        Always append

        :param int row:
        :param int count:
        :param QModelIndex parent_index:
        :param Profile data:
        :return: boolean indicating success of the insertion
        :rtype: bool
        """
        # beginInsertRows(self, QModelIndex, first, last)
        self.beginInsertRows(parent_index, self.rowCount(), self.rowCount())
        if data:
            # self.LOGGER.debug("inserting data {}".format(data))
            self.profiles.append(data)
        self.endInsertRows()
        return True

    def removeRows(self, row, *args, **kwargs):
        """
        For now, this only removes one row at a time.

        :param int row: which row to drop.
        :return:
        """
        self.beginRemoveRows(QModelIndex(), row, row)
        try:
            del self.profiles[row]
        except IndexError as e:
            # TODO: handle w/ messagebox
            self.LOGGER.error(str(e))
            self.endRemoveRows()
            return False
        self.endRemoveRows()
        return True

if __name__ == '__main__':
    from skymodman.managers.profiles import Profile
    import skymodman.skylog as log

    model = ProfileListModel()
    model.removeRows(12)

    log.stop_listener()