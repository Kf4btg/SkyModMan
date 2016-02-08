import os
from functools import lru_cache
from collections import deque
import asyncio

from skymodman.utils import withlogger
from skymodman.managers.archive import ArchiveHandler
from skymodman.installer.fomod import Fomod
from skymodman.installer import common
from skymodman.managers import modmanager as Manager

# from pprint import pprint


class installState:
    def __init__(self):
        self.file_path = None
        self.install_dest = None
        self.files_to_install = []
        self.files_installed_so_far = deque()

        self.flags = {}


# fake manager for testing
# class FakeManager:
#     class conf:
#         class paths:
#             dir_mods="res"
#
#     @staticmethod
#     def checkFileState(file, state):
#         if state == common.FileState.A:
#             return True
#
#         return False
#
# Manager = FakeManager

@withlogger
class InstallManager:
    """
    Handles unpacking of mod archives and moving mod files and directories into the appropriate locations.
    """

    # noinspection PyArgumentList
    def __init__(self, mod_archive, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.archiver = ArchiveHandler()

        self.archive = mod_archive
        self.current_fomod = None

        self.install_state = installState()

    def get_fomod_path(self):
        for e in self.iter_archive(files=False):
            # drop the last char because it is always '/' for directories
            if os.path.basename(e[:-1]).lower() == "fomod":
                return e

        return None

    async def extract(self, destination, entries=None,
                      srcdestpairs=None, callback=None):
        """

        :param destination: extraction destination
        :param entries: list of archive entries (i.e. directories or files) to extract; if None, all entries will be extracted
        """
        await self.archiver.extract_archive(
            archive=self.archive,
            dest_dir=destination,
            entries=entries,
            srcdestpairs=srcdestpairs,
            progress_callback=callback)

    def iter_archive(self, *, dirs=True, files=True):
        yield from self.archiver.list_archive(self.archive, dirs=dirs, files=files)

    def archive_contents(self, *, dirs=True, files=True):
        return list(self.archiver.list_archive(self.archive, dirs=dirs, files=files))

    def check_mod_structure(self):
        # todo: check that everything which should go in the Skyrim/Data directory is on the top level of the archive
        return True


    async def prepare_fomod(self, xmlfile, extract_dir=None):
        self.current_fomod = Fomod(xmlfile)
        self.install_state = installState()

        # we don't want to extract the entire archive before we start,
        # but we do need to extract any images defined in the
        # config file so that they can be shown during installation
        if self.archive and extract_dir is not None:
            await self.extract(extract_dir,
                               entries=self.current_fomod.all_images)


        if self.current_fomod.reqfiles:
            self.install_state.files_to_install=self.current_fomod.reqfiles

        # pprint(self.install_state.files_to_install)



    dep_checks = {
        "fileDependency": lambda s, d: s.check_file(d.file, d.state),
        "flagDependency": lambda s, d: s.check_flag(d.flag, d.value),
        "gameDependency": lambda s, d: s.check_game_version(d),
        "fommDependency": lambda s, d: s.check_fomm_version(d),
    }

    def set_flag(self, flag, value):
        self.install_state.flags[flag]=value

    def unset_flag(self, flag):
        try: del self.install_state.flags[flag]
        except KeyError: pass


    def mark_file_for_install(self, file, install=True):
        """
        :param common.File file:
        :return:
        """
        if install:
            self.install_state.files_to_install.append(file)
        else:
            self.install_state.files_to_install.remove(file)
        # pprint(self.install_state.files_to_install)


    def check_dependencies_pattern(self, dependencies):
        """

        :param common.Dependencies dependencies:
        :return:
        """
        # print(self.check_file.cache_info())

        if dependencies.operator == common.Operator.OR:
            for dtype, dep in dependencies:
                if self.dep_checks[dtype](self, dep):
                    return True
            return False

        else:  # assume AND (the default)
            for dtype, dep in dependencies:
                if not self.dep_checks[dtype](self, dep):
                    return False
        return True

    @lru_cache(256)
    def check_file(self, file, state):
        return Manager.checkFileState(file, state)

    def check_flag(self, flag, value):
        return flag in self.install_state.flags \
               and self.install_state.flags[flag] == value


    def check_game_version(self, version):
        return True

    def check_fomm_version(self, version):
        return True

    def check_conditional_installs(self):
        """
        Called after all the install steps have run.
        """
        flist = self.install_state.files_to_install
        if self.current_fomod.condinstalls:
            for pattern in self.current_fomod.condinstalls:
                if self.check_dependencies_pattern(pattern.dependencies):
                    flist.extend(pattern.files)


        # sort on priority
        flist.sort(key=lambda f: f.priority)
        flist.sort(key=lambda f: f.source.lower())

        # pprint(self.install_state.files_to_install)
        # self.install_state.files_to_install.sort(key=lambda f: f.priority)

    @property
    def install_files(self):
        return self.install_state.files_to_install

    @property
    def num_files_to_install(self):
        return len(self.install_state.files_to_install)

    async def copyfiles(self, dest_dir=None, callback=None):

        if dest_dir is None:
            dest_dir="/tmp/testinstall"


        flist = self.install_state.files_to_install
        progress = self.install_state.files_installed_so_far

        _callback = callback
        if _callback is None:
            def _callback(*args): pass

        def track_progress(filename, num_done):
            progress.append(flist[num_done-1])
            asyncio.get_event_loop().call_soon_threadsafe(
                _callback, filename, num_done)


        await self.extract(destination=dest_dir,
                           srcdestpairs=[(f.source, f.destination)
                                         for f in flist],
                           callback=track_progress)


    async def rewind_install(self, callback=print):
        """
        Called when an install is cancelled during file copy/unpacking.
        Any files that have already been moved to the install directory
        will be removed.

        :param callback:
        :return:
        """
        uninstalls=self.install_state.files_installed_so_far
        remaining=len(uninstalls)

        while remaining>0:
            await asyncio.sleep(0.02)
            f=uninstalls.pop()
            remaining -= 1
            asyncio.get_event_loop().call_soon_threadsafe(
                callback, f.source, remaining)


def __test_extract():
    os.mkdir('res/test-extract')

    im.extract(
        # 'res/ziptest.zip',
        'res/rartest.rar',
        'res/test-extract')

    for r, d, f in os.walk('res/test-extract'):
        print(r, d, f)

def __test_list():
    [print(e) for e in im.archive_contents('res/rartest.rar')]

def __test_fomod():
    assert not im.is_fomod('res/7ztest.7z')
    print(im.is_fomod('res/rartest.rar'))

def __test_exentries():
    from pathlib import Path
    rar = Path('res/rartest.rar').absolute()
    print(rar)
    fpath = im.is_fomod(str(rar))
    print(fpath)

    expath = Path('res/test-extract2').absolute()
    expath.mkdir(exist_ok=True)

    print(expath)

    im.extract(str(rar), str(expath), [fpath])

    for r,d,f in os.walk(str(fpath)):
        print(r,d,f)

    # print(os.listdir('res/test-extract'))


if __name__ == '__main__':
    from skymodman import skylog

    im = InstallManager(None)

    __test_list()
    # __test_extract()
    # __test_fomod()
    # __test_exentries()


    skylog.stop_listener()