from PyQt5.QtWidgets import QFileSystemModel
from PyQt5.QtCore import Qt


class ModFileTreeModel(QFileSystemModel):

    def __init__(self, manager: 'ModManager', *args, **kwargs):
        super(ModFileTreeModel, self).__init__(*args, **kwargs)

        self.manager = manager
        self.current_dir = None

        self.modfileinfo = None

    def data(self, index, role=None):

        if role==Qt.CheckStateRole:
            if not self.hasChildren(index):  # ie is not  a directory
                return Qt.Checked



        return super(ModFileTreeModel, self).data(index, role)

    def flags(self, index):
        default_flags = super(ModFileTreeModel, self).flags(index)

        flags = default_flags | Qt.ItemIsUserCheckable

        if not flags & Qt.ItemNeverHasChildren:
            # file is directory
            flags |= Qt.ItemIsTristate

        return flags












if __name__ == '__main__':
    from skymodman.managers import ModManager
