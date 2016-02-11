import os
from shlex import quote, split as shsplit
import shutil
import subprocess
import sys
from collections import OrderedDict
from pathlib import Path
import asyncio
import re
from itertools import count

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
        # x=extract; -cl=convert names to lowercase; -inul=disable msgs
        "unrar": "unrar x -cl {input} {includes} {dest}",
        "unar":  "unar -o {dest} {input} {includes}",
        "7z":    "7z x -o{dest} {includes} {input}",
    }
    INCLUDE_FILTERS = {
        # "unrar": lambda paths: "-n" + " -n".join(
        #     quote(p.rstrip('/')).lower() for p in paths),
            # p.rstrip('/').lower() for p in paths),
        "unrar": lambda paths: ["-n"+p.rstrip('/').lower() for p in paths],

        "7z":    lambda paths: "-i!" + " -i!".join(quote(p) for p in paths),
        "unar":  lambda paths: " ".join(
            quote(p) + '*' if p.endswith('/')
            else quote(p)
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
                self.LOGGER << "Detected {}: True".format(prog)
                programs[prog]=self.TEMPLATES[prog]
            else:
                self.LOGGER << "Detected {}: False".format(prog)

        return programs

    def _7z_supports_rar(self):
        """
        if unrar or unar were not found, but 7zip was,
        we'll need to find out if the installed 7z supports
        rar files. And apparently not all versions of 7z have
        the "7z i" command...so we have to do it the hard way.

        :return: True if the Rar codec lib
        """
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
                self.LOGGER << "System 7z has rar support"
                return True
            self.LOGGER << "System 7z does not have rar support"
        return False

    @staticmethod
    def list_archive(archive, *, dirs=True, files=True, depth=-1):
        """

        :param str archive: path to an archive
        :param dirs: include directories in the output
        :param files: include files in the output
        :param depth: if >= 0, only yield items whose directory level is below `depth`. Use depth=1 for top level items; depth=2 for top level and immediate children; etc. If depth is negative, results will not be limited by level.

        :return: generator over the internal paths of all files in the archive; directories, if included, will end in a final '/'
        :rtype: __generator[str, Any, None]
        """

        # israr = os.path.splitext(archive)[-1].lower()==".rar"
        from skymodman.utils import printattrs
        fpreint=True
        with file_reader(archive) as arc:
            for entry in arc: #type: libarchive.ArchiveEntry
                # printattrs(entry, entry.path, False, False)
                # RARS don't end dirs in '/';
                # the other archive types do...

                # if -1 < depth <= entry.path.rstrip('/').count('/'):
                #     continue # skip any files in lower directories
                # if entry.isfile and entry.size <=0:
                #     print(entry, entry.filetype, entry.mode, entry.mtime )
                # if entry.size == 0:
                if entry.path == 'Night-Comparison-Images':
                    # print([b for b in entry.get_blocks()])

                    printattrs(entry, entry.path, False, False)

                if files and entry.isfile:
                    if fpreint:
                        # print([b for b in entry.get_blocks()])
                        printattrs(entry, entry.path, False, False)
                        fpreint=False
                    # found a folder that was showing up as a file with a size of 0...but of course not all 0-size files are actually dirs...
                    yield entry.path
                elif dirs and entry.isdir:
                        # this is silly...stupid rars
                    if entry.path.endswith('/'):
                        yield entry.path
                    else: yield entry.path + '/'

                # elif dirs and entry.isdir:
                #     # this is silly...stupid rars
                #     if entry.path.endswith('/'):
                #         yield entry.path
                #     else:
                #         yield entry.path + '/'


    @staticmethod
    def count_entries(archive, include_dirs=True):
        """
        Return the number of files within the archive. If `include_dirs` is True, count directories separately.
        :param archive:
        :param include_dirs:
        :return:
        """
        counter=count(start=-1)
        lister = ArchiveHandler.list_archive(archive, dirs=include_dirs)

        ### To handle the issue with the folders being reported as 0-size
        # files, ... I guess we can do this:

        while True:
            try:
                next(lister)
                next(counter)
            except StopIteration:
                # break
                return next(counter)



        # with file_reader(archive) as arc:
        #     if include_dirs:
        #         for _ in arc: next(counter)
        #     else:
        #         for e in arc:
        #             if e.isfile: next(counter)
        # return next(counter)

    async def extract_archive(self, archive, dest_dir,
                              entries=None,
                              srcdestpairs=None,
                              progress_callback=None):
        """
        Extract all or a subset of the contents of `archive` to the destination directory

        :param archive: path to the archive file
        :param dest_dir: The directory into which the files will be extracted.
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

        dest_dir = Path(dest_dir)
        if not dest_dir.is_absolute():
            raise ArchiverError("Destination directory '{}' is not an absolute path.".format(dest_dir))

        dest_dir.mkdir(parents=True, exist_ok=True)
        self.LOGGER << "created destination folder at {}".format(dest_dir)

        errors = []
        success = True

        if apath.suffix == '.rar':
            self.LOGGER << "rar detected"
            success, errors = await self._unpack_rar(
               archive=str(archive), dest_dir=str(dest_dir),
                entries=entries, srcdestpairs=srcdestpairs,
                callback=progress_callback)

        else:
            self.LOGGER << "not a rar"
            try:
                await self._libarchive_extract(str(archive), str(dest_dir), entries, srcdestpairs, progress_callback)
            except ArchiveError as e:
                self.logger.error(e)
                success = False
                errors.append(e)

        return success, errors

    async def _unpack_rar(self, archive, dest_dir,
                          entries=None,
                          srcdestpairs=None,
                          callback=None):
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

            self.LOGGER << "attempting {}".format(cmdname)

            if cmdname == '7z' and not self._7zrar:
                self.LOGGER << "Skipping 7z due to lack of rar support"
                continue

            try:
                await self.extern_cmd(program=cmdname,
                                      cmd_template=cmd,
                                      archive=archive,
                                      dest=dest_dir,
                                      entries=entries,
                                      srcdestpairs=srcdestpairs,
                                      callback=callback)

                    # fullcmd = cmd.format(input=quote(archive), dest=quote(dest_dir),includes=self.INCLUDE_FILTERS[cmdname](entries))
                # else:

                # fullcmd = cmd.format(input=quote(archive), dest=quote(dest_dir), includes="")

            # print(fullcmd)
                # self.run_external(fullcmd)
                break # on success
            except ArchiveError as e:
                self.logger << e
                errors.append(e)
        else:
            # no command succeeded; try libarchive
            try:
                await self._libarchive_extract(archive=archive,
                                               dest_dir=dest_dir,
                                               entries=entries,
                                               srcdestpairs=srcdestpairs,
                                               callback=callback)
            except ArchiveError as e:
                errors.append(e)
            success = False

        return success, errors

    async def _libarchive_extract(self, archive, dest_dir,
                                  entries=None,
                                  srcdestpairs=None,
                                  callback=None):
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
                    await asyncio.get_event_loop().run_in_executor(None, libarchive.extract_file, archive)
                    # libarchive.extract_file(archive)
            except libarchive.ArchiveError as lae:
                errmsg = "Libarchive experienced an error attempting to unpack '{}': {}".format(archive, lae)
                self.logger.error(errmsg)

        if errmsg:
            raise ArchiveError(errmsg)

    async def _extract_matching_entries(self, archive, entries,
                                        srcdestpairs=None,
                                        flags=0,
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
        if callback is None:
            def callback(*args): pass

        buff, size, offset = c_void_p(), c_size_t(), c_longlong()

        buff_p, size_p, offset_p = byref(buff), byref(size), byref(offset)

        count_extracted = count()
        loop = asyncio.get_event_loop()
        with new_archive_write_disk(flags) as write_p:
            for entry in archive:
                # using the check below will make sure we get all child
                # entries for any folder listed in `entries`
                if any(entry.name.startswith(e) for e in entries):

                    loop.call_soon_threadsafe(
                        callback, entry.name, next(count_extracted))

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
            subprocess.run(shsplit(command), check=True,
                           stdout=stdout,
                           stderr=stderr,
                           timeout=timeout)
        except subprocess.CalledProcessError as cpe:
            errmsg = "External command `{err.cmd}` failed with exit code {err.returncode}: {err.stderr}".format(err=cpe)
            self.logger.error(errmsg)

            raise ArchiverError(errmsg).with_traceback(
                sys.exc_info()[2])
        except subprocess.TimeoutExpired as toe:
            errmsg = "External command `{err.cmd}` failed to respond after {err.timeout} seconds: {err.stderr}".format(err=toe)
            self.logger.error(errmsg)
            raise ArchiverError(errmsg).with_traceback(
                sys.exc_info()[2])


    async def extern_cmd(self, program, cmd_template,
                         archive, dest,
                         entries=None,
                         srcdestpairs=None,
                         callback=None,
                         stdout=asyncio.subprocess.PIPE):
        if callback is None:
            def callback(*args): pass

        errors = []
        if program == "unrar":
            errors = await self._extern_cmd_unrar(archive=archive, dest=dest, entries=entries, srcdestpairs=srcdestpairs, callback=callback, stdout=stdout)

        return errors


    async def _extern_cmd_unrar(self, archive, dest,
                                entries, srcdestpairs, callback,
                                stdout=asyncio.subprocess.PIPE
                                ):

        errors = []
        program = "unrar"
        opts=["x", "-cl", "-y",
              "-iddpc"]  # disables most messages

        if not srcdestpairs:

            if entries:
                self.LOGGER << "entry list given"
                total = len(entries)

                self.LOGGER << entries

                includes = self.INCLUDE_FILTERS[program](entries)

                self.LOGGER << includes
            else:
                self.LOGGER << "extracting all files"
                includes = []
                proc = await asyncio.create_subprocess_exec(
                    program, "l", archive, stdout=stdout)

                # self.LOGGER << program + " l " + archive

                total = 0
                prev = ""
                line = await proc.stdout.readline()
                while line:
                    prev, line = line, await proc.stdout.readline()

                self.LOGGER << "prev: "+prev
                # last line summarizes total bytes/items
                if prev: total = prev.split()[-1]

            self.logger.debug("total items to extract: {}".format(total))

            # we're either extracting everything, or just
            # the files listed in entries

            # self.logger.debug(" ".join([program, *opts, archive, *includes, dest]))

            proc = await asyncio.create_subprocess_exec(
                program, *opts,
                archive,
                *includes, dest,
                stdout=stdout, stderr=None)

            parse = re.compile(r'^(Creating|Extracting)\s+(\S.*)\s+OK$')
            line = await proc.stdout.readline()
            numdone = 0
            while line:
                line = line.decode('ascii').rstrip()
                # print(line)
                # m=parse.match(line.decode('ascii').rstrip())
                m = parse.match(line)
                if m:
                    numdone += 1  # send to callback as pct
                    callback(m.group(1),
                             numdone)
                line = await proc.stdout.readline()

            if proc.returncode != 0:
                errors.append((archive, proc.returncode))

        # we were given source, destination pairs from fomod
        else:
            # self.LOGGER << "src-dest pairs"
            self.LOGGER << "Running src-dest installs"
            # print(srcdestpairs)
            total = len(srcdestpairs)
            # print(total)


            # Notes: if dest does not exist, files will be extracted to
            # current directory.
            # so just to be safe...let's change our working dir
            with change_dir(str(dest)):

                numdone=count()
                for src, ddest in srcdestpairs:
                    # print(src, ddest)
                    src, ddest = src.lower(), ddest.lower()

                    if src.endswith("/"): # directory
                        # 'archive path' should be the src directory (ending slash does not matter)
                        opts.append("-ap{}".format(src.lower()))

                        # file-mask/include should be the same directory WITHOUT the ending slash (very important! weird things happen when the slash is left on...)
                        includes=src.rstrip('/').lower()

                    else: # file
                        # archive path and file mask will be the same
                        opts.append("-ap{}".format(src))
                        includes=src

                    if not ddest:  # empty string
                        # destination is just the root dest folder
                        exdest = dest

                    else:
                        # if dest was given, we need to create it first
                        exdest = Path(dest, ddest)
                        exdest.mkdir(parents=True, exist_ok=True)


                    proc = await asyncio.create_subprocess_exec(
                        program, *opts,
                        archive, includes,
                        exdest,
                        stdout=None,
                        # stdout=sys.stdout, # leave this normal stdout for now
                        stderr = None)
                        # stderr = None)

                    # tried to do this with asyncio.wait_for()...
                    # but it never stopped waiting. So hopefully
                    # we'll never need a timeout!  :|
                    result = await proc.wait()

                    # print(result)

                    if result != 0:
                        errors.append((src, result))

                    # print("numdone:", numdone)
                    callback(src, next(numdone))

        return errors
