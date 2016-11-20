import asyncio
import os
from collections import deque
from itertools import chain
from pathlib import PurePath, Path

from skymodman.managers.base import Submanager
from skymodman.installer.fomod import Fomod

from skymodman.types.archivefs import archivefs as arcfs
from skymodman.log import withlogger
from skymodman.utils.tree import Tree
from skymodman.utils.archive import ArchiveHandler
from skymodman.utils import fsutils


@withlogger
class InstallManager(Submanager):
    """
    Handles unpacking of mod archives and moving mod files and
    directories into the appropriate locations.
    """

    # noinspection PyArgumentList
    def __init__(self, mod_archive, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.archiver = ArchiveHandler()

        self.archive = mod_archive
        self.arc_path = Path(mod_archive)
        self.archive_files = None
        self.archive_dirs = None
        self.fomod = None

        # maintain a mapping of lower-case versions of the image-paths
        # defined in the fomod config to the actual filesystem-location
        # of the extracted images (likely in a temp dir, having been
        # extracted for display with the Fomod-installer)
        self.normalized_imgpaths = {}

        # we get the `mainmanager` attribute from our Submanager base
        # self.install_dir = self.mainmanager.Paths.dir_mods / self.arc_path.stem.lower()
        self.install_dir = self.mainmanager.Folders['mods'].path / self.arc_path.stem.lower()

        # Used to track progress during installation and allow
        # for "rewinding" a failed/cancelled partial install
        self.files_installed = deque()

        self.LOGGER << "Init installer for '{}'".format(self.archive)
        self.LOGGER << "Install destination: {}".format(self.install_dir)

    @property
    def num_files_installed_so_far(self):
        """There are only rare circumstances in which this property
        should be accessed. Namely, just immediately after the
        cancellation of an in-progress installation."""
        return len(self.files_installed)

    @property
    def install_destination(self):
        """The Path to the directory in which the current archive will
        be installed"""
        return self.install_dir

    ##=============================================
    ## FOMOD handling
    ##=============================================

    @property
    def has_fomod(self):
        """
        :return: True if this installer has found and prepared a
            Fomod configuration within the mod
        """
        return self.fomod is not None

    async def get_fomod_path(self):
        """
        If the associated mod archive contains a directory named 'fomod',
        return the internal path to that folder. Otherwise, return None.

        :return: str|None
        """
        for e in (await self.archive_contents(files=False)):
            # drop the last char because it is always '/' for directories
            if os.path.basename(e.rstrip('/')).lower() == "fomod":
                return e
        return None

    async def prepare_fomod(self, xmlfile, extract_dir=None):
        """
        Using the specified ModuleConfig.xml file `xmlfile`,
        (most likely extracted from this installer's associated
        archive in an earlier phase of installation), parse and
        analyze the script to prepare a Fomod object to give to an
        installer interface. Go ahead and mark any files marked as
        'required installs' for installation. Finally, extract any
        images that were referenced in the script so that they can be
        shown during the installation process.

        :param xmlfile:
        :param extract_dir: Where any images referenced by the script
            will be extracted. It is best to use a temporary directory
            for this so it can be easily cleaned up after install.
        """

        # make sure this is clear
        self.files_installed = deque()

        # todo: figure out what sort of things can go wrong while reading the fomod config, wrap them in a FomodError (within fomod.py), and catch that here so we can report it without crashing
        self.fomod = Fomod(xmlfile)

        # we don't want to extract the entire archive before we start,
        # but we do need to extract any images defined in the
        # config file so that they can be shown during installation
        if self.archive \
                and self.fomod.all_images \
                and extract_dir is not None:

            # this is the only place we do this, so no need to have
            # another coroutine for it...
            #XX await self._extract_fomod_images(extract_dir)

            # todo: maybe check to see if the images were inside the fomod directory, in which case they're already extracted.  Or, maybe only extract the config file by default instead of the entire fomod dir...

            await self.extract(extract_dir,
                               entries=self.fomod.all_images)

            join = os.path.join
            relpath = os.path.relpath
            # get lowercase, relative versions of all files extracted
            # so far and store them for later reference
            norm_fomodfiles = {}
            for root, dirs, files in os.walk(extract_dir):
                for f in files:
                    norm_fomodfiles[
                        relpath(join(root, f), extract_dir).lower()
                    ] = join(root, f)

            # ok, so this contains more than just the img paths...but
            # it's the most reliable way to make sure all the images
            # are represented correctly.
            self.normalized_imgpaths = norm_fomodfiles

        # pprint(self.files_to_install)

    def get_fomod_image(self, image_path):
        """
        Guaranteed to return the actual extraction path for an image
        path specified in a fomod config file even in spite of
        name-case-conflicts, so long as the file exists. If it does
        not exist, None is returned.
        """
        try:
            return self.normalized_imgpaths[image_path.lower()]
        except KeyError:
            return None

    @property
    def num_fomod_files_to_install(self):
        n = 0
        for f in self.fomod.files_to_install:
            if f.type == "folder":
                n += self.count_folder_contents(f.source)
            else:
                n += 1

        return n

    ##=============================================
    ## Archive Handling
    ##=============================================

    async def extract(self, destination, entries=None, callback=None):
                      # srcdestpairs=None,
        """
        Extract all or select items from the installer's associated
        mod archive to the `destination`. If `entries`
        is provided, only the items found in that
        collection will be extracted. If not given, all files from
        the archive will be extracted to the destination.

        :param str destination: extraction destination
        :param collections.abc.Iterable[str] entries: list of archive
            entries (i.e. directories or files) to extract
        """
        # :param srcdestpairs: A list of 2-tuples where the first item
        # is the source path within the archive of a file to install,
        # and the second item is the path (relative to the mod
        # installation directory) where the source should be extracted.

        await self.archiver.extract(archive=self.archive,
                                    destination=destination,
                                    specific_entries=entries,
                                    callback=callback)
        # srcdestpairs = srcdestpairs,

    async def archive_contents(self, *, dirs=True, files=True):
        """
        Return list of all files within the archive

        :param dirs: include directories in the output
        :param files: include files in the output
        """
        if self.archive_files is None:
            self.archive_dirs, self.archive_files = \
                await self.archiver.list_archive(self.archive)

        if dirs and not files:
            return self.archive_dirs
        if files and not dirs:
            return self.archive_files

        # otherwise return concat of both (even if `dirs` and `files`
        # are both false...because that's dumb)
        return self.archive_dirs + self.archive_files

    async def get_archive_file_count(self, *, include_dirs=True):
        """
        returns the total number of files (and possibly directories)
        within the mod archive
        :param include_dirs:
        """

        self.LOGGER << "counting files"
        return len(await self.archive_contents(dirs=include_dirs))

    def count_folder_contents(self, folder):
        """
        Given a path to a folder within the archive, return the
        number of files and directories contained within that folder
        and its children
        """
        self.LOGGER << "Counting contents of archive folder {0!r}".format(folder)

        folder += '/'

        return len(
            [f for f in chain(self.archive_files, self.archive_dirs)
             if f.startswith(folder)])

    async def mod_structure_tree(self):
        """
        Build a Tree structure where the names of the branches and
        leaves represent the directory and file names, respectively,
        of the items within the archive.
        :return:
        """
        modtree = Tree()
        self.LOGGER << "building tree"
        for arc_entry in (await self.archive_contents(dirs=False)):
            ap = PurePath(arc_entry)

            modtree.insert(ap.parent.parts, ap.name)

        return modtree

    async def mkarchivefs(self):
        """
        Create an instance of an ArchiveFS pseudo-filesystem from the
        installer's associated mod archive.

        :return: the created archivefs instance
        """
        # create an empty archivefs--just has a root.
        modfs = arcfs.ArchiveFS()

        # add path of each file in the archive; since intermediate
        # directories are created automatically, there's no need to do
        # mkdir--although this method DOES mean that, if the archive contains
        # any empty directories, they will not be present in the fs. Not sure
        # yet if this is going to be an issue.
        for arc_entry in (await self.archive_contents(dirs=False)):
            # add root anchor to all entries
            modfs.touch("/"+arc_entry)

        return modfs

    ##=============================================
    ## Actual installation
    ##=============================================

    async def install_archive(self, start_dir=None, callback=None):
        """
        Install the entire contents of the associated archive to its
        default location in the Mods folder

        :param str start_dir: usually, files will be extracted from the
            root of the archive. If `start_dir` is provided, it must be
            a path (relative to the root of the archive files) to a
            directory that will be considered the 'root' when unpacking
            the archive.

        :param callback: called with args
            (name_of_file, total_extracted_so_far) during extraction
            process to indicate progress
        """

        self.LOGGER << "installing archive"

        progress = self.files_installed
        progress.clear()

        if callback is None:
            def _callback(*args): pass
        else:
            _callback = callback

        def track_progress(filepath, num_done):
            progress.append(filepath)
            _callback(filepath, num_done)

        asyncio.get_event_loop().call_soon_threadsafe(
            _callback, "Starting extraction...", 0)

        if start_dir:
            # make sure startdir ends with a single "/"
            start_dir = start_dir.rstrip("/")+"/"

            await self.extract(destination=self.install_dir,
                               # filter archive contents based on
                               # containing directory
                               entries=[e for e in
                                        await self.archive_contents(dirs=False)
                                        if e.startswith(start_dir)],
                               callback=track_progress)

            # fix file paths
            self.remove_basepath(start_dir)

        else:

            await self.extract(destination=self.install_dir,
                           callback=track_progress)

    async def rewind_install(self, callback=print):
        """
        Called when an install is cancelled during file copy/unpacking.
        Any files that have already been moved to the install directory
        will be removed.

        :param callback: called with (str, int) args
        :return:
        """
        uninstalls=self.files_installed

        i=0
        asyncio.get_event_loop().call_soon_threadsafe(
            callback, "Removing installed files...", i)

        instdir = self.install_dir

        while uninstalls:
            # if we remove from the end, that should ensure that when we
            # reach a directory, all of its contents have already been
            # removed, and we can use rmdir() on it (assuming it had
            # no other contents beforehand)
            f=uninstalls.pop()
            f_installed = instdir / f

            if f_installed.is_dir():
                try:
                    f_installed.rmdir()
                except OSError as e:
                    # not empty; there may have been something there
                    # before we installed files
                    self.LOGGER.error("Could not remove directory")
                    self.LOGGER.exception(e)
            else:
                f_installed.unlink()

            i+=1
            asyncio.get_event_loop().call_soon_threadsafe(
                callback, f, i)

        # finally, try to remove the mod install folder
        try:
            instdir.rmdir()
        except OSError as e:
            self.LOGGER.error("Could not remove mod directory")
            self.LOGGER.exception(e)


    def remove_basepath(self, basepath):
        """For the current install_dir, given a `basepath` relative
        to the root of that directory, remove that path from all files
        under it, essentially moving them up in the file hierarchy.

        For example, if the current install_dir is "$MOD_REPO/mod42":

            >>> remove_basepath("mod42_data")

            then for every item under "$MOD_REPO/mod42/mod42_data/"
            directory, e.g.:
                "mod42/mod42_data/textures/"
                "mod42/mod42_data/scripts/"
                "mod42/mod42_data/mod42.esp"

            remove "mod42_data" from their path. The new file-
            structure would then be:

                "mod42/textures/"
                "mod42/scripts/"
                "mod42/mod42.esp"

        This is to handle mod-archives that do not place the data in the
        top-level of the archive.
        """

        # remove leading '/' from basepath so it doesn't screw stuff up
        target = self.install_dir / basepath.lstrip('/')

        try:
            # move all contents to the mod-root
            for f in target.iterdir():
                f.rename(self.install_dir / f.name)
        except Exception as e:
            self.LOGGER.exception(e)
            raise

        # folder should be empty; try to remove it
        try:
            target.rmdir()
        except OSError as e:
            self.LOGGER.error("Could not remove directory {0!r}".format(str(target)))
            self.LOGGER.exception(e)


    #=================================
    # Fomod Installation
    #---------------------------------

    async def install_fomod_files(self, dest_dir=None, callback=None):
        """

        :param str dest_dir: path to installation directory for this
            mod; if not provided, the files will be installed to the
            main Mod-install directory in a folder with the same name
            as the archive.
        :param callback: called with args
            (name_of_file, total_extracted_so_far) during extraction
            process to indicate progress
        """


        if dest_dir is None:
            # dest_dir="/tmp/testinstall"
            dest_dir = self.install_dir

        # get list of files from fomod
        to_install = self.fomod.files_to_install

        progress = self.files_installed

        # sort files by priority, then by name
        to_install.sort(key=lambda f: f.priority)
        to_install.sort(key=lambda f: f.source.lower())


        if callback is None:
            def _callback(*args): pass
        else:
            _callback = callback

        def track_progress(filename, num_done):
            progress.append(filename)
            _callback(filename, num_done)

        asyncio.get_event_loop().call_soon_threadsafe(
            _callback, "Starting extraction...", 0)

        # FIXME: we need to unpack to a different directory thatn the destination directory (and probably not the temp dir we've been using, either, since that's likely on a RAM disk and we may have many MBs or even GBs of data to unpack). Right now, the folders from the archive are extracted as-is (e.g. we get folder '11-Your-Option' in the mod install dir) when what we really want is the files inside those folders to be placed in the root of the installation dir (or wherever the 'destination' attribute in the fomod config specifies).

        await self.extract(destination=dest_dir,
                           entries=[f.source for f in to_install],
                           # srcdestpairs=[(f.source, f.destination)
                           #               for f in flist],
                           callback=track_progress)

        # after unpack, files must be moved to correct destinations
        # as specified by fomod config
        dmm = fsutils.dir_move_merge
        for file_item in to_install:

            # FIXME: this loop right here is supposed to address the problem discussed in the above FIXME, but it doesn't seem to work...

            installed = Path(dest_dir, file_item.source)
            destination = Path(dest_dir, file_item.destination.lower())

            if file_item.type == 'file':
                # files are moved "inside" the destination
                destination.mkdir(parents=True, exist_ok=True)
                installed.rename(destination / installed.name)

            elif not installed.samefile(destination):
                # folder are moved "to" the destination (their contents
                # are merged with it)
                dmm(installed, destination,
                    overwite=True, name_mod=str.lower)

    async def rewind_fomod_install(self, callback=print):
        """
        Called when an install is cancelled during file copy/unpacking.
        Any files that have already been moved to the install directory
        will be removed.

        :param callback: called with (str, int) args
        :return:
        """
        uninstalls=self.files_installed
        remaining=len(uninstalls)

        # FIXME: this doesn't actually do anything...

        while remaining>0:
            # fake a slow operation...
            await asyncio.sleep(0.02)
            f=uninstalls.pop()
            remaining -= 1
            asyncio.get_event_loop().call_soon_threadsafe(
                callback, f.source, remaining)
