import asyncio
import os
import re
from collections import deque
from pathlib import Path #, PurePath

from skymodman.managers.base import Submanager
from skymodman.installer.fomod import Fomod
from skymodman.installer.infoxml import InfoXML

from skymodman.types.archivefs import archivefs as arcfs
from skymodman.log import withlogger
# from skymodman.utils.tree import Tree
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
        self.archive_path = Path(mod_archive)
        self.archive_files = None
        self.archive_dirs = None
        self.fomod : Fomod = None
        # holds parsed fomod config
        self.info : InfoXML = None  # holds parsed info.xml

        # maintain a mapping of lower-case versions of the image-paths
        # defined in the fomod config to the actual filesystem-location
        # of the extracted images (likely in a temp dir, having been
        # extracted for display with the Fomod-installer)
        self.normalized_imgpaths = {}

        # name of the directory where we will install the mod
        # (initial value is tentative)
        self._install_dirname = self.archive_path.stem.lower()

        self.LOGGER << f"Init installer for '{self.archive}'"

    @property
    def install_destination(self):
        """The Path to the directory in which the current archive will
        be installed"""
        # return self.install_dir
        return self.mainmanager.Folders['mods'].path / self._install_dirname

    @property
    def install_dir(self):
        ## temporary; replace w/ install_destination
        return self.install_destination

    def path_to(self, mod_ident):
        # given install/folder name of mod, get the path to its installation directory
        return self.mainmanager.Folders['mods'].path / mod_ident

    @property
    def _modrepo(self):
        # returns path to main mod repository
        return self.mainmanager.Folders['mods'].path

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

    @property
    def has_info(self):
        """
        :return: True if the archive included an info.xml file
        """
        return self.info is not None

    def prepare_info(self, infoxml_file):
        """If the mod archive included an info.xml file, parse it
        and make it available via the "info" attribute

        :param infoxml_file: path to previously-extracted info.xml file
        """

        self.info = InfoXML(infoxml_file)

        if self.info.name:
            self.LOGGER << f"Mod Name from info.xml: {self.info.name}"

            self._install_dirname = self.info.name.lower()

    def get_fomod_image(self, image_path):
        """
        Guaranteed to return the actual extraction path for an image
        path specified in a fomod config file even in spite of
        name-case-conflicts, so long as the file exists. If it does
        not exist, ``None`` is returned.
        """
        try:
            return self.normalized_imgpaths[image_path.lower()]
        except KeyError:
            return None

    async def get_fomod_path(self):
        """
        If the associated mod archive contains a directory named 'fomod',
        return the internal path to that folder. Otherwise, return None.

        :return: str|None
        """
        async for e in self.archive_contents(files=False):
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

        # todo: figure out what sort of things can go wrong while reading the fomod config, wrap them in a FomodError (within fomod.py), and catch that here so we can report it without crashing
        self.fomod = Fomod(xmlfile, self.mainmanager.checkFileState)

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

    async def num_fomod_files_to_install(self):
        """
        From the list of folders and individual files scheduled to
        be installed from the fomod, calculate the TOTAL number of
        files and directories that need to be extracted from the
        archive.
        """
        n = 0
        for f in self.fomod.files_to_install:
            if f.type == "folder":
                n += await self.count_folder_contents(f.source)
            else:
                n += 1

        return n

    ##=============================================
    ## Archive Handling
    ##=============================================

    # srcdestpairs=None,
    async def extract(self, destination, entries=None, callback=None):
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

        # TODO: ignore "._"-prefixed mac-cruft files
        loop = asyncio.get_event_loop()
        c=0
        # noinspection PyTypeChecker
        async for extracted in self.archiver.extract(
                archive=self.archive,
                destination=destination,
                specific_entries=entries,
                # callback=callback
        ):
            c+=1
            if callback:
                loop.call_soon_threadsafe(callback, extracted, c)
        self.LOGGER << f"{c} files extracted"

        # srcdestpairs = srcdestpairs,

    #TODO: condense to a single extract() method that can optionally either yield names or just extract as fast as possible

    async def eextract(self, destination, entries=None):
        """
        Works like extract, but yields the path of each file as
        it is extracted.

        :param destination:
        :param entries:
        """

        # noinspection PyTypeChecker
        async for f in self.archiver.extract(
            archive=self.archive,
            destination=destination,
            specific_entries=entries
        ):
            yield f

    async def archive_contents(self, *, dirs=True, files=True):
        """
        Return list of all files within the archive

        :param dirs: include directories in the output
        :param files: include files in the output
        """
        if self.archive_files is None:
            self.archive_dirs, self.archive_files = \
                await self.archiver.list_archive(self.archive)

        if not dirs and not files:
            # if both are false, that's dumb. set both true.
            dirs = files = True

        if dirs:
            for f in self.archive_dirs:
                yield f
        if files:
            for f in self.archive_files:
                yield f


    async def get_archive_file_count(self, *, include_dirs=True):
        """
        returns the total number of files (and possibly directories)
        within the mod archive
        :param include_dirs:
        """

        self.LOGGER << "counting files"
        if self.archive_files is None:
            # we've not attempted to list the archive before
            return len([f async for f in self.archive_contents(dirs=include_dirs)])
        else:
            if include_dirs:
                return len(self.archive_dirs) + len(self.archive_files)
            return len(self.archive_files)

    async def count_folder_contents(self, folder):
        """
        Given a path to a folder within the archive, return the
        number of files and directories contained within that folder
        and its children
        """
        self.LOGGER << f"Counting contents of archive folder {folder!r}"

        folder = folder.strip('/') + '/'

        c = 0
        async for f in self.archive_contents():
            if f.startswith(folder): c+=1

        return c

    async def mkarchivefs(self):
        """
        Create an instance of an ArchiveFS pseudo-filesystem from the
        installer's associated mod archive.

        :return: the created archivefs instance
        """
        # create an empty archivefs--just has a root.
        modfs : arcfs.ArchiveFS = arcfs.ArchiveFS()

        # add path of each file in the archive; since intermediate
        # directories are created automatically, there's no need to do
        # mkdir--although this method DOES mean that, if the archive contains
        # any empty directories, they will not be present in the fs. Not sure
        # yet if this is going to be an issue.
        async for arc_entry in self.archive_contents(dirs=False):
            # add root anchor to all entries
            modfs.touch("/"+arc_entry)

        return modfs

    ##=============================================
    ## Actual installation
    ##=============================================

    def derive_mod_name(self):
        """
        Attempt to determine the "proper" name of the mod from
        all available information.
        """

        # a) if we're lucky, this is a Fomod install w/ a modname attr
        # TODO: some non-Fomod mods still include an "info.xml" file
        if self.has_fomod:
            fname = self.fomod.modname.name
            # fix: the fomod name often includes a version number on the end (like "Soul Gem Things v1.4.5")
            vmatch = _version_format.search(fname)
            if vmatch:
                fname = fname[:vmatch.start()].strip()

            print("fomod found:")
            print("  orig:", self.fomod.modname.name)
            print("  name:", fname)

            # return self.fomod.modname.name
            return fname

        # if not, we'll have to get clever

        # b) if the mod includes esp/bsa/etc. files, they're often
        #   labeled with the mod's "real" name
        bname = os.path.basename
        split = os.path.splitext

        # check top 2 levels
        # accumulate names
        _names = []
        ext_re = re.compile(r".*\.(es[pm]|bsa)$")
        for f in filter(lambda s: ext_re.search(s.lower()),
                           self.archive_files):
            # if re.search(r".*\.(es[pm]|bsa)$", f.lower()):
                _names.append(split(bname(f))[0])

        print(f"names from esp/bsa ({len(_names)}):")
        for n in _names:
            print(f" {n}")

        # c) see if we can figure it out from the archive name;
        # try to ignore the version numbers
        archive_name = self.archive_path.stem

        # archives downloaded from the nexus generally have
        # the mod name, then a hyphen followed by the modid, then
        # (optionally) another hyphen and version info
        m = _nexus_archive_name_format.match(archive_name)

        if m:
            name = m['name']

            # TODO: if we can get the modid, we should be able to look up the mod info on the nexus...though that would of course require writing an async web-request module...
            modid = m['modid']
            ver = m['version']

            if name:
                # ==> eventually, this should pull the name from the nexus

                # sometimes there's some extra stuff like (redundant)
                # version info on the end of the name
                exm = _extra_stuff.search(name)
                if exm:
                    name = name[:exm.start()]

            if ver:
                ver = ver.replace("-", ".")

            print("Derived from archive name:")
            print("  name:", name)
            print("  modid:", modid)
            print("  version:", ver)
            return name

        return ""


    async def _archive_installation(self, dest_dir, entries):
        """common part of install/extraction process

        clears "files_installed" list before beginning, and appends
        path of each file to it as they are extracted.

        yields paths of files as extracted
        """
        # progress = self.files_installed
        # progress.clear()

        yield "Starting extraction..."

        async for e in self.eextract(dest_dir, entries):
            yield e


    async def install_archive(self, start_dir=None):
        """
        Install the entire contents of the associated archive to its
        default location in the Mods folder

        Yields (total_extracted_so_far, file_just_extracted) tuples


        :param str start_dir: usually, files will be extracted from the
            root of the archive. If `start_dir` is provided, it must be
            a path (relative to the root of the archive files) to a
            directory that will be considered the 'root' when unpacking
            the archive.
        """

        self.LOGGER << "installing archive"

        yield "Starting extraction..."

        entries=None

        if start_dir:
            # make sure startdir ends with a single "/"
            start_dir = start_dir.strip("/")+"/"

            # use shell globbing to set our includes value;
            # this ensures we get the contents of the directory
            # and not the directory itself
            entries = [start_dir+"*"]

        # extract all or subset of archive entries
        async for extracted in self.eextract(self.install_destination,
                                             entries):
            yield extracted

        # fix file paths if needed
        if start_dir:
            self.remove_basepath(start_dir)


    def abort_install(self):
        """
        Remove all files installed so far for the active install-archive
        """
        # We can't rely on records from installation; they don't
        # necessarily line up with what was actually installed,
        # making the "rewind" approach fail.
        # Just going to remove everything in the folder

        self.uninstall(self.install_destination.name)

        ## verify that it's gone
        if self.install_destination.exists():
            self.LOGGER.error("Mod directory not removed!")
        else:
            self.LOGGER << "Mod directory removed!"


    def uninstall(self, mod_ident):
        """
        Remove all the files currently installed for the mod w/ the
        installation/folder name `mod_ident`. This cannot be undone.

        :param mod_ident: name of folder in which mod is installed.
            Must be within main mod repository.
        """

        if mod_ident:
            target = self.path_to(mod_ident)

            if target.exists() and target.is_dir():
                fsutils.recursive_delete(target)

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
        target = self.install_destination / basepath.lstrip('/')

        try:
            # move all contents to the mod-root
            for f in target.iterdir():
                f.rename(self.install_destination / f.name)
        except Exception as e:
            self.LOGGER.exception(e)
            raise

        # folder should be empty; try to remove it
        try:
            # FIXME: the dir won't necessarily be empty...
            target.rmdir()
        except OSError as e:
            self.LOGGER.error(f"Could not remove directory '{target}'")
            self.LOGGER.exception(e)


    #=================================
    # Fomod Installation
    #---------------------------------

    # async def install_fomod_files(self, dest_dir=None, callback=None):
    async def install_fomod_files(self, dest_dir=None):
        """
        Yields name of files as they are extracted

        :param str dest_dir: path to installation directory for this
            mod; if not provided, the files will be installed to the
            main Mod-install directory in a folder with the same name
            as the archive.
        """


        if dest_dir is None:
            # dest_dir="/tmp/testinstall"
            dest_dir = self.install_destination

        # get list of files  from fomod
        # --remember that fomod "files" are basically
        # {source, dest, priority} tuples
        to_install = self.fomod.files_to_install

        # sort files by priority, then by name
        to_install.sort(key=lambda f: f.priority)
        to_install.sort(key=lambda f: f.source.lower())

        async for extracted in self.eextract(
                dest_dir,
                [f.source.lstrip("/") for f in to_install]):
            yield extracted


        # FIXME: we need to unpack to a different directory thatn the destination directory (and probably not the temp dir we've been using, either, since that's likely on a RAM disk and we may have many MBs or even GBs of data to unpack). Right now, the folders from the archive are extracted as-is (e.g. we get folder '11-Your-Option' in the mod install dir) when what we really want is the files inside those folders to be placed in the root of the installation dir (or wherever the 'destination' attribute in the fomod config specifies).

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
    #
    # async def rewind_fomod_install(self, callback=print):
    #     """
    #     Called when an install is cancelled during file copy/unpacking.
    #     Any files that have already been moved to the install directory
    #     will be removed.
    #
    #     :param callback: called with (str, int) args
    #     :return:
    #     """
    #     uninstalls=self.files_installed
    #     remaining=len(uninstalls)
    #
    #     # FIXME: this doesn't actually do anything...
    #
    #     while remaining>0:
    #         # fake a slow operation...
    #         await asyncio.sleep(0.02)
    #         f=uninstalls.pop()
    #         remaining -= 1
    #         asyncio.get_event_loop().call_soon_threadsafe(
    #             callback, f.source, remaining)


