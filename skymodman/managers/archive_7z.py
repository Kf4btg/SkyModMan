import asyncio
import os
import re
# from itertools import count
# from functools import lru_cache
from pathlib import Path

from skymodman.exceptions import ArchiverError
from skymodman.utils import withlogger, diqt


@withlogger
class ArchiveHandler:
    """
    A reimplementation of the archive handler that leans heavily on 7zip
    """

    FORMATS = ["zip", "rar", "7z"]
    PROGRAM = "7z"

    TEMPLATES = {
        "extract", "{prog} x -o{dest} {includes} {archive}",
        "list", "{prog} l {archive}",
    }

    INCLUDE_FILTER = lambda paths: ["-i!"+p.rstrip('/') for p in paths]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._7z_supports_rar = self._7z_rar_support()

    def _7z_rar_support(self):
        """
        Determine if the installed 7z supports
        rar files. Apparently not all versions of 7z have
        the "7z i" command...so we have to do it the hard way.

        :return: True if the Rar codec lib
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
                self.LOGGER << "System 7z has rar support"
                return True
            self.LOGGER << "System 7z does not have rar support"
        return False

    _list_archive_cache=diqt(maxlen_=8)
    _cache_hits=0
    _cache_misses=0
    async def list_archive(self, archive, *, include_dirs=True, include_files=True):
        """
        By default, return a list of all the files and folders in the specified archive. Names will be normalized to lower case.

        If `include_files` or `include_dirs` is False, files or folders will be excluded from the results, respectively. There is no short-circuit if both are False, even though nothing will be returned--just try to avoid calling the function in that case.

        :param str archive:
        :param include_dirs:
        :param include_files:
        :return:
        """

        try:
            results = ArchiveHandler._list_archive_cache[(archive, include_dirs, include_files)]
            ArchiveHandler._cache_hits+=1
        except KeyError:
            ArchiveHandler._cache_misses+=1

            retcode, dirs, files = await self._archive_contents(archive)

            if retcode:
                raise ArchiverError(
                    "7z-list process returned a non-zero exit code: {}".format(
                        retcode))
            else:
                results = []
                if include_dirs:
                    results.extend(dirs)
                if include_files:
                    results.extend(files)

                ArchiveHandler._list_archive_cache[(archive, include_dirs, include_files)] = results

        self.LOGGER << "Cache hits: {0._cache_hits}, misses: {0._cache_misses}".format(ArchiveHandler)
        return results


    async def _archive_contents(self, archive):
        # self.LOGGER << "BEGIN _archive_contents"
        files_buffer = bytearray()
        dirs_buffer = bytearray()

        self.LOGGER << "Creating 7z process"
        create = asyncio.create_subprocess_exec(
            "7z", "l", archive,
            stdout=asyncio.subprocess.PIPE)

        proc = await create

        # wait for process to be created and become ready
        # self.LOGGER << "waiting for process creation"
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

        # wait for subprocess to finish
        # self.LOGGER << "waiting for subprocess to finish"
        await proc.wait()

        return_code = proc.returncode
        if not return_code: # == 0
            self.LOGGER << "Return code was 0; parsing results"
            # decode bytes results to str and parse into a list
            files = self._parse_7z_filelisting(bytes(files_buffer).decode())

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
        Split the lines returned from the ``7z l`` command into a list of filenames; names will be normalized to lowercase. If suffix is a non-empty string, it will be appended to the end of each file name.
        :param output:
        :param suffix:
        :return:
        """
        # self.LOGGER << "parsing results"
        if not output:
            return []
        lines = output.splitlines()

        # normalize to lower case
        return [l.lower()+suffix for l in lines]

    async def extract(self, archive, destination, specific_entries=None, callback=None):

        destination = '/tmp/testinstall'

        if not callback:
            def callback(*args): pass

        dpath = Path(destination)

        if not dpath.is_absolute():
            raise ArchiverError("Destination path '{}' is not an absolute path.".format(destination))

        if not dpath.exists():
            dpath.mkdir(parents=True, exist_ok=True)

        retcode = await self._extract_files(archive, str(dpath),
                                            specific_entries, callback)

        if retcode:
            raise ArchiverError(
                "7z-extraction process returned a non-zero exit code: {}".format(
                    retcode))


    async def _extract_files(self, archive, dest, entries, callback):
        self.LOGGER << "begin _extract_files"
        if entries:
            includes = type(self).INCLUDE_FILTER(entries)
        else:
            includes = [""]

        create = asyncio.create_subprocess_exec(
            "7z", "x", "-o{}".format(dest),
            *includes, archive,
            stdout=asyncio.subprocess.PIPE
        )

        proc = await create

        while True:
            line = await proc.stdout.readline()
            print("read {!r}".format(line))

            if not line: break

        await proc.wait()

        return proc.returncode
