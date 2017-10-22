import asyncio
import os
import re
import signal
from pathlib import Path

from skymodman.exceptions import ArchiverError, ExternalProcessError
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
    Uses a system-installed 7-zip (via subprocess) to handle extraction
    of archives. Allow partial extraction, and listing and inspection
    without extraction.
    """

    INCLUDE_FILTER = lambda paths: ["-i!"+p.rstrip('/') for p in paths]

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
                    f"7z-list process returned a non-zero exit code: {retcode}")
            else:
                ArchiveHandler._list_archive_cache[archive] = (dirs, files)

        # self.LOGGER << "Cache hits: {0._cache_hits},
        # misses: {0._cache_misses}".format(ArchiveHandler)
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

        # as each line comes in
        async for line in proc.stdout:

            if line.find(b'D...') > -1: # directory

                # file name always starts at 54th character
                dirs_buffer.extend(line[53:])

            elif line.find(b'...A') > -1: # file
                files_buffer.extend(line[53:])

        # finish communication
        await proc.wait()

        return_code = proc.returncode
        if not return_code: # == 0
            # decode bytes results to str and parse into a list

            if files_buffer:
                files = list(
                    bytes(files_buffer).decode().splitlines())
            else:
                files=[]

            # add / to end of directories to differentiate them
            if dirs_buffer:
                dirs = [d + "/" for d in
                        bytes(dirs_buffer).decode().splitlines()]
            else:
                dirs=[]

        else:
            self.LOGGER << "non-zero return code"
            files = dirs = []

        return return_code, dirs, files

    async def extract(self, archive, destination, specific_entries=None):
        """

        :param archive:
        :param str destination:
        :param specific_entries:
        """

        dpath = Path(destination)

        if not dpath.is_absolute():
            raise ArchiverError(f"Destination path '{destination}' is not an absolute path.")

        if not dpath.exists():
            dpath.mkdir(parents=True, exist_ok=True)

        # retcode = \
        # c = count(start=1)
        async for f in self._extract_files(
                archive=archive,
                dest=str(dpath),
                entries=specific_entries): yield f


    async def _extract_files(self, archive, dest, entries):
        """
        Creates and executes the 7zip command that will extract the
        specified entries from the archive.
        """
        # self.LOGGER << "begin _extract_files"

        if entries:
            includes = type(self).INCLUDE_FILTER(entries)
        else:
            includes = [""]


        # opts=("-bd",    # disable progress indic (uses readline)
        #       "-bb1",   # output verbosity 1 (show files as extracted)
        #       "-ssc-",  # case-INsensitive mode
        #       "-y",     # assume yes to queries
        #       )
        create = asyncio.create_subprocess_exec(
            "7z", "x", *_7zopts, f"-o{dest}", *includes, archive,
            preexec_fn=os.setpgrp, # allows cancellation
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL
        )

        proc = await create
        try:
            async for line in proc.stdout:

                # I tried...but it seems to be impossible to get
                # 7z to produce line-buffered output when connected
                # to a pipe.  It insists on spitting it out in chunks.
                # might be able to implement some sort of
                # parallelization to speed things up, but it's
                # probably not worth the effort

                # This might be a good point to put a reminder that
                # the reason we're using the command line version
                # of 7zip in the first place is because there
                # are VERY few archive utilities that support
                # extraction of all the common mod-archive types
                # in a single package. And there are no python
                # bindings for 7z (or anything else) that support
                # everything the cli version does. Also, its free
                # and fairly ubiquitous, so shouldn't be much
                # of an obstacle to use of this program

                # 7z logs filepaths on lines starting w/ '- '
                if line.startswith(b'- '):
                    yield line[2:].decode().rstrip()

        except asyncio.CancelledError:
            self.LOGGER.warning("Task cancelled, killing process")

            # since 7z apparently spawns a child process, we have
            # to kill the entire process group or the child (which
            # does all the actual work) will keep running
            os.killpg(proc.pid, signal.SIGTERM)

        await proc.wait()

        if proc.returncode < 0: # killed w/ signal (cancelled)
            raise asyncio.CancelledError
        elif proc.returncode > 0:
            raise ExternalProcessError(proc.returncode)