##=============================================
## Regular Expressions
## -------------------
## for matching names of archives downloaded
## from the nexus
##=============================================

_nexus_archive_name_format = re.compile(
    r"""^
        (?P<name>.*)        # mod name
        -                   # hyphen, no surrounding spaces
        (?P<modid>\d{3,})   # nexus id; try for 3+ numbers

        (-                  # next section may not be present.
        (?P<version>.*)     # version; can include anything...
        )?$
    """, re.X)

# (-  # next section may not be present
            #  (?P<version>  # version; check for numbers, a,b,v
            #    [abv0-9-]*)  # can include anything, though...
            # )?$

# _n = re.compile(r"^(.*)-(\d{3,})(-(.*))?$")

__ver = r'v?(?:[0-9]+[._-])*[0-9]+[ab]?'
__alphabeta = r'alpha|beta'
__verfull = f"{__ver}|{__alphabeta}"

# composite
__vcomp = rf"\b({__verfull}[_-])*{__verfull}$"

# possible extra crap on end of name
_extra_stuff = re.compile(__vcomp, re.I)
    # r"([v]?[0-9_-]+)?(beta)?(alpha)?$", re.I)
# --this is nowhere near robust enough...

# _re_ver = re.compile(r"\b[vV](?:[0-9]+[._-])*[0-9]+[ab]?$")
_version_format = re.compile(__ver, re.I)
