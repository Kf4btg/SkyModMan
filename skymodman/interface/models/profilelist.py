from PyQt5.Qt import QModelIndex
from PyQt5.QtCore import Qt, QAbstractListModel, pyqtSignal

from skymodman.log import withlogger

@withlogger
class ProfileListModel(QAbstractListModel):
    """Contains a list of names of the available profiles. The UserRole
    contains the on-disk name, while the DisplayRole contains a
    capitalized version that will appear in the selector"""

    profileNameChanged = pyqtSignal(str, str)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.profiles = [] # type: list [str]

    def addProfile(self, new_profile):
        """
        implement my own API for adding stuff because the QCombobox is STUPID

        :param new_profile: A Profile object to add to the model.
        """

        if not isinstance(new_profile, str):
            # assume its a Profile instance in this case
            new_profile = new_profile.name

        current_rows = self.rowCount()
        self.beginInsertRows(QModelIndex(), current_rows, current_rows)
        self.profiles.append(new_profile)
        self.endInsertRows()

        new_index = self.createIndex(current_rows, 0)
        self.dataChanged.emit(new_index, new_index)

    def rename_profile(self, current_name, new_name):
        """Convenience wrapper for setData so callers don't need to go
        about determining the correct QModelIndex themselves"""

        # to avoid setting a profile name to an empty string
        if not (current_name and new_name):
            self.LOGGER.error("Arguments must be valid strings")
            return False

        try:
            row = self.profiles.index(current_name)

        except ValueError as e:
            # name not found
            self.LOGGER.error(f"Profile '{current_name}' not found")
            return False

        return self.setData(self.index(row), new_name)

    def rowCount(self, *args, **kwargs) -> int:
        return len(self.profiles)

    def data(self, index, role=Qt.UserRole):
        """
        Return capitalized name for DisplayRole, on-disk folder name
        for UserRole

        :param QModelIndex index:
        :param role:
        """
        if not index.isValid(): # or not (0<index.row()<len(self.profiles)):
            return None

        if role==Qt.UserRole:
            return self.profiles[index.row()]

        if role==Qt.DisplayRole:
            return self.profiles[index.row()].capitalize()

    def setData(self, index, value, role=Qt.UserRole):
        """
        Allow changing the UserRole to support renaming profiles
        via the model

        :param QModelIndex index:
        :param str value:
        :param role:
        """

        # for a valid index & role, update the name if a non-empty
        # string was passed
        if index.isValid() and role == Qt.UserRole and value:
            row = index.row()

            # remember current value
            old_name = self.profiles[row]

            # update to new value
            self.profiles[row] = value

            # emit signal with old_name, new_name
            self.profileNameChanged.emit(old_name, self.profiles[row])

            # notify attached views
            self.dataChanged.emit(index, index)

            return True

        return False

    def insertRows(self, row=0, count=1, parent_index=QModelIndex(), data=None, *args, **kwargs):
        """
        Always append

        :param int row:
        :param int count:
        :param QModelIndex parent_index:
        :param data:
        :return: boolean indicating success of the insertion
        :rtype: bool
        """
        #    beginInsertRows(self, QModelIndex, first, last)
        self.beginInsertRows(parent_index, self.rowCount(), self.rowCount())
        if data:
            _profile_name = data
            if not isinstance(data, str):
                # assume its a Profile instance in this case
                _profile_name = data.name
            # self.LOGGER.debug("inserting data {}".format(data))
            self.profiles.append(_profile_name)
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

# if __name__ == '__main__':
#     from skymodman.managers.profiles import Profile
#     import skymodman.skylog as log
#
#     model = ProfileListModel()
#     model.removeRows(12)
#
#     log.stop_listener()