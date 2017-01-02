import asyncio
import os
import re
from itertools import count
from pathlib import Path

from skymodman.exceptions import ArchiverError
from skymodman.types import diqt
from skymodman.log import withlogger

_7zopts=("-bd",    # disable progress indic (uses readline, won't really work here...)
          "-bb1",  # output verbosity 1 (show files as extracted)
          "-ssc-", # case-INsensitive mode
          "-y",    # assume yes to queries
          )

@withlogger
class ArchiveHandler:
    """
    A reimplementation of the archive handler that leans heavily on 7zip
    """

    FORMATS = ["zip", "rar", "7z"]
    PROGRAM = "7z"

    # read the 7z manual to figure out what all these switches mean
    TEMPLATES = {
        "extract", "{prog} x -o{dest} {includes} {archive}",
        "list", "{prog} l {archive}",
    }

    INCLUDE_FILTER = lambda paths: ["-i!"+p.rstrip('/') for p in paths]

    # def __init__(self, *args, **kwargs):
    #     super().__init__(*args, **kwargs)
    def __init__(self):
        self._7z_supports_rar = self._7z_rar_support()

    def _7z_rar_support(self):
        """
        Determine if the installed 7z supports
        rar files. Apparently not all versions of 7z have
        the "7z i" command...so we have to do it the hard way.

        :return: True if the Rar codec lib exists
        """
        codec_dir = 'p7zip/Codecs'
        codec_name = re.compile(r'Rar[0-9]*\.so')

        # search in all the possible lib dirs i can think of...
        for dlib in (
                '/usr/lib', '/usr/local/lib', '/usr/lib64',
                '/usr/local/lib64',
                '/usr/lib/i386-linux-gnu', '/usr/lib/x86_64-linux-gnu'):

            codec_path = os.path.join(dlib, codec_dir)
            if os.path.exists(codec_path) and any(
                    codec_name.match(c)
                    for c in os.listdir(codec_path)):
                # self.LOGGER << "System 7z has rar support"
                return True

        self.LOGGER << "System 7z does not have rar support"
        return False

    _list_archive_cache=diqt(maxlen_=8)
    # _cache_hits=0
    # _cache_misses=0
    async def list_archive(self, archive):
        """

        Returns a 2-tuple where the first item is a list of all the
        directories in the `archive`, the second a list of all the files
        """

        try:
            dirs, files = ArchiveHandler._list_archive_cache[archive]
            # ArchiveHandler._cache_hits+=1
        except KeyError:
            # ArchiveHandler._cache_misses+=1

            retcode, dirs, files = await self._archive_contents(archive)

            if retcode:
                raise ArchiverError(
                    "7z-list process returned a non-zero exit code: {}".format(
                        retcode))
            else:
                ArchiveHandler._list_archive_cache[archive] = (dirs, files)

        # self.LOGGER << "Cache hits: {0._cache_hits}, misses: {0._cache_misses}".format(ArchiveHandler)
        return dirs, files


    async def _archive_contents(self, archive):
        """
        Use the 'list' option of 7z to examine the types of files
        held within the archive without actually extracting them all
        """
        # self.LOGGER << "BEGIN _archive_contents"
        files_buffer = bytearray()
        dirs_buffer = bytearray()

        create = asyncio.create_subprocess_exec(
            "7z", "l", archive,
            stdout=asyncio.subprocess.PIPE)

        proc = await create

        while True:
            # as each line comes in
            line = await proc.stdout.readline()

            # empty byte string returned at EOF
            if not line: break

            if line.find(b'D...') > -1: # directory

                # file name always starts at 54th character
                dirs_buffer.extend(line[53:])

            elif line.find(b'...A') > -1: # file
                files_buffer.extend(line[53:])

        # self.LOGGER << "waiting for subprocess to finish"
        await proc.wait()

        return_code = proc.returncode
        if not return_code: # == 0
            # self.LOGGER << "Return code was 0; parsing results"
            # decode bytes results to str and parse into a list
            files = self._parse_7z_filelisting(
                bytes(files_buffer).decode())

            dirs = self._parse_7z_filelisting(
                # add / to end of directories to differentiate them
                bytes(dirs_buffer).decode(), '/')
        else:
            self.LOGGER << "non-zero return code"
            files = dirs = []

        # self.LOGGER << "returning results"
        return return_code, dirs, files


    def _parse_7z_filelisting(self, output, suffix=''):
        """
        Split the lines returned from the ``7z l`` command into a list
        of filenames. If suffix is a non-empty string, it will be
        appended to the end of each file name.

        :param output:
        :param suffix:
        :return:
        """
        # self.LOGGER << "parsing results"
        if not output:
            return []
        lines = output.splitlines()

        return [l+suffix for l in lines]

    async def extract(self, archive, destination,
                      specific_entries=None,
                      callback=None):
        """

        :param archive:
        :param str destination:
        :param specific_entries:
        :param callback:
        :return:
        """

        dpath = Path(destination)

        if not dpath.is_absolute():
            raise ArchiverError("Destination path '{}' is not an absolute path.".format(destination))

        if not dpath.exists():
            dpath.mkdir(parents=True, exist_ok=True)

        retcode = await self._extract_files(archive=archive,
                                            dest=str(dpath),
                                            entries=specific_entries,
                                            callback=callback)

        if retcode:
            raise ArchiverError(
                "7z-extraction process returned a non-zero exit code: {}".format(
                    retcode))


    async def _extract_files(self, archive, dest, entries, callback):
        """
        Creates and executes the 7zip command that will extract the
        specified entries from the archive.
        """
        # self.LOGGER << "begin _extract_files"
        if not callback:
            def callback(*args): pass

        if entries:
            includes = type(self).INCLUDE_FILTER(entries)
        else:
            includes = [""]

        # opts=("-bd",    # disable progress indic (uses readline, won't really work here...)
        #       "-bb1",   # output verbosity 1 (show files as extracted)
        #       "-ssc-",  # case-INsensitive mode
        #       "-y",     # assume yes to queries
        #       )
        create = asyncio.create_subprocess_exec(
            "7z", "x", *_7zopts, "-o{}".format(dest),
            *includes, archive,
            stdout=asyncio.subprocess.PIPE
        )
        # print("7z", "x", *opts, "-o{}".format(dest),
        #       *includes, archive)

        proc = await create
        c = count(start=1)
        loop = asyncio.get_event_loop()
        while True:
            # simulate long processes
            # await asyncio.sleep(1)

            line = await proc.stdout.readline()
            # print("{!r}".format(line))
            if not line: break

            # 7z logs filepaths on lines starting w/ '- '
            if line.startswith(b'- '):
                loop.call_soon_threadsafe(callback, line[2:].decode(), next(c))

        await proc.wait()

        return proc.returncode
