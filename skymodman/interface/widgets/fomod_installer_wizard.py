from pathlib import Path
from os.path import exists
from itertools import count

from PyQt5.QtCore import Qt, pyqtProperty
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import (QWizard, QWizardPage,
                             QLabel, QTreeWidgetItem,
                             QStyle, QProxyStyle,
                             QDialog)

# from skymodman.installer.fomod import Fomod
from skymodman.managers import installer
from skymodman.installer.common import GroupType, PluginType#, Dependencies, Operator
from skymodman.interface.designer.uic.plugin_wizpage_ui import Ui_InstallStepPage
from skymodman.interface.designer.uic.installation_wizpage_ui import Ui_FinalPage

class FomodInstaller(QWizard):

    Pages = []

    def __init__(self, install_manager, files_path, *args, **kwargs):
        """

        :param installer.InstallManager install_manager:
        :param args:
        :param kwargs:
        :return:
        """
        super().__init__(*args, **kwargs)
        self.installer = install_manager

        self.fomod = self.installer.current_fomod
        self.rootpath = files_path
        self.step_pages = []

        FomodInstaller.Pages = []

        # tracking page ids
        self.page_count = count()

        self.initUI()

        self.resize(800,800)

    def initUI(self):

        self.setObjectName("fomod_installer")
        self.setWizardStyle(QWizard.ClassicStyle)
        self.setOptions(QWizard.NoBackButtonOnStartPage |
                        QWizard.NoBackButtonOnLastPage  |
                        QWizard.NoCancelButtonOnLastPage)
        self.setWindowTitle("Mod Installation: " + self.fomod.modname.name)

        self.page_start = StartPage(self.rootpath, self.fomod.modname, self.fomod.modimage, next(self.page_count))

        self.addPage(self.page_start)
        FomodInstaller.Pages.append(self.page_start)

        steplist=self.fomod.installsteps
        for step in steplist:
            self.step_pages.append(
                InstallStepPage(
                    self.rootpath,
                    self.fomod.modname.name,
                    step, next(self.page_count),
                    self.installer
                ))

            self.addPage(self.step_pages[-1])

        FomodInstaller.Pages.extend(self.step_pages)

        self._final_page = FinalPage(self.rootpath,
                                     self.fomod.modname.name,
                                     self.fomod.modimage,
                                     self.installer)

        self.addPage(self._final_page)
        FomodInstaller.Pages.append(self._final_page)

    def done(self, result):
        if result != QDialog.Rejected:
            self.installer.check_conditional_installs()


        super().done(result)

class StartPage(QWizardPage):
    def __init__(self,path, modname, modimage, pageid, *args):
        super().__init__(*args)
        self.setTitle(modname.name)
        self.modroot = path

        self.pageid = pageid


        modimgpath = Path(self.modroot, modimage.path).as_posix()

        if exists(modimgpath):
            self.setPixmap(QWizard.WatermarkPixmap,
                              QPixmap(modimgpath))

class FinalPage(QWizardPage, Ui_FinalPage):
    def __init__(self, path, modname, modimage, install_manager, *args):
        super().__init__(*args)

        self.man = install_manager

        self.setupUi(self)

        self._opening_html = """
            <html><head><style type="text/css">
            body {font-family: monospace;}
            p, li { white-space: pre-wrap; }
            </style></head><body>
            <p>Installing the following files:</p>
            <ul>
            """

        self._closing_html = """</ul></body></html>"""
        self._html = []

        self.setTitle(modname)


    def initializePage(self):

        self.man.check_conditional_installs()
        self._html.append(self._opening_html)
        for f in self.man.install_files:
            self._html.append("<li>{0.source}</li>".format(f))


        self._html.append(self._closing_html)
        self.install_summary.setHtml("".join(self._html))

        self.install_progress.reset()

    def cleanupPage(self):
        self._html = []
        self.install_summary.setHtml("<html><body></body></html>")
        self.install_progress.reset()

