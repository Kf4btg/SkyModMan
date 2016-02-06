from pathlib import Path
from os.path import exists

from PyQt5.QtCore import Qt, pyqtProperty, pyqtSignal
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import (QWizard, QWizardPage,
                             QLabel, QTreeWidgetItem,
                             QStyle, QProxyStyle)

from skymodman.installer.fomod import Fomod
from skymodman.installer.common import GroupType, PluginType
from skymodman.interface.designer.uic.plugin_wizpage_ui import Ui_InstallStepPage

from PyQt5.QtCore import QObject


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
        self.setWindowTitle("Mod Installation: " + self.fomod.modname.name)

        # set the isValid property as default for PluginGroups
        self.setDefaultProperty("PluginGroup", "isValid", "selectionChanged")

        self.page_start = StartPage(self.rootpath, self.fomod.modname, self.fomod.modimage)

        self.addPage(self.page_start)

        steplist=self.fomod.installsteps
        for step in steplist:
            self.step_pages.append(InstallStepPage(self.rootpath, self.fomod.modname.name, step))

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


class InstallStepPage(QWizardPage, Ui_InstallStepPage):

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

        # clear any placeholder data
        self.plugin_list.clear()

        #try to make page sections a reasonable default size
        self.v_splitter.setSizes([300, 500])
        self.h_splitter.setSizes([200, 600])

        # set custom style that enables showing RadioButtons
        # (instead of checkboxes) for mutually-exclusive groups
        self.plugin_list.setStyle(
            RadioButtonStyle(self.plugin_list.style()))

        # keep a list of the groups for easy reference
        self.groups = []

        # each group gets its own subsection in the list
        for group in step.optionalFileGroups:

            group_label = PluginGroup(
                group.type,
                group.plugin_order,
                self.plugin_list,
                [group.name +
                 self.group_label_suffixes[group.type]])

            # fname = group.name
            # if group.type in [GroupType.EXO,
            #                   GroupType.ALL,
            #                   GroupType.ALO]:
            #     fname += '*'  #mandatory
            # self.registerField(fname, self)

            for p in group.plugins:
                if group.type in [GroupType.EXO, GroupType.AMO]:
                    i = RadioItem(group_label)
                else:
                    i = QTreeWidgetItem(group_label)
                i.setData(0, Qt.UserRole, p)


                if group.type == GroupType.ALL:
                    i.setFlags(Qt.ItemIsUserCheckable)
                    i.setCheckState(0, Qt.Checked)
                else:
                    i.setFlags(
                        Qt.ItemIsEnabled | Qt.ItemIsUserCheckable)
                    QTreeWidgetItem.setCheckState(i, 0, Qt.Unchecked)


                # using a qlabel seems to be the only way to get
                # the text to wrap
                lab = QLabel(p.name)
                lab.setWordWrap(True)

                lab.setMouseTracking(True)

                self.plugin_list.setItemWidget(i, 0, lab)

            group_label.setExpanded(True)
            self.groups.append(group_label)
            # group_label.selectionChanged.connect(self.completeChanged.emit)

        self.plugin_list.itemEntered.connect(self.show_item_info)

    def on_plugin_list_itemClicked(self, item, column):
        """

        :param QTreeWidgetItem item:
        :param column:
        """
        if item.flags() & Qt.ItemIsUserCheckable:
            ostate = item.checkState(column)
            item.setCheckState(column, ostate ^ Qt.Checked)
            item.parent().on_child_checkstateChanged(item, ostate, item.checkState(column))
            self.completeChanged.emit()


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

    def isComplete(self):
        return all(g.isValid for g in self.groups)


class PluginGroup(QTreeWidgetItem):

    ## notifier signal for Wizard Fields
    selectionChanged = pyqtSignal()

    def __init__(self, group_type, plugin_order, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.group_type = group_type

        self.order = plugin_order


    _check_isvalid =  {
            GroupType.EXO:
                lambda g: sum(1 for c in g.children() if
                               (c.checkState(0) & Qt.Checked)) == 1,
            GroupType.AMO:
                lambda g: sum(1 for c in g.children() if
                               (c.checkState(0) & Qt.Checked)) <= 1,
            GroupType.ALO:
                lambda g: any((c.checkState(0) & Qt.Checked) for c in
                               g.children()),
            GroupType.ALL:
                lambda g: all((c.checkState(0) & Qt.Checked) for c in
                               g.children()),
            GroupType.ANY:
                lambda g: True
        }

    @pyqtProperty(bool)
    def isValid(self):
        """
        Returns whether a valid choice(s) has been made for this
        group (or if it is necessary)
        :return:
        """
        return self._check_isvalid[self.group_type](self)

    def flags(self):
        """
        These just need to be enabled.
        """
        return Qt.ItemIsEnabled

    def children(self):
        """
        Iterates over the plugins in the group (a flat list; there
        are no subtrees here)
        """
        for i in range(self.childCount()):
            yield self.child(i)

    def on_child_checkstateChanged(self, item, old_state, new_state):
        if old_state != new_state:
            if self.group_type in [GroupType.EXO, GroupType.AMO] and (new_state & Qt.Checked):
                self.uncheck_others(item)

    def uncheck_others(self, checked_item):
        """
        Only used for the EXO and AMO types
        :param checked_item:
        :return:
        """

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

        # only the "AtMostOne" radio groups should be uncheckable
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
    ffile, fpath = 'res/STEP/ModuleConfig.xml','res/STEP'
    # ffile, fpath = 'res/SMIM/fomod/ModuleConfig.xml','res/SMIM'
    # ffile, fpath = 'res/SkyFallsMills/FOMod/ModuleConfig.xml','res/SkyFallsMills'
    fwiz = FomodInstaller(Fomod(ffile), fpath)

    # img='res/PerMa.jpg'
    # img='res/STEP/STEP.png'
    # fwiz.setPixmap(QWizard.BannerPixmap, QPixmap(img))
    # fwiz.setPixmap(QWizard.LogoPixmap, QPixmap(img))
    # fwiz.setPixmap(QWizard.WatermarkPixmap, QPixmap(img))


    fwiz.show()

    sys.exit(app.exec_())