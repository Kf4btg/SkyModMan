import asyncio
from tempfile import TemporaryDirectory

from PyQt5.QtCore import Qt, QObject, pyqtSignal
from PyQt5.QtWidgets import QProgressDialog
import quamash

from skymodman import Manager
from skymodman.interface.dialogs import message
from skymodman.log import withlogger


@withlogger
class InstallerUI(QObject):

    modAdded = pyqtSignal(str)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.tmpdir = None
        self.numfiles = 0
        # this should be instantiated from the main window after the
        # manager has been initialized
        self.Manager = Manager()

        # the current InstallManager instance
        self.installer = None


    async def do_install(self, archive, ready_callback=lambda:None, manual=False):
        """
        Determine the type of install (auto, manual, fomod), get the necessary
         info from the ModManager/InstallManager, and launch the necessary
         interface.

        :param archive: path to the mod archive to install
        :param manual: if False, attempt an auto or guided install (may
            still fall back to manual install); if True, show the
            manual-installation dialog by default.
        :param ready_callback: called when an installer dialog is about to be shown.
        """

        if manual:
            self.LOGGER << "initiating installer for manual install"

            self.installer = await self.Manager.get_installer(archive)
            modfs = await self.installer.mkarchivefs()
            ready_callback()
            await self._show_manual_install_dialog(modfs)

        else:
            # FIXME: make sure this temp dir is cleaned up even if we crash and burn during the install
            with TemporaryDirectory() as tmpdir:
                self.LOGGER << "Created temporary directory at %s" % tmpdir

                self.installer = await self.Manager.get_installer(archive, tmpdir)

                ready_callback()

                # Fomod config was found and prepared
                if self.installer.has_fomod:
                    await self.run_fomod_installer(tmpdir)

                else:
                    self.LOGGER << "No FOMOD config found."

                    # count the files, and get the mod structure
                    # count = await installer.get_file_count()

                    # retrieve a view of the archive's contents as a pseudo-filesystem
                    modfs = await self.installer.mkarchivefs()

                    ## check the root of the file hierarchy for usable data
                    if modfs.fsck_quick():
                        ## if it's there, install the mod automatically
                        await self.extraction_progress_dialog()
                    else:
                        ## perform one last check if the previous search turned up nothing:
                        # if there is only one item on the top level
                        # of the mod and that item is a directory, then check inside that
                        # directory for the necessary files.

                        root_items = modfs.listdir("/")

                        ## only 1 item...
                        # ## which is a directory...
                        # ## that contains game data
                        if len(root_items) == 1 \
                                and modfs.is_dir(root_items[0]) \
                                and modfs.fsck_quick(root_items[0]):
                            self.LOGGER << "Game data found in immediate" \
                                           "subdirectory {0!r}.".format(str(root_items[0]))
                            await self.extraction_progress_dialog(str(root_items[0]))
                            # message("information", title="Game Data Found",
                            #         text="In immediate subdirectory '{}'. Automatic install of this data would be performed now.".format(root_items[0]))

                        else:
                            self.logger.warning("no toplevel items found; showing manual install dialog")
                            await self._show_manual_install_dialog(modfs)


    def install_successful(self):
        """Callback that should be invoked when an archive has been
        successfully installed.

        """

        # emit modAdded w/ just the name of the installation target dir
        self.modAdded.emit(self.installer.install_destination.name)

    async def run_fomod_installer(self, tmpdir):
        """
        Create and execute the Guided Fomod Installer, using the
        fomod config info loaded by `installer`; ``installer.has_fomod``
        must return True for this method to run.


        :param tmpdir: temporary directory where the files necessary for
            running the installer (and only those files) will be
            extracted. After the install, the folder and its contents
            will be deleted automatically.
        """
        from skymodman.interface.dialogs.fomod_installer_wizard import FomodInstaller

        # split the installer into a separate thread.
        with quamash.QThreadExecutor(1) as ex:
            wizard = FomodInstaller(self.installer, tmpdir)
            wizard.show()
            f = asyncio.get_event_loop(
                ).run_in_executor(ex, wizard.exec_)
            await f

        del FomodInstaller

    # async def do_manual_install(self, archive, ready_callback=lambda:None):
    #     """
    #     Get a tree representing the internal structure of `archive` and launch a dialog
    #     allowing the user to determine which of its contents to install.
    #
    #     :param archive:
    #     :param ready_callback: called when the dialog is about to be shown
    #     :return:
    #     """
    #     mod_contents = await Manager.get_mod_archive_structure(archive)
    #
    #     ready_callback()
    #     await self._show_manual_install_dialog(mod_contents)

    async def _show_manual_install_dialog(self, contents):

        from skymodman.interface.dialogs.manual_install_dialog import ManualInstallDialog

        self.logger << "creating manual install dialog"
        with quamash.QThreadExecutor(1) as ex:
            mi_dialog = ManualInstallDialog(contents)
            mi_dialog.show()
            f = asyncio.get_event_loop(
                ).run_in_executor(ex, mi_dialog.exec_)
            await f

        del ManualInstallDialog


    async def extraction_progress_dialog(self, start_dir=None):
        """
        Have the install manager extract the contents of its archive
        to the default installation location. Create a progress dialog
        that will show if the process is estimated to take more than
        ~4 seconds.

        :param start_dir: If the items to be extracted are not under the
            root of the archive but rather in a subfolder, pass the
            path to that folder as `start_dir`

        :return:
        """
        self.LOGGER << "Performing auto-install"

        # TODO: show notification when extraction is finished

        num_to_extract = (await self.installer.get_archive_file_count()) if not start_dir else self.installer.count_folder_contents(start_dir)

        dlg = QProgressDialog("Extracting Files...", "Cancel", 0, num_to_extract)
        dlg.setWindowModality(Qt.WindowModal)

        task = asyncio.get_event_loop().create_task(
            self._do_archive_install(dlg, start_dir))

        dlg.canceled.connect(task.cancel)

        # catch the finished task
        task.add_done_callback(self._install_finished)


    def _install_finished(self, task):
        """

        :param asyncio.Task task:
        :return:
        """

        if task.cancelled():
            self.LOGGER.warning("Install task was cancelled")
        elif task.exception():
            self.LOGGER.error("Exception raised by install task")
            self.LOGGER.exception(task.exception())
        else:
            self.LOGGER.info("Installation completed")
            self.modAdded.emit(self.installer.install_destination.name)

    async def _do_archive_install(self, progress_dlg, start_dir=None):
        try:
            await self.installer.install_archive(start_dir,
                lambda f, c: progress_dlg.setValue(c))

        except asyncio.CancelledError:
            self.LOGGER.warning("Extraction task cancelled")
            progress_dlg.setLabelText("Cleaning up...")
            # this hides & deletes the cancel button
            progress_dlg.setCancelButtonText("")
            progress_dlg.setMaximum(self.installer.num_files_installed_so_far)
            progress_dlg.setValue(0)
            await self.installer.rewind_install(
                lambda f, c: progress_dlg.setValue(c))

        # Or we could make sure that value == maximum at end...
        progress_dlg.reset()