class InstallStepPage(QWizardPage, Ui_InstallStepPage):

    group_label_suffixes = {
        GroupType.EXO: " (Select One)",
        GroupType.ALL: " (All Required)",
        GroupType.AMO: " (Optional, Select One)",
        GroupType.ALO: " (Select At Least One)",
        GroupType.ANY: " (Optional)"
    }

    def __init__(self, path, modname, step, pageid, install_manager, *args):
        """

        :param Fomod.InstallStep step:
        :param args:
        """
        super().__init__(*args)
        self.step = step
        self.installman = install_manager

        self.modroot =Path(path)
        self.setupUi(self)
        self.setTitle(modname)
        self.setSubTitle(step.name)

        # clear any placeholder data
        self.plugin_list.clear()

        self.pageid = pageid
        self.next_page_visible = True
        # print(pageid, step.name)


        #try to make page sections a reasonable default size
        self.v_splitter.setSizes([300, 500])
        self.h_splitter.setSizes([400, 400])

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
                self.installman,

                # parent, text
                self.plugin_list,
                [group.name +
                 self.group_label_suffixes[group.type]])

            for p in group.plugins:

                # the mutually-exclusive groups get radiobuttons
                if group.type in [GroupType.EXO, GroupType.AMO]:
                    i = RadioItem(p, group_label)
                # the rest, plain treewidgetitems w/ checkboxes
                else:
                    i = PluginItem(p, group_label)

                # store the Plugin object in the TreeWidgetItem
                i.setData(0, Qt.UserRole, p)

                # set 'all-required' groups to checked and disable
                # them to prevent unchecking
                if group.type == GroupType.ALL:
                    i.setFlags(Qt.ItemNeverHasChildren)
                    i.setCheckState(0, Qt.Checked)
                else:
                    i.setFlags(
                        Qt.ItemIsEnabled | Qt.ItemIsUserCheckable |
                        Qt.ItemNeverHasChildren)
                    QTreeWidgetItem.setCheckState(i, 0, Qt.Unchecked)


                # using a qlabel seems to be the only way to get
                # the text to wrap
                lab = QLabel(p.name)
                lab.setWordWrap(True)
                # this keeps our image/desc boxes working
                lab.setMouseTracking(True)
                # now set the label as the item widget for this row
                self.plugin_list.setItemWidget(i, 0, lab)
                i.label = lab

            # they can't be collapsed, but they need to be expanded
            group_label.setExpanded(True)
            # track group
            self.groups.append(group_label)

        # connect mouse-enter event to changing item image/description
        self.plugin_list.itemEntered.connect(self.show_item_info)

    def initializePage(self):
        for g in self.groups:
            for c in g.children():
                g.check_child_type(c)

    def cleanupPage(self):
        for g in self.groups:
            g.reset()

    def checkVisible(self):
        # print(self.step.visible)

        if self.step.visible:
            return self.installman.check_dependencies_pattern(self.step.visible)

        # if no visible element, always True
        return True


    def on_plugin_list_itemClicked(self, item, column):
        """

        :param QTreeWidgetItem item:
        :param column:
        """
        if item.flags() & Qt.ItemIsUserCheckable:
            ostate = item.checkState(column)
            item.setCheckState(column, ostate ^ Qt.Checked)
            item.parent().on_child_checkstateChanged(item, ostate, item.checkState(column))
            # noinspection PyUnresolvedReferences
            self.completeChanged.emit()


    def show_item_info(self, item):
        """
        :param QTreeWidgetItem item:
        """

        if item.flags() & Qt.ItemNeverHasChildren:
            plugin = item.data(0, Qt.UserRole)
            self.plugin_description_view.setText(plugin.description)

            # show image if there is one
            if plugin.image:
                imgpath = Path(self.modroot, plugin.image).as_posix()

                if exists(imgpath):
                    self.label.setScaledPixmap(imgpath)

    def isComplete(self):
        """If all groups on this page have a valid selection,
        enable the next/finish buttons"""
        return all(g.isValid for g in self.groups)
    
    def nextId(self):
        """
        Return the id of the next installation step whose visible parameter
        evaluates to True; if No further steps evaluate such, return -1
        :return:
        """

        next_id = super().nextId()

        if next_id != -1:
            try:
                if not FomodInstaller.Pages[next_id].checkVisible():
                    next_id = FomodInstaller.Pages[next_id].nextId()
            except AttributeError: # final final page
                pass

        return next_id




