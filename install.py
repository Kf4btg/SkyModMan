import locale
import sys
import textwrap

from argh import arg, dispatch_command
from dialog import Dialog

import fomod
from fomod.installer import IModInstaller, zenity, qt5
# import fomod.installer.zenity
import fomod.installer.easy
# import fomod.installer.qt5

# According to author of pythondialog:
# # This is almost always a good thing to do at the beginning of your programs:
# locale.setlocale(locale.LC_ALL, '')

# from pprint import pprint


def install(mod, installer: IModInstaller):

    plugin_handler = {
        "SelectAny"        : lambda pl : installer.selectAny(pl),
        "SelectExactlyOne" : lambda pl : installer.selectExactlyOne(pl),
        "SelectAtMostOne"  : lambda pl : installer.selectAtMostOne(pl),
        "SelectAll"        : lambda pl : installer.selectAll(pl)
    }

    # modName: given in installer constructor
    # TODO: handle other attributes

    #modimage: when we have an installer capable of showing images...

    # mod dependencies:
    if mod.moduleDependencies:
        if not installer.checkDependencyPattern(mod.moduleDependencies.dependencies):
            print("Dependencies not satisfied")
            # todo: handle showing a message box or something
            # about which deps are missing

    # required install files
    if mod.requiredInstallFiles:
        [installer.markFileForInstall(f, type) for type, flist in mod.requiredInstallFiles.items() for f in flist]

    # install steps
    installer.step_order = mod.installSteps.order
    for step in mod.installSteps.installStep:
        installer.step = step
        if not installer.checkVisiblePattern():
            continue
        for group in step.optionalFileGroups.group:
            installer.group = group
            plugin_list = group.plugins.plugin

            # should return a list of plugins that were selected,
            # or None if no plugins were selected
            results = plugin_handler[group.type](plugin_list)

            if results:
                for selected_plugin in results:
                    # set necessary flags
                    if selected_plugin.conditionFlags:
                        [installer.setFlag(flag.name, flag.text) for flag in selected_plugin.conditionFlags.flag]

                    # mark designated files for installation
                    if selected_plugin.files:
                        [installer.markFileForInstall(file, type) for type, flist in selected_plugin.files.items() for file in flist]

            # installer.groupHandler(group)

    # conditional file installs
    if mod.conditionalFileInstalls \
        and "patterns" in mod.conditionalFileInstalls:
        for pat in mod.conditionalFileInstalls.patterns.pattern:
            if installer.checkDependencyPattern(pat.dependencies):
                [installer.markFileForInstall(f, type) for type, flist in pat.files.items() for f in flist]

    # Process final Results (i.e. install marked files)
    installer.installFiles()




def install2(mod):

    d = Dialog(dialog="dialog", autowidgetsize=False)
    button_names = {d.OK: "Next", d.CANCEL: "Cancel", d.HELP: "Help", d.EXTRA: "Extra"}

    modname=mod.moduleName.text
    d.set_background_title(modname)
    d.msgbox("Welcome to the Installer for "+modname)

    tw = textwrap.TextWrapper(width=80, tabsize=2, break_long_words=False)

    step_order = mod.installSteps.order
    for step in mod.installSteps.installStep:
        d.set_background_title(step.name)

        # step_name = step.name

        for group in step.optionalFileGroups.group:

            if group.type == "SelectAny":
                choices = []
                for plugin in group.plugins.plugin:
                    choices.append((plugin.name, "{}".format(tw.fill(plugin.description)), False ))
                    # choices.append((plugin.name, row, 1, plugin.description, row, 2, 0, 0))
                code, tags = d.checklist(group.name, choices=choices, title=group.name, height=0, width=0)
                # code, tags = d.form(group.name, elements=choices, title=step.name)



            elif group.type == "SelectExactlyOne":
                plist = group.plugins.plugin
                if len(plist)==2 and plist[0].name in ["Yes", "No"] and plist[1].name in ["Yes", "No"] and plist[0].name != plist[1].name:
                        y = plist[0 if plist[0].name == "Yes" else 1].description
                        n = plist[1 if plist[0].name == "Yes" else 0].description

                        text = "{}\n\nYes: {}\n\nNo: {}".format(group.name, y, n)
                        response = d.yesno(text, title=group.name)
                else:
                    choices = []
                    text=[]
                    for plugin in plist:
                        choices.append((plugin.name, "", plugin.description))
                    code, tag = d.menu(group.description, choices=choices, title=group.name, item_help=True)




@arg('xml', help='The ModuleConfig.xml file for the fomod being installed.')
@arg('--useinstaller', help='The type of installer to use; valid options are: zenity')
@arg('--modfolder', help='Path to the folder where mods are installed.')
def main(xml, modfolder=None, useinstaller="qt5"):
    # mod = fomod.lxmlParse(xml)
    with open(xml, "rb") as x:
        mod = fomod.dictParse(x).config

    if modfolder is None:
        modfolder = '/home/datadir/games/skyrim/SkyDirs/2_mods'

    if useinstaller == "qt5":
        import asyncio
        from PyQt5.QtWidgets import QApplication
        from quamash import QEventLoop, QThreadExecutor

        app = QApplication(sys.argv)
        loop = QEventLoop(app)
        asyncio.set_event_loop(loop)

        installer = qt5.QTInstaller(mod)
        installer.mod_folder = modfolder

        # this feels more than a little bit hacky...
        # installer.install_process.begin_install.connect(install)
        installer.show()
        # sys.exit(app.exec_())
        with loop:
            loop.run_until_complete(installer.InstallMod())
    else:
        if useinstaller=="zenity":
            installer = fomod.installer.zenity.ZenityInstaller(mod.moduleName.text)


        else:
            # this won't work...
            installer = fomod.installer.IModInstaller(mod.moduleName.text)

        installer.mod_folder = modfolder
        install(mod, installer)


if __name__ == '__main__':
    dispatch_command(main)

    sys.exit(0)