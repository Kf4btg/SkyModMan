from pathlib import Path
from os.path import exists
from functools import lru_cache

from PyQt5.QtCore import Qt, QModelIndex
from PyQt5.QtWidgets import QWizard, QWizardPage, QListWidgetItem, QLabel, QTreeWidgetItem, QStyledItemDelegate, QStyle, \
    QStyleOptionViewItem, QStyleOption, QProxyStyle, QTreeWidget
from PyQt5.QtGui import QPixmap, QPainter

from skymodman.interface.designer.uic.plugin_wizpage_ui import Ui_WizardPage
from skymodman.fomod.untangler2 import Fomod
from skymodman.fomod.common import GroupType, PluginType


class ScaledLabel(QLabel):
    """
    A QLabel designed to be used to display QPixmaps. It always
    shows its pixmap contents scaled to its current size while
    preserving the original aspect ratio.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._pixmap = QPixmap(self.pixmap())
        self._scaled_cache_valid = False

    def setScaledPixmap(self, from_file):
        """
        load the image `from_file` into a QPixmap and save in the
        self._pixmap attribute. If the file has been loaded recently,
        a cached version will be used rather than reloading from disk.
        After loading, the pixmap is scaled to the current dimensions
        of the label and displayed.

        :param from_file:
        """
        self._pixmap = get_pixmap_from_file(from_file)

        # if there have been any resize events since we last
        # loaded a pixmap, clear the cached scale-results.
        if not self._scaled_cache_valid:
            self.scale_pixmap.cache_clear()
            self._scaled_cache_valid = True

        self.setPixmap(self.scale_pixmap(from_file))


    @lru_cache(8)
    def scale_pixmap(self, filename):
        """
        If there have been no resize events since the last time
        the pixmap for `filename` was shown, then (assuming it's
        still in the cache), this will returned the saved, already-
        scaled pixmap instead of recomputing it.

        :param filename:
        """
        return scale_pixmap(self._pixmap,
                            self.width(),
                            self.height())

    def resizeEvent(self, event):
        """
        This redraws the current image scaled to the label size.
        It also invalidates the cached results of previous scale
        operations so that loading a previous image will not
        show an image of the incorrect dimensions
        :param event:
        """
        # self.scale_pixmap()
        self._scaled_cache_valid = False
        self.setPixmap(scale_pixmap(self._pixmap,
                                    self.width(),
                                    self.height()
                                    ))


def scale_pixmap(pixmap, width, height):
    return pixmap.scaled(width, height, Qt.KeepAspectRatio, Qt.SmoothTransformation)

@lru_cache(16)
def get_pixmap_from_file(file):
    """
    This uses an lru-cache to prevent reloading an image from disk
    if it has been recently loaded. Size is limited to 16 to prevent
    mods with many large images from devouring up RAM.
    :param file:
    """
    return QPixmap(file)

class FomodInstaller(QWizard):

    def __init__(self, fomod, files_path, *args, **kwargs):
        """

        :param Fomod fomod:
        :param args:
        :param kwargs:
        :return:
        """
        super().__init__(*args, **kwargs)

        self.fomod = fomod
        self.rootpath = files_path

        self.step_pages = []

        self.initUI()

        self.resize(800,800)

    def initUI(self):

        self.setObjectName("fomod_installer")
        self.setWizardStyle(QWizard.ClassicStyle)
        self.setOptions(QWizard.NoBackButtonOnStartPage)
        self.setWindowTitle("Mod Installation: "+self.fomod.modname.name)

        self.page_start = StartPage(self.rootpath, self.fomod.modname, self.fomod.modimage)

        self.addPage(self.page_start)

        steplist=self.fomod.installsteps
        for step in steplist:
            self.step_pages.append(PluginPage(self.rootpath, self.fomod.modname.name, step))

            self.addPage(self.step_pages[-1])


class StartPage(QWizardPage):
    def __init__(self,path, modname, modimage,  *args):
        super().__init__(*args)
        self.setTitle(modname.name)
        self.modroot = path

        if Path(self.modroot, modimage.path).exists():
            self.setPixmap(QWizard.WatermarkPixmap,
                              QPixmap(modimage.path))


class PluginPage(QWizardPage, Ui_WizardPage):
    def __init__(self, path, modname, step, *args):
        """

        :param Fomod.InstallStep step:
        :param args:
        :return:
        """
        super().__init__(*args)

        self.modroot =Path(path)
        self.setupUi(self)
        self.setTitle(modname)
        self.setSubTitle(step.name)

        self.plugin_list.clear()

        self.v_splitter.setSizes([300, 500])
        self.h_splitter.setSizes([200, 600])
        self.plugin_list.setStyleSheet("")


        # self.plugin_list.setItemDelegateForColumn(0, RadioDelegate(self.plugin_list))
        self.plugin_list.setStyle(customStyle(self.plugin_list.style()))

        for g in step.optionalFileGroups:

            gtype = g.type

            group_label = PluginGroup(gtype, g.plugin_order,
                                      self.plugin_list, [g.name])
            group_label.setFlags(Qt.ItemIsEnabled)

            for p in g.plugins:
                if gtype == GroupType.EXO:
                    i = RadioItem(group_label)
                else:
                    i = QTreeWidgetItem(group_label)
                i.setData(0, Qt.UserRole, p)

                # using a qlabel seems to be the only way to get
                # the text to wrap
                lab = QLabel(p.name)
                i.setFlags(Qt.ItemIsEnabled | Qt.ItemIsUserCheckable)
                QTreeWidgetItem.setCheckState(i, 0, Qt.Unchecked)

                lab.setWordWrap(True)

                lab.setMouseTracking(True)


                self.plugin_list.setItemWidget(i, 0, lab)

            group_label.setExpanded(True)

        self.plugin_list.itemEntered.connect(self.show_item_info)

    def on_plugin_list_itemClicked(self, item, column):
        """

        :param QTreeWidgetItem item:
        :param column:
        :return:
        """
        if item.flags() & Qt.ItemIsUserCheckable:
            item.setCheckState(0, item.checkState(0) ^ Qt.Checked)


    def show_item_info(self, item):
        """

        :param QTreeWidgetItem item:
        :return:
        """

        if item.flags() & Qt.ItemIsUserCheckable:
            plugin = item.data(0, Qt.UserRole)
            self.plugin_description_view.setText(plugin.description)

            if plugin.image:
                imgpath = Path(self.modroot, plugin.image).as_posix()

                if exists(imgpath):
                    self.label.setScaledPixmap(imgpath)


class PluginGroup(QTreeWidgetItem):
    def __init__(self, group_type, plugin_order, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.group_type = group_type

        self.exclusive = self.group_type == GroupType.EXO

        self.order = plugin_order

    def flags(self):
        return Qt.ItemIsEnabled

    def children(self):
        for i in range(self.childCount()):
            yield self.child(i)

    def uncheck_others(self, checked_item):
        for item in self.children():
            if item.checkState(0) & Qt.Checked and \
                item is not checked_item:
                # have to bypass the subclass override or nothing
                # will ever get unchecked...
                QTreeWidgetItem.setCheckState(item, 0, Qt.Unchecked)

class RadioItem(QTreeWidgetItem):
    def __init__(self, *args, **kwargs):
        """
        :param group: The Plugin Group this item belongs to
        """
        super().__init__(*args, **kwargs)
        self.group = self.parent()

        self.group_type = self.group.group_type

    def setCheckState(self, column, state):
        if not (self.checkState(column) & Qt.Checked):
            super().setCheckState(column, Qt.Checked)
            self.group.uncheck_others(self)


class customStyle(QProxyStyle):

    def drawPrimitive(self, element, option, painter, widget=None):
        """

        :param element:
        :param option:
        :param painter:
        :param QTreeWidget widget:
        :return:
        """
        if element == QStyle.PE_IndicatorCheckBox and isinstance(option.widget.itemFromIndex(option.index), RadioItem):
            # if option.index.parent()
            # if option.widget().itemFromIndex(option.index).group_type == GroupType.EXO:
            # index=option.index #type: # QModelIndex
            # print(index.flags())
            # print(widget)
            # print(dir(option.state))
            # print(dir(option))
            # print(option.checkState)
            # print(option.widget)
            # option.state |= QStyle.State_On
            # print(option.index.model().data(option.index, Qt.UserRole))
                super().drawPrimitive(QStyle.PE_IndicatorRadioButton,
                                  option, painter, widget)
        else:
            super().drawPrimitive(element,
                                  option, painter, widget)


class RadioDelegate(QStyledItemDelegate):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        QProxyStyle

    def paint(self, painter, option, index):
        """

        :param QPainter painter:
        :param option:
        :param QModelIndex index:
        :return:
        """
        print(option)
        option.state |= QStyle.State_On
        # option.state |= {
        #     Qt.Unchecked: QStyle.State_Off,
        #     Qt.Checked: QStyle.State_On,
        # }[index.internalPointer().checkState()]
        style=QApplication.style()


        style.drawPrimitive(QStyle.PE_IndicatorRadioButton,
                                option, painter)


    # def drawCheck(self, painter, option, rect, checkstate):
    #     if rect.isValid():
    #         option.rect = rect
    #         option.state &= ~QStyle.State_HasFocus
    #         option.state |= {
    #             Qt.Unchecked: QStyle.State_Off,
    #             Qt.Checked: QStyle.State_On,
    #         }[checkstate]
    #
    #     style = QApplication.style() # type: QStyle
    #
    #     style.drawPrimitive(QStyle.PE_IndicatorRadioButton,
    #                         option, painter)



if __name__ == '__main__':
    from PyQt5.QtWidgets import QApplication
    import sys

    app = QApplication(sys.argv)
    fwiz = FomodInstaller(Fomod('res/SMIM/fomod/ModuleConfig.xml'), 'res/SMIM')

    # img='res/PerMa.jpg'
    # img='res/STEP/STEP.png'
    # fwiz.setPixmap(QWizard.BannerPixmap, QPixmap(img))
    # fwiz.setPixmap(QWizard.LogoPixmap, QPixmap(img))
    # fwiz.setPixmap(QWizard.WatermarkPixmap, QPixmap(img))


    fwiz.show()

    sys.exit(app.exec_())