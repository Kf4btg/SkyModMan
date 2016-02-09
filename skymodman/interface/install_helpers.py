import asyncio
from tempfile import TemporaryDirectory

import quamash

from skymodman.managers import modmanager as Manager
# from skymodman.interface.widgets import FomodInstaller, message
from skymodman.interface.widgets import message, ManualInstallDialog



class InstallerUI:

    def __init__(self):
        self.tmpdir = None


    async def do_install(self, archive, ready_callback):
        print("doinstall")

        with TemporaryDirectory() as tmpdir:
            # await asyncio.sleep(5)
            installer = await Manager.extract_fomod(archive, tmpdir)

            ready_callback()

            if installer is not None:
                print("awaiting installer")
                await self.run_fomod_installer(installer, tmpdir)


            else:
                print("not fomod")
                structure = await Manager.install_archive()
                # todo: if there's an issue with the mod structure, show manual-install dialog and ask the user to restructure the archive.
                # also todo: go ahead and install the mod if the structure is fine


                message("information", title="Mod Structure",
                        text=str(structure))
                # text="\n".join(structure))
                # extract_location =  # should extract the archive
                # if extract_location is None:
                #     extract_location="The mod structure is incorrect"

                # message("information", text=extract_location)


    async def run_fomod_installer(self, installer, tmpdir):
        from skymodman.interface.widgets import FomodInstaller

        # split the installer into a separate thread.
        with quamash.QThreadExecutor(1) as ex:
            print("about to create wizard")
            wizard = FomodInstaller(installer, tmpdir)
            print("about to run in exec")
            wizard.show()
            f = asyncio.get_event_loop().run_in_executor(ex, wizard.exec_)
            print("awaiting future")
            await f

        del FomodInstaller



    async def do_manual_install(self, archive, ready_callback):
        mod_contents = await Manager.prepare_manual_install(archive)

        ready_callback()

        with quamash.QThreadExecutor(1) as ex:
            print("about to create wizard")
            mi_dialog = ManualInstallDialog(mod_contents)
            print("about to run in exec")
            mi_dialog.show()
            f = asyncio.get_event_loop().run_in_executor(ex,
                                                         mi_dialog.exec_)
            print("awaiting future")
            await f







