import os
import shutil
import subprocess
import sys
from collections import OrderedDict
from pathlib import Path
import asyncio

import libarchive
from libarchive import file_reader, ArchiveError, ffi
from libarchive.extract import new_archive_write_disk
from ctypes import byref, c_longlong, c_size_t, c_void_p

from skymodman.exceptions import ArchiverError
from skymodman.utils import withlogger, change_dir #, printattrs #, checkPath


@withlogger
class ArchiveHandler:
    FORMATS = ["zip", "rar", "7z"]
    PROGRAMS = ["unrar", "unar", "7z"]
    TEMPLATES = {
        "unrar": "unrar x {input} {includes} {dest}",
        "unar":  "unar -o {dest} {input} {includes}",
        "7z":    "7z x -o{dest} {includes} {input}",
    }
    INCLUDE_FILTERS = {
        "unrar": lambda paths: "-n" + " -n".join(paths),
        "7z":    lambda paths: "-i!" + " -i!".join(paths),
        "unar":  lambda paths: " ".join(
            p + '*' if p.endswith('/')
            else p
            for p in paths),
    }
    """A mapping  from the command name to a callable crafted to return the unique include-file syntax for each of the different commands"""

    def __init__(self, *args, **kwargs):
        # noinspection PyArgumentList
        super().__init__(*args, **kwargs)

        self._7zrar = False
        self._programs = self.detect_programs()

        if '7z' in self._programs:
            self._7zrar = self._7z_supports_rar()

    def detect_programs(self):
        """
        Find out which programs are available for use on the user's computer for unpacking archives (mainly rar; libarchive can handle everything else; it can actually handle some rars, too, but not all)
        :return: list of installed and usable programs
        """

        programs=OrderedDict()
        # let user specify an unrar program via
        # the SMM_UNRAR env variable. This should be a string
        # that describes a valid cli-command; the placeholders
        # "{input}" and "{dest}" can be used for the archive to
        # be unpacked and the destination folder, if needed. If the
        # command unpacks archives to the current directory by default,
        # then the {dest} placeholder does not need to be used.
        user_def=os.getenv('SMM_UNRAR')

        if user_def and shutil.which(user_def):
            programs['user'] = user_def

        for prog in ['unrar', 'unar', '7z']:
            if shutil.which(prog):
                programs[prog]=self.TEMPLATES[prog]

        return programs

    def _7z_supports_rar(self):
        """
        if unrar or unar were not found, but 7zip was,
        we'll need to find out if the installed 7z supports
        rar files. And apparently not all versions of 7z have
        the "7z i" command...so we have to do it the hard way.

        :return: True if the Rar codec lib
        """
        import re
        codec_dir = 'p7zip/Codecs'
        codec_name = re.compile(r'Rar[0-9]*\.so')

        # search in all the possible lib dirs i can think of...
        for dlib in (
        '/usr/lib', '/usr/local/lib', '/usr/lib64', '/usr/local/lib64',
        '/usr/lib/i386-linux-gnu', '/usr/lib/x86_64-linux-gnu'):

            codec_path = os.path.join(dlib, codec_dir)
            if os.path.exists(codec_path) and any(
                    codec_name.match(c)
                    for c in os.listdir(codec_path)):
                return True
        return False

    def list_archive(self, archive, *, dirs=True, files=True):
        """

        :param str archive: path to an archive
        :param dirs: include directories in the output
        :param files: include files in the output
        :return: generator over the internal paths of all files in the archive; directories, if included, will end in a final '/'
        :rtype: __generator[str, Any, None]
        """
        with file_reader(archive) as arc:
            yield from (entry.path + "/" # add a final / to paths to differentiate
                        if entry.isdir else entry.path
                        for entry in arc
                        if (dirs and files)
                        or (dirs and entry.isdir)
                        or (files and entry.isfile))


    async def extract_archive(self, archive, dest_dir, entries=None, progress_callback=None):
        """
        Extract all or a subset of the contents of `archive` to the destination directory

        :param archive: path to the archive file
        :param dest_dir: The directory into which the files will be extracted. Must already exist.
        :param entries: If given, must be a list of strings to the paths of the specific items within the archive to be extracted.  If not specified or None, all entries will be extracted.
        :param progress_callback: if provided, will be called periodically during the excecution of the extraction process to report the percentage progress.
        :return: Tuple of (bool, list[ArchiveError]); the first item  is whether the archive was sucessfully unpacked, while the second is the list of errors encountered, if any, during the operations.
        """

        if isinstance(archive, str):
            apath = Path(archive).absolute()
        else:
            assert isinstance(archive, Path)
            apath = archive.absolute()

        assert apath.exists()

        errors = []
        success = True

        if apath.suffix == 'rar':
            success, errors = await self._unpack_rar(str(archive), str(dest_dir), entries, progress_callback)

        else:
            try:
                await self._libarchive_extract(str(archive), str(dest_dir), entries, progress_callback)
            except ArchiveError as e:
                success = False
                errors.append(e)

        return success, errors

    async def _unpack_rar(self, archive, dest_dir, entries=None, callback=None):
        """
        While most archives can be handled just fine using libarchive,
        Rar archives can sometimes partially fail to unpack. For that
        reason, if we've been given a rar to unpack, we first try
        several other programs (if installed) to extract it, falling
        back to libarchive as a last resort.

        :param str archive:
        :param str dest_dir:
        :param list[str] entries:
        :return: Tuple of (bool, list[ArchiveError]); the first item  is whether any command was able to sucessfully unpack the archive, while the second is the list of errors encountered, if any, during the various attempts.
        """

        errors = []
        success=True

        # first, try our other programs
        for cmdname, cmd in self._programs.items():
            if cmdname == '7z' and not self._7zrar: continue

            if entries:
                fullcmd = cmd.format(input=archive, dest=dest_dir,includes=self.INCLUDE_FILTERS[cmdname](entries))
            else:
                fullcmd = cmd.format(input=archive, dest=dest_dir, includes="")

            try:
                self.run_external(fullcmd)
                break # on success
            except ArchiveError as e:
                errors.append(e)
        else:
            # no command succeeded; try libarchive
            try:
                self._libarchive_extract(archive, dest_dir, entries)
            except ArchiveError as e:
                errors.append(e)
            success = False

        return success, errors

    async def _libarchive_extract(self, archive, dest_dir, entries=None, callback=None):
        """
        Extract the archive using the libarchive library. This should work fine for most archives, but should only be used as a last resort for 'rar' archives.

        :param archive:
        :param dest_dir:
        :param entries:
        """

        errmsg = None
        # could raise exception?
        with change_dir(dest_dir):
            try:
                if entries:
                    with file_reader(archive) as arc:
                        await self._extract_matching_entries(arc, entries, callback)
                else:
                    libarchive.extract_file(archive)
            except libarchive.ArchiveError as lae:
                errmsg = "Libarchive experienced an error attempting to unpack '{}': {}".format(archive, lae)
                self.logger.error(errmsg)

        if errmsg:
            raise ArchiveError(errmsg)

    async def _extract_matching_entries(self, archive, entries, flags=0,
                                        callback=None, *,
                                  write_header=ffi.write_header,
                                  read_data_block=ffi.read_data_block,
                                  write_data_block=ffi.write_data_block,
                                  write_finish_entry=ffi.write_finish_entry,
                                  ARCHIVE_EOF=ffi.ARCHIVE_EOF):
        """
        Trying to directly use the context managers provided by libarchive led to the archive pointer being freed before we passed the list of entries to the extract_entries method. Thus, this is a reimplementation of extract_entries that internally checks the path names for a match.
        :param archive: the archive pointer
        :param list[str] entries: list of paths inside the archive that should be extracted.
        :param flags:

        The other params are internal details of libarchive and should not be altered.

        :param write_header:
        :param read_data_block:
        :param write_data_block:
        :param write_finish_entry:
        :param ARCHIVE_EOF:
        """
        buff, size, offset = c_void_p(), c_size_t(), c_longlong()

        buff_p, size_p, offset_p = byref(buff), byref(size), byref(offset)

        with new_archive_write_disk(flags) as write_p:
            for entry in archive:
                # using the check below will make sure we get all child
                # entries for any folder listed in `entries`
                if any(entry.name.startswith(e) for e in entries):
                    write_header(write_p, entry._entry_p)
                    read_p = entry._archive_p
                    while 1:
                        r = read_data_block(read_p, buff_p,
                                            size_p, offset_p)
                        if r == ARCHIVE_EOF: break

                        write_data_block(write_p, buff,
                                         size, offset)
                    write_finish_entry(write_p)

    def run_external(self, command, *, stdout=None,
                     stderr=subprocess.PIPE, timeout=120):
        """

        :param str command:
        :param timeout:
        :return:
        """

        try:
            subprocess.run(command.split(), check=True,
                           stdout=stdout,
                           stderr=stderr,
                           timeout=timeout)
        except subprocess.CalledProcessError as cpe:
            errmsg = "External command `{err.cmd}` failed with exit code {err.returncode}: {err.stderr}".format(cpe)
            self.logger.error(errmsg)

            raise ArchiverError(errmsg).with_traceback(
                sys.exc_info()[2])
        except subprocess.TimeoutExpired as toe:
            errmsg = "External command `{err.cmd}` failed to respond after {err.timeout} seconds: {err.stderr}".format(
                toe)
            self.logger.error(errmsg)
            raise ArchiverError(errmsg).with_traceback(
                sys.exc_info()[2])
