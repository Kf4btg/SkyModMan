import asyncio
from tempfile import TemporaryDirectory

from PyQt5.QtCore import Qt, QObject, pyqtSignal
from PyQt5.QtWidgets import QProgressDialog
import quamash

from skymodman import Manager
# from skymodman.interface.dialogs import message
from skymodman.log import withlogger


# TODO: add fields for changing the name/destination of the mod to all the installation tools

@withlogger
class InstallerUI(QObject):

    modAdded = pyqtSignal(str)
    installerReady = pyqtSignal()
    """emitted when the archive has been examined, the type
    of install has been determined, and the appropriate
    dialog is about to be shown"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.tmpdir = None

        # TODO: figure out -- consistently -- whether this includes/should include directories or not
        self.numfiles = 0 # will hold number of files to be installed


        # this should be instantiated from the main window after the
        # manager has been initialized
        self.Manager = Manager()

        # the current InstallManager instance
        self.installer = None

        # if we make it to the actual extraction process,
        # here's the progress dialog we can use
        self.pdialog : QProgressDialog = None

    ## methods for the progress dialog
    ## FIXME: due to the way 7z buffers its output to pipes, this "lack-of" progress dialog is much less useful than one would hope. During a 20 second extraction, it MIGHT update a total of 2 or 3 times. Not very informative. Would probably be better to show a busy indicator (instead of a progress line) and some text above it that shows the % done the last time we actually got feedback. So we'd maybe jump from 0, to 35%, to 70%, to done.

    # E.g somethign like this, where the bar in the middle is one of
    # those animated barber-shop-pole busy things.
    # Just update the progress % whenever we get more info.
    # Honestly, the cancel button is the real point of the dialog.
    #   ----------------------------------
    #   |   Extracting Files...          |
    #   |                                |
    #   |   Progress:           35%      |
    #   |   __________________________   |
    #   |   | // // // // // // // //|   |
    #   |   --------------------------   |
    #   |                                |
    #   |                    | Cancel |  |
    #   ----------------------------------


    def _create_progress_dialog(self,
            initial_text="Extracting Files...",
            cancel_text="Cancel"):
        ##Create the progress dialog. max-files taken from self.numfiles

        self.pdialog = QProgressDialog(initial_text,
                                  cancel_text,
                                  0, self.numfiles)
        self.pdialog.setWindowModality(Qt.WindowModal)

        # show after 1 sec, at least for testing
        self.pdialog.setMinimumDuration(0)
        self.pdialog.show()

    def _update_dialog(self, count, text):
        # call during extraction
        self.pdialog.setValue(count)
        self.pdialog.setLabelText(text)

    ##=============================================
    ## Installer hooks
    ## --- these are called from other modules
    ## to invoke the installer(s).
    ##=============================================

    async def do_install(self, archive, manual=False):
        """
        Determine the type of install (auto, manual, fomod), get the
        necessary info from the ModManager/InstallManager, and launch
        the appropriate interface.

        :param archive: path to the mod archive to install
        :param manual: if False, attempt an auto or guided install (may
            still fall back to manual install); if True, show the
            manual-installation dialog by default.
        """

        # this method is used as a task, so catch the CancelledError;
        # cancel is provided mainly in case something goes wrong and
        # whatever install-method was supposed to happen never gets
        # executed. The user can click the cancel button to stop
        # the "busy" indicator from running indefinitely
        # TODO: I feel like we should be able to determine when there was an exception and clear the busy indicator in that case without needing a manual cancel from the user

        try:
            if manual:
                #For explicitly-manual installs (not 'fallback-to-manual')

                # await self._do_install_manual(archive)
                self.LOGGER << "initiating installer for manual install"

                self.installer = await self.Manager.get_installer(
                    archive)
                modfs = await self.installer.mkarchivefs()

                # tell everyone we're ready
                self.installerReady.emit()

                await self._show_manual_install_dialog(modfs)

            else:
                # put this in its own function, for readability
                await self._do_install_auto_or_guided(archive)

        except asyncio.CancelledError:
            self.LOGGER.warning("Installation task cancelled!")

            #TODO: cleanup (...clean up what?)

    async def _do_install_auto_or_guided(self, archive):
        """could be a fomod (guided) install, or a simple extract op.
        If archive structure is incorrect for either of these, fallback
        to manual install"""

        # FIXME: make sure this temp dir is cleaned up even if we crash and burn during the install
        with TemporaryDirectory() as tmpdir:
            self.LOGGER << f"Created temporary directory at {tmpdir}"

            self.installer = await self.Manager.get_installer(archive,
                                                              tmpdir)

            # mod name could come from info.xml, or we may have to
            # derive it elsewhise
            self.installer.derive_mod_name()

            # Fomod config was found and prepared
            if self.installer.has_fomod:
                # tell everyone we're ready
                self.installerReady.emit()
                await self._run_fomod_installer(tmpdir)

            else:
                self.LOGGER << "No FOMOD config found."

                # retrieve a view of the archive's contents as a
                # pseudo-filesystem
                ## TODO: make better use of this!
                modfs = await self.installer.mkarchivefs()

                ## check the root of the file hierarchy for usable data
                if modfs.fsck_quick():
                    ## if it's there, install the mod automatically
                    self.installerReady.emit()
                    await self._auto_install()
                else:
                    ## perform one last check if the previous search
                    # turned up nothing:
                    # if there is only one item on the top level
                    # of the mod and that item is a directory, then
                    # check inside that directory for the necessary
                    # files.

                    root_items = modfs.listdir("/")

                    ## only 1 item...
                    # ## which is a directory...
                    # ## that contains game data
                    if len(root_items) == 1 \
                            and modfs.is_dir(root_items[0]) \
                            and modfs.fsck_quick(root_items[0]):
                        self.LOGGER << f"Game data found in immediate subdirectory {str(root_items[0])!r}."

                        self.installerReady.emit()
                        await self._auto_install(str(root_items[0]))
                    else:
                        self.LOGGER.warning(
                            "no toplevel items found; "
                            "showing manual install dialog")

                        self.installerReady.emit()
                        await self._show_manual_install_dialog(modfs)


    async def _auto_install(self, start_dir=None):
        self.LOGGER << "Performing auto-install"
        if not start_dir:
            self.numfiles = await self.installer.get_archive_file_count()
        else:
            self.numfiles = await self.installer.count_folder_contents(start_dir)

        self._create_progress_dialog()
        self._extract_with_progress(
            self.installer.install_archive(start_dir))


    async def _show_manual_install_dialog(self, contents):

        from skymodman.interface.dialogs.manual_install_dialog import ManualInstallDialog

        self.logger << "creating manual install dialog"
        with quamash.QThreadExecutor(1) as ex:
            mi_dialog = ManualInstallDialog(contents)
            mi_dialog.show()
            f = asyncio.get_event_loop(
                ).run_in_executor(ex, mi_dialog.exec_)
            await f

        if mi_dialog.result() == ManualInstallDialog.Accepted:

            self.numfiles = await self.installer.count_folder_contents(mi_dialog.root_path)
            self._create_progress_dialog()

            self._extract_with_progress(
                self.installer.install_archive(mi_dialog.root_path))

        del ManualInstallDialog


    async def _run_fomod_installer(self, tmpdir):
        """
        Create and execute the Guided Fomod Installer, using the
        fomod config info loaded by `installer`; ``installer.has_fomod``
        must return True for this method to run.


        :param tmpdir: temporary directory where the files necessary for
            running the installer (and only those files) will be
            extracted. After the install, the folder and its contents
            will be deleted automatically.
        """
        from skymodman.interface.dialogs.fomod_installer_wizard import \
            FomodInstaller

        # split the installer into a separate thread.
        wizard = FomodInstaller(self.installer, tmpdir)
        wizard.show()
        with quamash.QThreadExecutor(1) as ex:
            f = asyncio.get_event_loop(
            ).run_in_executor(ex, wizard.exec_)
            await f

        # so long as they didn't hit cancel, extract the files
        if wizard.result() == wizard.Accepted:
            # total num of files to install
            self.numfiles = await self.installer.num_fomod_files_to_install()

            # init progress dialog
            self._create_progress_dialog()
            self._extract_with_progress(
                self.installer.install_fomod_files())

            # await self.installer.install_fomod_files()
            # self.modAdded.emit(self.installer.install_destination.name)

        del FomodInstaller

    ##=============================================
    ## Extraction loop
    ##=============================================

    def _extract_with_progress(self, install_gen):
        """
        Generic method that creates and schedules the task which will
        do the actual installation

        :param install_gen: async generator/iterable which, when iterated
            over, will run the extraction process. Should be the
            actual generator object (already called, along with
            arguments, but not yet iterated)
        """

        loop = asyncio.get_event_loop()

        async def do_extraction():
            try:
                count = 0

                async for fpath in install_gen:
                    loop.call_soon_threadsafe(self._update_dialog,
                                              count, fpath)
                    count += 1

            except asyncio.CancelledError:
                self.LOGGER.warning("Extraction cancelled")
                self.pdialog.close()

                raise

        def on_finish(task):
            # finishes the dialog, whether something went wrong or not
            loop.call_soon_threadsafe(self.pdialog.setValue,
                                      self.pdialog.maximum())

            if task.cancelled():
                # clean up partially extracted files
                self.LOGGER.warning("Removing extracted files")
                self.installer.abort_install()

            elif task.exception():
                self.LOGGER.error(
                    "Exception raised by install task")
                self.LOGGER.error(repr(task.exception()))
                self.LOGGER.exception(task.exception())
            else:
                self.LOGGER.info("Installation completed")
                self.modAdded.emit(
                    self.installer.install_destination.name)

        itask = loop.create_task(do_extraction())

        self.pdialog.canceled.connect(itask.cancel)

        # catch the finished task
        itask.add_done_callback(on_finish)



            # async def extraction_progress_dialog(self, start_dir=None):
    #     """
    #     Have the install manager extract the contents of its archive
    #     to the default installation location. Create a progress dialog
    #     that will show if the process is estimated to take more than
    #     ~4 seconds.
    #
    #     :param start_dir: If the items to be extracted are not under the
    #         root of the archive but rather in a subfolder, pass the
    #         path to that folder as `start_dir`
    #
    #     :return:
    #     """
    #     self.LOGGER << "Performing auto-install"
    #
    #     # TODO: show notification when extraction is finished
    #
    #     if not start_dir:
    #         num_to_extract = await self.installer.get_archive_file_count()
    #     else:
    #         num_to_extract = await self.installer.count_folder_contents(start_dir)
    #
    #     dlg = QProgressDialog("Extracting Files...", "Cancel",
    #                           0, num_to_extract)
    #     dlg.setWindowModality(Qt.WindowModal)
    #
    #     task = asyncio.get_event_loop().create_task(
    #         self._do_archive_install(dlg, start_dir))
    #
    #     dlg.canceled.connect(task.cancel)
    #
    #     # catch the finished task
    #     task.add_done_callback(self._install_finished)



    # def _install_finished(self, task):
    #     """
    #
    #     :param asyncio.Task task:
    #     :return:
    #     """
    #
    #     if task.cancelled():
    #         self.LOGGER.warning("Install task was cancelled")
    #     elif task.exception():
    #         self.LOGGER.error("Exception raised by install task")
    #         self.LOGGER.exception(task.exception())
    #     else:
    #         self.LOGGER.info("Installation completed")
    #         self.modAdded.emit(self.installer.install_destination.name)


    # async def _do_archive_install(self, progress_dlg, start_dir=None):
    #     try:
    #         await self.installer.install_archive(start_dir,
    #             lambda f, c: progress_dlg.setValue(c))
    #
    #     except asyncio.CancelledError:
    #         self.LOGGER.warning("Extraction task cancelled")
    #         progress_dlg.setLabelText("Cleaning up...")
    #         # this hides & deletes the cancel button
    #         progress_dlg.setCancelButtonText("")
    #         progress_dlg.setMaximum(self.installer.num_files_installed_so_far)
    #         progress_dlg.setValue(0)
    #         await self.installer.rewind_install(
    #             lambda f, c: progress_dlg.setValue(c))
    #
    #     # Or we could make sure that value == maximum at end...
    #     progress_dlg.reset()

