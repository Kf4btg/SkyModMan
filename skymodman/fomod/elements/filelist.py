from io import StringIO
from pprint import pprint
import enum

class FileSystemObject:
    """
    Describes the attributes of a file or folder which will be installed if the
    conditions of its containing element are satisfied, along with any other files
    or folders listed by that element.

    Think of this as a generic class:

        FileSystemObject<T> where T: FSType

        FSType = FSType.file | FSType.folder
    """

    class FSType(enum.Enum):
        file   = "file"
        folder = "folder"

        def __repr__(self):
            return "FSType."+self.name

    def __init__(self, fstype: FSType, source: str,
                 destination: str=None, priority: int=0,
                 always_install: bool = False,
                 install_if_usable: bool = False):
        self._type = fstype
        self._source = source
        self._destination = source if destination is None else destination
        self._priority = priority
        self._always_install = always_install
        self._install_if_usable = install_if_usable

    @property
    def source(self) -> str:
        return self._source

    @property
    def destination(self) -> str:
        return self._destination

    @property
    def priority(self) -> int:
        return self._priority

    @property
    def always_install(self) -> bool:
        return self._always_install

    @property
    def install_if_usable(self) -> bool:
        return self._install_if_usable

    @property
    def type(self) -> FSType:
        return self._type

    def __repr__(self):
        sio = StringIO()
        sio.write("FileSystemObject: ")
        pprint(self.__dict__, sio)
        return sio.getvalue()

class FileList:
    """
    "files" and "folders" are lists whose entries are dict objects that describe the attributes of a filesystem item of the corresponding type.
    """

    def __init__(self, file_items=None):
        """
        file_items, if provided, must be a list() of FileSystemObjects
        """

        self._fileObjects = {
            "file" : [],
            "folder" : []
        }

        if file_items is not None:
            for fi in file_items:
                assert isinstance(fi, FileSystemObject)
                self._fileObjects[fi.type.value].append(fi)

        #     self._fileObjects["file"] = files
        #
        # if folders is not None:
        #     self._fileObjects["folder"] = folders

    # @property
    # def files(self):
    #     """
    #     return-type: list<dict(str, ...)>
    #     :return: list() of dicts() describing just the files (not folders) in this FileList
    #     """
    #     return self._fileObjects["file"]

    # def fileFSOs(self):
    @property
    def files(self):
        """
        return-type: list<FileSystemObject<FSType.file>>
        :return: list of just the files (not folders) in this FileList, as FileSystemObjects
        """
        return self._fileObjects["file"]
        # return [FileSystemObject(FileSystemObject.FSType.file, **dict(f))
        #         for f in self._fileObjects["file"]]

    # @property
    # def folders(self):
    #     """
    #     return-type: list<dict(str, ...)>
    #     :return: list() of dicts() describing just the folders in this FileList
    #     """
    #     return self._fileObjects["folder"]

    # def folderFSOs(self):
    @property
    def folders(self):
        """
        return-type: list<FileSystemObject<FSType.folder>>
        :return: list of just the folders in this FileList, as FileSystemObjects
        """
        return self._fileObjects["folder"]
        # return [FileSystemObject(FileSystemObject.FSType.file, **dict(f))
        #         for f in self._fileObjects["file"]]

    @property
    def fileObjects(self):
        """
        :return: all files and folders as a flattened list of FileSystemObjects
        """
        return [f for flist in self._fileObjects.values() for f in flist]

        # return [FileSystemObject(
        #             FileSystemObject.FSType(tag),
        #             **dict(f))
        #     for tag, flist in self._fileObjects.items()
        #     for f in flist]

    def add(self, tag: str, source: str, destination: str=None, priority: int=0, always_install: bool = False, install_if_usable: bool = False):
        """
        tag is either "file" or "folder", corresponding to the xml tag for the filesystem item being described
        :param install_if_usable:
        :param always_install:
        :param tag:
        :param source:
        :param destination:
        :param priority:
        """
        if destination is None:
            destination = source

        self._fileObjects[tag].append(
                FileSystemObject(FileSystemObject.FSType(tag),
                source, destination, priority, always_install, install_if_usable))
        #     {
            # "source" : source,
            # "destination": destination,
            # "priority": priority,
            # "always_install" : always_install,
            # "install_if_usable" : install_if_usable
            # })

    def __repr__(self):
        sio = StringIO()
        pprint(self._fileObjects, sio)
        return sio.getvalue()

# if __name__=="__main__":
#     fl = FileList()
#     fl.add("file", "here/a", None, 1, True, False)
#     fl.add("folder", "here/b", "there/b", 2, False, True)
#     fl.add("folder", "here/b/c", "")
#
#     print(fl)
#     # print(fl)
#     # print([f.type.name for f in fl.fileObjects])
#     # print(fl.fileObjects)
