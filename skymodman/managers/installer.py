import os

from skymodman.utils import withlogger
from skymodman.managers.archive import ArchiveHandler


@withlogger
class InstallManager:
    """
    Handles unpacking of mod archives and moving mod files and directories into the appropriate locations.
    """

    # noinspection PyArgumentList
    def __init__(self, manager, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.manager = manager
        self.archiver = ArchiveHandler()

    def is_fomod(self, archive):
        for e in self.list_archive(archive, files=False):
            if os.path.basename(e).lower() == "fomod":
                return e

        return None

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