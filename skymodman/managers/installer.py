from collections import OrderedDict
import shutil
import os
import subprocess
from pathlib import Path
import sys

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
    """A mapping containing from the command name to a callable crafted to return the unique include-file syntax for each of the different commands"""

    def __init__(self, *args, **kwargs):
        # noinspection PyArgumentList
        super().__init__(*args, **kwargs)
        self.archiver = ArchiveHandler()

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
                programs[prog]=InstallManager.TEMPLATES["prog"]

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


    def extract_archive(self, archive, dest_dir, entries=None):
        """
        Extract all or a subset of the contents of `archive` to the destination directory

        :param archive: path to the archive file
        :param dest_dir: The directory into which the files will be extracted. Must already exist.
        :param entries: If given, must be a list of strings to the paths of the specific items within the archive to be extracted.  If not specified or None, all entries will be extracted.
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
            success, errors = self._unpack_rar(str(archive), str(dest_dir), entries)

        else:
            try:
                self._libarchive_extract(str(archive), str(dest_dir), entries)
            except ArchiveError as e:
                success = False
                errors.append(e)

        return success, errors

    def _unpack_rar(self, archive, dest_dir, entries=None):
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
            try:
                self.run_external(
                    cmd.format(input=archive, dest=dest_dir))
                break # on success
            except ArchiveError as e:
                errors.append(e)
        else:
            # no command succeeded; try libarchive
            try:
                self._libarchive_extract(archive,
                                         dest_dir,
                                         entries)
            except ArchiveError as e:
                errors.append(e)
            success = False

        return success, errors

    def _libarchive_extract(self, archive, dest_dir, entries=None):
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
                        self._extract_matching_entries(arc, entries)
                else:
                    libarchive.extract_file(archive)
            except libarchive.ArchiveError as lae:
                errmsg = "Libarchive experienced an error attempting to unpack '{}': {}".format(archive, lae)
                self.logger.error(errmsg)

        if errmsg:
            raise ArchiveError(errmsg)

    def _extract_matching_entries(self,
                                  archive,
                                  entries,
                                  flags=0,
                                  *,
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

    def run_external(self, command, archive='', dest_dir='', entries=None, *, timeout=120):
        """

        :param str command:
        :param archive:
        :param dest_dir:
        :param timeout:
        :return:
        """

        try:
            subprocess.run(command.split(), check=True,
                           stderr=subprocess.PIPE,
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




def __test_extract():
    os.mkdir('res/test-extract')

    im.extract_archive(
        # 'res/ziptest.zip',
        'res/rartest.rar',
        'res/test-extract')

    for r, d, f in os.walk('res/test-extract'):
        print(r, d, f)

def __test_list():
    [print(e) for e in im.list_archive('res/rartest.rar')]

def __test_fomod():
    assert not im.is_fomod('res/7ztest.7z')
    print(im.is_fomod('res/rartest.rar'))

def __test_exentries():
    rar = Path('res/rartest.rar').absolute()
    print(rar)
    fpath = im.is_fomod(str(rar))
    print(fpath)

    expath = Path('res/test-extract2').absolute()
    expath.mkdir(exist_ok=True)

    print(expath)

    im.extract_archive(str(rar), str(expath), [fpath])

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