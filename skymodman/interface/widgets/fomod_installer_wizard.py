from pathlib import Path
from os.path import exists, join

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QWizard, QWizardPage, QListWidgetItem, QLabel
from PyQt5.QtGui import QPixmap

from skymodman.interface.designer.uic.plugin_wizpage_ui import Ui_WizardPage
from skymodman.fomod.untangler2 import Fomod

class ScaledLabel(QLabel):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._pixmap = QPixmap(self.pixmap())
        
    def setPixmap(self, pixmap):
        self._pixmap = pixmap
        super().setPixmap(pixmap)

    def resizeEvent(self, event):
        self.setPixmap(self._pixmap.scaled(
            self.width(), self.height(),
            Qt.KeepAspectRatio
        ))



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

        self.resize(600,500)



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

        for g in step.optionalFileGroups:
            group_label =QListWidgetItem(g.name)
            group_label.setFlags(Qt.ItemIsEnabled)
            self.plugin_list.addItem(group_label)
            for p in g.plugins:
                i = QListWidgetItem(p.name)
                i.setData(Qt.UserRole, p)
                i.setFlags(Qt.ItemIsEnabled | Qt.ItemIsUserCheckable)
                i.setCheckState(Qt.Unchecked)
                self.plugin_list.addItem(i)

        self.plugin_list.itemEntered.connect(self.show_item_info)

    def show_item_info(self, item):
        """

        :param QListWidgetItem item:
        :return:
        """

        if item.flags() & Qt.ItemIsUserCheckable:
            plugin = item.data(Qt.UserRole)
            self.plugin_description_view.setText(plugin.description)

            if plugin.image:
                imgpath = Path(self.modroot, plugin.image).as_posix()
                # print(imgpath)
                if exists(imgpath):
                    self.label.setPixmap(QPixmap(imgpath))

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