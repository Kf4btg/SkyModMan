from pathlib import Path
from os.path import exists

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import (QWizard, QWizardPage,
                             QLabel, QTreeWidgetItem,
                             QStyle, QProxyStyle)

from skymodman.installer.fomod import Fomod
from skymodman.installer.common import GroupType, PluginType
from skymodman.interface.designer.uic.plugin_wizpage_ui import Ui_InstallStepPage


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
        modimgpath = Path(self.modroot, modimage.path).as_posix()

        if exists(modimgpath):
            self.setPixmap(QWizard.WatermarkPixmap,
                              QPixmap(modimgpath))


class PluginPage(QWizardPage, Ui_InstallStepPage):

    group_label_suffixes = {
        GroupType.EXO: " (Select One)",
        GroupType.ALL: " (All Required)",
        GroupType.AMO: " (Optional, Select One)",
        GroupType.ALO: " (Select At Least One)",
        GroupType.ANY: " (Optional)"
    }

    def __init__(self, path, modname, step, *args):
        """

        :param Fomod.InstallStep step:
        :param args:
        """
        super().__init__(*args)

        self.modroot =Path(path)
        self.setupUi(self)
        self.setTitle(modname)
        self.setSubTitle(step.name)

        self.plugin_list.clear()

        self.v_splitter.setSizes([300, 500])
        self.h_splitter.setSizes([200, 600])


        self.plugin_list.setStyle(
            RadioButtonStyle(self.plugin_list.style()))

        for group in step.optionalFileGroups:

            group_label = PluginGroup(
                group.type,
                group.plugin_order,
                self.plugin_list,
                [
                    group.name + self.group_label_suffixes[group.type]
                ])
            group_label.setFlags(Qt.ItemIsEnabled)

            for p in group.plugins:
                if group.type in [GroupType.EXO, GroupType.AMO]:
                    i = RadioItem(group_label)
                else:
                    i = QTreeWidgetItem(group_label)
                i.setData(0, Qt.UserRole, p)

                # using a qlabel seems to be the only way to get
                # the text to wrap
                lab = QLabel(p.name)

                if group.type == GroupType.ALL:
                    i.setFlags(Qt.ItemIsUserCheckable)
                    i.setCheckState(0, Qt.Checked)
                else:
                    i.setFlags(
                        Qt.ItemIsEnabled | Qt.ItemIsUserCheckable)
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
        """
        if item.flags() & Qt.ItemIsUserCheckable:
            item.setCheckState(0, item.checkState(0) ^ Qt.Checked)


    def show_item_info(self, item):
        """

        :param QTreeWidgetItem item:
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
        if state & Qt.Checked:
            super().setCheckState(column, state)
            self.group.uncheck_others(self)

        # only the "AtMostOne" groups should be uncheckable
        elif self.group_type == GroupType.AMO:
            super().setCheckState(column, state)



class RadioButtonStyle(QProxyStyle):

    def drawPrimitive(self, element, option, painter, widget=None):
        """
        Draws radio buttons for RadioItems rather than the normal
         check boxes

        :param element:
        :param option:
        :param painter:
        :param QTreeWidget widget:
        :return:
        """
        if element == QStyle.PE_IndicatorCheckBox and isinstance(option.widget.itemFromIndex(option.index), RadioItem):
                super().drawPrimitive(QStyle.PE_IndicatorRadioButton,
                                  option, painter, widget)
        else:
            super().drawPrimitive(element,
                                  option, painter, widget)



if __name__ == '__main__':
    from PyQt5.QtWidgets import QApplication, QTreeWidget
    import sys

    app = QApplication(sys.argv)
    # ffile, fpath = 'res/STEP/ModuleConfig.xml','res/STEP'
    # ffile, fpath = 'res/SMIM/fomod/ModuleConfig.xml','res/SMIM'
    ffile, fpath = 'res/SkyFallsMills/FOMod/ModuleConfig.xml','res/SkyFallsMills'
    fwiz = FomodInstaller(Fomod(ffile), fpath)

    # img='res/PerMa.jpg'
    # img='res/STEP/STEP.png'
    # fwiz.setPixmap(QWizard.BannerPixmap, QPixmap(img))
    # fwiz.setPixmap(QWizard.LogoPixmap, QPixmap(img))
    # fwiz.setPixmap(QWizard.WatermarkPixmap, QPixmap(img))


    fwiz.show()

    sys.exit(app.exec_())