class PluginGroup(QTreeWidgetItem):

    def __init__(self, group_type, plugin_order, install_manager, *args, **kwargs):
        # noinspection PyArgumentList
        super().__init__(*args, **kwargs)

        self.group_type = group_type

        self.order = plugin_order

        self.installman = install_manager


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

    def get_plugin(self, item):
        """
        Return the Plugin object stored in the TreeWidgetItem `item`
        :param QTreeWidgetItem item:
        :return:
        """
        return item.data(0, Qt.UserRole)

    def on_child_checkstateChanged(self, item, old_state, new_state):
        """

        :param QTreeWidgetItem item:
        :param old_state:
        :param new_state:
        :return:
        """
        if old_state != new_state:

            if new_state & Qt.Checked:
                if self.group_type in [
                    GroupType.EXO, GroupType.AMO]:
                    self.uncheck_others(item)

                for flag in self.get_plugin(item).conditionFlags:
                    self.installman.set_flag(flag.name, flag.value)
            else:
                for flag in self.get_plugin(item).conditionFlags:
                    self.installman.unset_flag(flag.name)

    def check_child_type(self, child):
        """
        Notes:
        default-type: The default type of the plugin used if none of the specified dependency states are satisfied.
        dependencyPatterns: The list of dependency patterns against which to match the user's installation. The first pattern that matches the user's installation determines the type of the plugin.

        :param PluginItem child:
        :return:
        """

        ctype = child.plugin.type # default type

        if child.plugin.patterns:
            for pat in child.plugin.patterns:
                if self.installman.check_dependencies_pattern(pat.dependencies):
                    ctype = pat.type
                    break

        # print(child.plugin.name, ctype)

        if ctype == PluginType.REQ:
            child.setCheckState(0, Qt.Checked)
            # child.setDisabled(True)
            child.setFlags(Qt.ItemNeverHasChildren)

        elif ctype == PluginType.NOT:
            child.setCheckState(0, Qt.Unchecked)
            child.setFlags(Qt.ItemNeverHasChildren)
            child.label.setEnabled(False)

        elif ctype == PluginType.REC:
            child.setCheckState(0, Qt.Checked)


    def reset(self):
        for c in self.children():
            if c.checkState(0) & Qt.Checked:
                c.setCheckState(0, Qt.Unchecked)

    def change_plugin_status(self, plugin, enable):
        """

        :param plugin:
        :param bool enable:
        :return:
        """

        # print(plugin.files)

        if enable:
            for flag in plugin.conditionFlags:
                self.installman.set_flag(flag.name, flag.value)
            for file in plugin.files:
                self.installman.mark_file_for_install(file)
        else:
            for flag in plugin.conditionFlags:
                self.installman.unset_flag(flag.name)
            for file in plugin.files:
                self.installman.mark_file_for_install(file, False)

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

                self.change_plugin_status(item.plugin, False)

class PluginItem(QTreeWidgetItem):
    def __init__(self, plugin, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.group = self.parent()
        self.group_type = self.group.group_type
        self.plugin = plugin
        self.label = None


    def setCheckState(self, column, state):
        super().setCheckState(column, state)

        self.group.change_plugin_status(self.plugin, state & Qt.Checked)





class RadioItem(PluginItem):
    def __init__(self, *args, **kwargs):
        """
        :param group: The Plugin Group this item belongs to
        """
        # noinspection PyArgumentList
        super().__init__(*args, **kwargs)

    def setCheckState(self, column, state):
        if self.checkState(0) != state:
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
    # ffile, fpath = 'res/STEP/ModuleConfig.xml','res/STEP'
    # ffile, fpath = 'res/SMIM/fomod/ModuleConfig.xml','res/SMIM'
    ffile, fpath = 'res/SkyFallsMills/FOMod/ModuleConfig.xml','res/SkyFallsMills'

    im = installer.InstallManager()
    im.prepare_fomod(ffile)

    fwiz = FomodInstaller(im, fpath)

    # img='res/PerMa.jpg'
    # img='res/STEP/STEP.png'
    # fwiz.setPixmap(QWizard.BannerPixmap, QPixmap(img))
    # fwiz.setPixmap(QWizard.LogoPixmap, QPixmap(img))
    # fwiz.setPixmap(QWizard.WatermarkPixmap, QPixmap(img))


    fwiz.show()

    sys.exit(app.exec_())