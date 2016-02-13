import os
from functools import lru_cache
from collections import deque
import asyncio
import re
from pathlib import PurePath, Path

from skymodman.utils import withlogger, tree
from skymodman.utils.fsutils import dir_move_merge
# from skymodman.managers.archive import ArchiveHandler
from skymodman.managers.archive_7z import ArchiveHandler
from skymodman.installer.fomod import Fomod
from skymodman.installer import common
from skymodman.managers import modmanager as Manager
from skymodman.constants import TopLevelDirs_Bain, TopLevelSuffixes

## todo: clean this thing up

# class installState:
#     def __init__(self):
#         self.file_path = None
#         self.install_dest = None
#         self.files_to_install = []
#         self.files_installed_so_far = deque()
#
#         self.flags = {}

@withlogger
class InstallManager:
    """
    Handles unpacking of mod archives and moving mod files and directories into the appropriate locations.
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
        self.fomoddir = None

        self.toplevitems = []
        self.docs = []
        self.inis = []
        self.baditems = []


        # self.install_state = installState()

        # maintain a mapping of lower-case versions of the image-paths
        # defined in the fomod config to the actual filesystem-location of the
        # extracted images (likely in a temp dir, having been extracted
        # for display with the Fomod-installer)
        self.normalized_imgpaths = {}

        self.install_dir = Manager.conf.paths.dir_mods / self.arc_path.stem.lower()
        # Used to track state during installation
        self.files_to_install = []
        self.files_installed = deque()
        self.flags = {}

    def init_install_state(self):
        self.files_to_install = []
        self.files_installed = deque()
        self.flags = {}

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

    async def extract(self, destination, entries=None,
                      srcdestpairs=None, callback=None):
        """
        Extract all or select items from the installer's associated mod archive to the `destination`. If either `entries` or `srcdestpairs` is specified, only the items found in those collections will be extracted (srcdestpairs takes precedence if both are provided). If neither are given, all files from the archive will be extracted to the destination.

        :param destination: extraction destination
        :param entries: list of archive entries (i.e. directories or files) to extract
        :param srcdestpairs: A list of 2-tuples where the first item is the source path within the archive of a file to install, and the second item is the path (relative to the mod installation directory) where the source should be extracted.
        """
        await self.archiver.extract(
            archive=self.archive,
            destination=destination,
            specific_entries=entries,
            callback=callback)
        # srcdestpairs = srcdestpairs,

    async def archive_contents(self, *, dirs=True, files=True):
        """
        Return list of all files within the archive

        :param dirs: include directories in the output
        :param files: include files in the output
        :return:
        """
        if self.archive_files is None:
            self.archive_dirs, self.archive_files = await self.archiver.list_archive(self.archive)

        if dirs and not files:
            return self.archive_dirs
        if files and not dirs:
            return self.archive_files

        return self.archive_dirs + self.archive_files

        # res = await self.archiver.list_archive(
        #         self.archive, include_dirs=dirs, include_files=files)

    async def get_file_count(self, *, include_dirs=True):
        """
        returns the total number of files (and possibly directories)
        within the mod archive
        :param include_dirs:
        :return:
        """

        self.LOGGER << "counting files"
        return len(await self.archive_contents(dirs=include_dirs))

    async def mod_structure_tree(self):
        """
        Build a Tree structure where the names of the branches and
        leaves represent the directory and file names, respectively,
        of the items within the archive.
        :return:
        """
        modtree = tree.Tree()
        self.LOGGER << "building tree"
        for arc_entry in (await self.archive_contents(dirs=False)):
            ap = PurePath(arc_entry)

            modtree.insert(ap.parent.parts, ap.name)

        return modtree

    def analyze_structure_tree(self, mod_tree):
        """
        check the mod-structure for an already-created tree
        :param mod_tree:
        :return: a tuple where the first item is the number of recognized
        top-level items found, and the second is a dict with the keys
        "files" and "folders", containing those recognized items, as
        well as "docs" and "fomod_dir", if anything of that kind was found.
        """
        self.logger.debug("Analyzing structure of tree")
        mod_data = {
            "folders": [],
            "files": [],
            "docs": [],
            # some mods have a fomod dir that just contains information
            # about the mod, with no config script
            "fomod_dir": None
        }
        doc_match = re.compile(r'(read.?me|doc(s|umentation)|info)', re.IGNORECASE)
        for topdir in mod_tree.keys():
            # grab anything that looks like mod data from the
            # the top level of the tree
            if topdir.lower() in TopLevelDirs_Bain:
                mod_data["folders"].append(topdir)

            elif doc_match.search(topdir):
                mod_data["docs"].append(topdir)
            elif topdir.lower()=="fomod":
                mod_data["fomod_dir"] = topdir

        for topfile in mod_tree.leaves:
            if os.path.splitext(topfile)[-1].lstrip('.').lower() in  TopLevelSuffixes:
                mod_data["files"].append(topfile)
            elif doc_match.search(topfile):
                mod_data["docs"].append(topfile)

        # one last check: if there is only one item on the top level
        # of the mod and that item is a directory, then check inside that
        # directory for the necessary files.
        if not mod_data["folders"] and not mod_data["files"]:
            if len(mod_tree) == 1 and "_files" not in mod_tree.keys():
                for _, subtree in mod_tree.items():
                    # this recursive call could obviously dig deeper than
                    # one more level in the tree, but there'd have to be
                    # several 1-folder nested directories of non-top-level
                    # dirs for that to happen, which seems rather unlikely.
                    return self.analyze_structure_tree(subtree)

        return len(mod_data["folders"])+len(mod_data["files"]), mod_data


    async def prepare_fomod(self, xmlfile, extract_dir=None):
        """
        Using the specified ModuleConfig.xml file `xmlfile`, (most likely extracted from this installer's associated archive in an earlier phase of installation), parse and analyze the script to prepare a Fomod object to give to an installer interface. Go ahead and mark any files marked as 'required installs' for installation. Finally, extract any images that were referenced in the script so that they can be shown during the installation process.

        :param xmlfile:
        :param extract_dir: Where any images referenced by the script will be extracted. It is best to use a temporary directory for this so it can be easily cleaned up after install.
        :return:
        """
        self.init_install_state()
        # self.install_state = installState() # tracks flags, install files

        # todo: figure out what sort of things can go wrong while reading the fomod config, wrap them in a FomodError (within fomod.py), and catch that here so we can report it without crashing
        self.fomod = Fomod(xmlfile)

        # we don't want to extract the entire archive before we start,
        # but we do need to extract any images defined in the
        # config file so that they can be shown during installation
        if self.archive and self.fomod.all_images and extract_dir is not None:
            await self._extract_fomod_images(extract_dir)

        # go ahead and mark any required installs
        if self.fomod.reqfiles:
            self.files_to_install=self.fomod.reqfiles

        # pprint(self.files_to_install)

    async def _extract_fomod_images(self, extract_dir, *, join=os.path.join, relpath=os.path.relpath):
        """
        if there is a (legitimate) common base-path to the images
        (they are often kept in a single directory), then extract
        that entire folder. Otherwise, extract each image path
        individually.

        :param extract_dir:
        :return:
        """
        # todo: maybe check to see if the images were inside the fomod directory, in which case they're already extracted.  Or, maybe only extract the config file by default instead of the entire fomod dir...
        await self.extract(
            extract_dir,
            entries=self.fomod.all_images)

        # get lowercase, relative versions of all files extracted so far and
        # store them for later reference
        norm_fomodfiles = {}
        for root, dirs, files in os.walk(extract_dir):
            for f in files:
                norm_fomodfiles[
                    relpath(join(root, f), extract_dir).lower()
                    ]=join(root, f)

        # ok, so this contains more than just the img paths...but it's the most
        # reliable way to make sure all the images are represented correctly.
        self.normalized_imgpaths = norm_fomodfiles

    def get_fomod_image(self, image_path):
        """
        Guaranteed to return the actual extraction path for an image path specified in a fomod config file even in spite of name-case-conflicts, so long as the file exists. If it does not exist, None is returned.
        """
        try:
            return self.normalized_imgpaths[image_path.lower()]
        except KeyError:
            return None



    def set_flag(self, flag, value):
        self.flags[flag]=value

    def unset_flag(self, flag):
        try: del self.flags[flag]
        except KeyError: pass

    def mark_file_for_install(self, file, install=True):
        """
        :param common.File file:
        :param install: if true, mark the file for install; if False, remove it from the list of files to install
        """
        if install:
            self.files_to_install.append(file)
        else:
            self.files_to_install.remove(file)

    dep_checks = { # s=self, d=dependency item (key=dependency type)
        "fileDependency": lambda s, d: s.check_file(d.file, d.state),
        "flagDependency": lambda s, d: s.check_flag(d.flag, d.value),
        "gameDependency": lambda s, d: s.check_game_version(d),
        "fommDependency": lambda s, d: s.check_fomm_version(d),
    }  ## used below

    operator_func = {
        common.Operator.OR:  any, # true if any item is true
        common.Operator.AND: all  # true iff all items are true
    } ## also used below

    def check_dependencies_pattern(self, dependencies):
        """

        :param common.Dependencies dependencies: A ``Dependencies`` object extracted from the fomod config.
        :return: boolean indicating whether the dependencies were satisfied.
        """
        # print(self.check_file.cache_info())

        condition = self.operator_func[dependencies.operator]

        return condition(self.dep_checks[dtype](self, dep)
                         for dtype, dep in dependencies)

    @lru_cache(256)
    def check_file(self, file, state):
        return Manager.checkFileState(file, state)

    def check_flag(self, flag, value):
        return flag in self.flags \
               and self.flags[flag] == value

    def check_game_version(self, version):
        return True

    def check_fomm_version(self, version):
        return True

    def check_conditional_installs(self):
        """
        Called after all the install steps have run.
        """
        flist = self.files_to_install
        if self.fomod.condinstalls:
            for pattern in self.fomod.condinstalls:
                if self.check_dependencies_pattern(pattern.dependencies):
                    flist.extend(pattern.files)




    @property
    def num_files_to_install(self):
        n=0
        for f in self.files_to_install:
            if f.type=="folder":
                n+=self._count_folder_contents(f.source)
            else:
                n+=1

        return n
        # return len(self.files_to_install)

    def _count_folder_contents(self, folder):
        folder += '/'

        n= len([f for f in self.archive_files+self.archive_dirs if f.startswith(folder)])
        # print(folder, n)
        return n

    async def install_files(self, dest_dir=None, callback=None):
        """

        :param str dest_dir: path to installation directory for this mod
        :param callback: called with args (name_of_file, total_extracted_so_far) during extraction process to indicate progress
        """


        if dest_dir is None:
            # dest_dir="/tmp/testinstall"
            dest_dir = self.install_dir

        flist = self.files_to_install
        progress = self.files_installed

        # sort files by priority, then by name
        flist.sort(key=lambda f: f.priority)
        flist.sort(key=lambda f: f.source.lower())

        _callback = callback
        if _callback is None:
            def _callback(*args): pass

        def track_progress(filename, num_done):
            progress.append(filename)
            _callback(filename, num_done)

        await self.extract(destination=dest_dir,
                           entries=[f.source for f in flist],
                           # srcdestpairs=[(f.source, f.destination)
                           #               for f in flist],
                           callback=track_progress)

        # after unpack, files must be moved to correct destinations as specified by fomod config
        for file_item in flist:

            installed=Path(dest_dir, file_item.source)
            destination = Path(dest_dir, file_item.destination)

            if file_item.type == 'file':
                # files are moved "inside" the destination
                destination.mkdir(parents=True, exist_ok=True)
                # dest = Path(dest_dir, file_item.destination, installed.name)
                installed.rename(destination / installed.name)

            elif not installed.samefile(destination):
                # folder are moved "to" the destination (their contents are merged with it)
                dir_move_merge(installed, destination)





    async def rewind_install(self, callback=print):
        """
        Called when an install is cancelled during file copy/unpacking.
        Any files that have already been moved to the install directory
        will be removed.

        :param callback:
        :return:
        """
        uninstalls=self.files_installed
        remaining=len(uninstalls)

        while remaining>0:
            await asyncio.sleep(0.02)
            f=uninstalls.pop()
            remaining -= 1
            asyncio.get_event_loop().call_soon_threadsafe(
                callback, f.source, remaining)

