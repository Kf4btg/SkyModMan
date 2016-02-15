import asyncio
from PyQt5.QtWidgets import QProgressDialog
from tempfile import TemporaryDirectory

import quamash

from skymodman.managers import modmanager as Manager
from skymodman.interface.widgets import message, ManualInstallDialog
from skymodman.utils import withlogger

@withlogger
class InstallerUI:

    def __init__(self):
        self.tmpdir = None
        self.numfiles = 0


    async def do_install(self, archive, ready_callback=lambda:None):
        """
        Determine the type of install (auto, manual, fomod), get the necessary
         info from the ModManager/InstallManager, and launch the necessary
         interface.

        :param archive: path to the mod archive to install
        :param ready_callback: called when an installer dialog is about to be shown.
        """
        with TemporaryDirectory() as tmpdir:
            self.LOGGER << "Created temporary directory at %s" % tmpdir

            installer = await Manager.get_installer(archive, tmpdir)

            ready_callback()

            # Fomod config was found and prepared
            if installer.has_fomod:
                await self.run_fomod_installer(installer, tmpdir)

            else:
                self.LOGGER << "No FOMOD config found."

                # count the files, and get the mod structure
                # count = await installer.get_file_count()
                # tree = await installer.mod_structure_tree()
                modfs = await installer.mkarchivefs()

                # print("count:", count)
                # print(tree)

                # dataroot (folder which contains the actual game data) may
                # be different the current root of the filesystem
                # count, gamedata, dataroot = self.fsck_modfs(modfs)

                # if dataroot != modfs.root:




                # toplevcount, toplevdata = installer.analyze_structure_tree(tree)

                # print(toplevcount, toplevdata)

                # if count:
                if modfs.fsck_quick():
                    # await self.extraction_progress_dialog()
                    message("information", title="Game Data Found", text="")


                    # await installer.extract("/tmp/testinstall",
                    #                         entries=toplevdata["folders"]
                    #                                 +toplevdata["files"],
                    #                         callback=
                    #              )
                else:
                    # one last check if the previous search turned up nothing:
                    # if there is only one item on the top level
                    # of the mod and that item is a directory, then check inside that
                    # directory for the necessary files.
                    _list = modfs.listdir("/")
                    if len(_list) == 1 and modfs.is_dir(_list[0]) and modfs.fsck_quick(_list[0]):
                        message("information", title="Game Data Found",
                                text="In immediate subdirectory '{}'".format(_list[0]))

                    else:
                        self.logger.debug("no toplevel items found; showing manual install dialog")
                        await self._show_manual_install_dialog(modfs)


    async def run_fomod_installer(self, installer, tmpdir):
        """
        Create and execute the Guided Fomod Installer, using the fomod config
        info loaded by `installer`; ``installer.has_fomod()`` must return True for
        this method to run.

        :param installer: InstallManager instance that has already loaded a Fomod Config file.
        :param tmpdir: temporary directory where the files necessary for running the installer
        (and only those files) will be extracted. After the install, the folder and its contents
        will be deleted automatically.
        """
        from skymodman.interface.widgets import FomodInstaller

        # split the installer into a separate thread.
        with quamash.QThreadExecutor(1) as ex:
            wizard = FomodInstaller(installer, tmpdir)
            wizard.show()
            f = asyncio.get_event_loop(
                ).run_in_executor(ex, wizard.exec_)
            await f

        del FomodInstaller

    async def do_manual_install(self, archive, ready_callback=lambda:None):
        """
        Get a tree representing the internal structure of `archive` and launch a dialog
        allowing the user to determine which of its contents to install.

        :param archive:
        :param ready_callback: called when the dialog is about to be shown
        :return:
        """
        mod_contents = await Manager.get_mod_archive_structure(archive)

        ready_callback()
        await self._show_manual_install_dialog(mod_contents)

    async def _show_manual_install_dialog(self, contents):

        self.logger.debug("creating manual install dialog")
        with quamash.QThreadExecutor(1) as ex:
            mi_dialog = ManualInstallDialog(contents)
            self.LOGGER << "calling dialog.show()"
            mi_dialog.show()
            self.LOGGER << "dialog.show() done, about to exec"
            f = asyncio.get_event_loop(
                ).run_in_executor(ex, mi_dialog.exec_)
            await f


    async def extraction_progress_dialog(self, archive, entries, numfiles):
        dlg = QProgressDialog("Extracting Files...", "Cancel", 0, numfiles)




