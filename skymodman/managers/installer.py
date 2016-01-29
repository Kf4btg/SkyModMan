from functools import partialmethod
from contextlib import ContextDecorator
# import traceback
import shutil
import os
import sys

import libarchive
from libarchive import file_reader, ArchiveError
from libarchive.extract import extract_entries


# import patoolib
from skymodman.utils import withlogger #, checkPath, printattrs

@withlogger
class _catchArchiveError(ContextDecorator):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def __enter__(self):
        return self



    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is ArchiveError:
            self.logger.error("Error reading archive: {}".format(exc_val))

            # print(traceback.format_tb(exc_tb))
            # traceback.print_tb(exc_tb)
            # printattrs(exc_tb, "traceback")
            # printattrs(exc_tb.tb_frame)
            # return True

        return False




class ArchiveHandler:

    def __init__(self, archive_type):
        self._type = archive_type
        self._commands = {
            "list":    lambda:None,
            "extract": lambda:None,
            "create":  lambda:None
        }
        self._options = {
            "list":    None,
            "extract": None,
            "create":  None
        }

    @property
    def type(self):
        return self._type

    @property
    def list(self):
        return self._commands["list"]

    @property
    def extract(self):
        return self._commands["extract"]

    @property
    def create(self):
        return self._commands["create"]

    def set_command(self, cmd_name, command=None, options=None):
        self._commands[cmd_name] = command
        self._options[cmd_name] = options

    set_list_command    = partialmethod(set_command, "list")
    set_extract_command = partialmethod(set_command, "extract")
    set_create_command  = partialmethod(set_command, "create")



@withlogger
class InstallManager:
    """
    Handles unpacking of mod archives and moving mod files and directories into the appropriate locations.
    """

    FORMATS = ["zip", "rar", "7z"]

    def __init__(self, manager):
        self.manager = manager


    @_catchArchiveError
    def list_archive(self, archive, include_dirs=True):
        """

        :param str archive: path to an archive
        :rtype: __generator[libarchive.ArchiveEntry, Any, None]
        """
        with file_reader(archive) as arc:
            yield from (entry for entry in arc if include_dirs or entry.isfile)

    def extract_archive(self, archive, dest_dir, entries=None):
        """
        Extract all or a subset of the contents of `archive` to the destination directory

        :param archive: path to the archive file
        :param dest_dir: The directory into which the files will be extracted. Must already exist.
        :param entries: If given, must be a list of strings or ArchiveEntries corresponding to the specific items within the archive to be extracted.  If not specified or None, all entries will be extracted.
        :return:
        """

        # could raise exception?
        os.chdir(dest_dir)

        if entries:
            if isinstance(entries[0],str):
                with file_reader(archive) as arc:
                    entries = [e for e in arc if e.name in entries]
            #else:
                # assume it's already a list of ArchiveEntries
            extract_entries(entries)
        else:
            libarchive.extract_file(archive)








if __name__ == '__main__':
    from skymodman import skylog

    im = InstallManager(None)

    # x=im.list_archive('res/test.rar')

    fr = libarchive.file_reader
    from pprint import pprint

    # for file in ['res/ziptest.zip',
    #              'res/7ztest.7z',
    #              'res/rartest.rar',
    #              'res/bad7ztest.rar']:
    for file in ['res/ziptest.zip',
                'res/notazip.zip']:

        print(file)
        with _catchArchiveError():
            with fr(file) as aarc:
                # print(type(arc))
                for entry in aarc: # type: libarchive.ArchiveEntry
                    print(entry)
                    print('\t',entry.filetype)
                    # for a in dir(entry):

                        # print(a,getattr(entry,a),sep=": ")
                    # pprint(dir(entry))
                    # print(type(entry))
                    # print(entry)
            print()

    skylog.stop_listener()