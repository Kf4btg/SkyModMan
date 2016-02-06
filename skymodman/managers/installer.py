import os
from tempfile import TemporaryDirectory
from functools import lru_cache
import asyncio

from skymodman.utils import withlogger
from skymodman.managers.archive import ArchiveHandler
from skymodman.installer.fomod import Fomod
from skymodman.installer import common
# from skymodman.managers import modmanager as Manager

from pprint import pprint


class installState:
    def __init__(self):
        self.file_path = None
        self.install_dest = None
        self.files_to_install = []

        self.flags = {}


    # fake manager for testing
class FakeManager:
    class conf:
        class paths:
            dir_mods="res"

    @staticmethod
    def checkFileState(file, state):
        if state == common.FileState.A:
            return True

        return False

Manager = FakeManager

@withlogger
class InstallManager:
    """
    Handles unpacking of mod archives and moving mod files and directories into the appropriate locations.
    """

    # noinspection PyArgumentList
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.archiver = ArchiveHandler()

        self.current_fomod = None

        self.install_state = installState()

    def is_fomod(self, archive):
        for e in self.iter_archive(archive, files=False):
            if os.path.basename(e).lower() == "fomod":
                return e

        return None

    def extract_fomod(self, archive, fomod_path):
        """
        Extracts fomod install script to a temporary directory

        :param archive:
        :param fomod_path: The internal path to the 'fomod' directory within the archive (as returned by is_fomod)
        :return: Path to the extracted install script
        """
        with TemporaryDirectory() as tmpdir:
            self.extract(archive, tmpdir, entries=[fomod_path])

    def extract(self, archive, destination, entries=None):
        """

        :param archive: the archive to unpack
        :param destination: extraction destination
        :param entries: list of archive entries (i.e. directories or files) to extract; if None, all entries will be extracted
        :return:
        """

        self.archiver.extract_archive(archive, destination, entries)

    def iter_archive(self, archive, *, dirs=True, files=True):
        yield from self.archiver.list_archive(archive, dirs=dirs, files=files)

    def archive_contents(self, archive, *, dirs=True, files=True):
        return list(self.archiver.list_archive(archive, dirs=dirs, files=files))


    def prepare_fomod(self, xmlfile):
        self.current_fomod = Fomod(xmlfile)
        self.install_state = installState()

        self.install_state.install_dest = Manager.conf.paths.dir_mods

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
        # print(self.install_state.flags)

    def unset_flag(self, flag):
        try: del self.install_state.flags[flag]
        except KeyError: pass
        # print(self.install_state.flags)


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
        # print("check file", file, state)
        # ret = Manager.checkFileState(file, state)

        # print(ret)
        return Manager.checkFileState(file, state)

    def check_flag(self, flag, value):
        # print(flag, value)
        # print( self.install_state.flags[flag] if flag in self.install_state.flags else "flag {} missing".format(flag))

        ret= flag in self.install_state.flags \
               and self.install_state.flags[flag] == value

        # print(ret)
        return ret

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

    async def copyfiles(self, callback=print):
        flist = self.install_state.files_to_install
        total = len(flist)

        amt_copied=0
        for file in flist:
            await asyncio.sleep(0.05)
            amt_copied+=1
            asyncio.get_event_loop().call_soon_threadsafe(
                "{.2}".format(amt_copied/total))










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




    # fr = libarchive.file_reader

    # for file in ['res/ziptest.zip',
    #              'res/7ztest.7z',
    #              'res/rartest.rar',
    #              'res/bad7ztest.rar']:
    # for file in ['res/ziptest.zip',
    #             'res/notazip.zip']:
    #
    #     print(file)
    #     with _catchArchiveError():
    #         with fr(file) as aarc:
    #             # print(type(arc))
    #             for entry in aarc: # type: libarchive.ArchiveEntry
    #                 print(entry)
    #                 print('\t',entry.filetype)
    #                 # for a in dir(entry):
    #
    #                     # print(a,getattr(entry,a),sep=": ")
    #                 # pprint(dir(entry))
    #                 # print(type(entry))
    #                 # print(entry)
    #         print()

    skylog.stop_listener()