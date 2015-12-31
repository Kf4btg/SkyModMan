from .elements import ModName, ModImage, FileList, DependencyList, InstallSteps
from io import StringIO
from pprint import pprint

class Fomod:
    # def __init__(self, xml=None):
    def __init__(self):
        # self.xml = etree.parse(xml, etree.XMLParser(remove_blank_text=True, remove_comments=True))
        # self.tree = objectify.parse(xml)
        # self.config = self.xml.getroot()
        # self.config = self.tree.getroot()

        self._mod_name = None
        self._mod_image = None # path to image
        self._mod_deps = None # module dependencies ... ???? 
        self._install_steps = None
        self._required_install_files = None
        self._conditional_file_installs = None

    @property
    def module_name(self) -> ModName:
        """Name of this mod"""
        return self._mod_name

    @module_name.setter
    def module_name(self, value: ModName):
        self._mod_name = value

    @property
    def module_image(self) -> ModImage:
        """Path to the main image for this mod"""
        return self._mod_image

    @module_image.setter
    def module_image(self, value: ModImage):
        self._mod_image = value

    @property
    def required_install_files(self) -> FileList:
        return self._required_install_files

    @required_install_files.setter
    def required_install_files(self, value: FileList):
        self._required_install_files = value

    @property
    def module_dependencies(self) -> DependencyList:
        return self._mod_deps

    @module_dependencies.setter
    def module_dependencies(self, value):
        self._mod_deps = value

    @property
    def install_steps(self) -> InstallSteps:
        return self._install_steps

    @install_steps.setter
    def install_steps(self, value):
        assert isinstance(value, InstallSteps)
        self._install_steps = value

    @property
    def conditional_file_installs(self) -> list:
        return self._conditional_file_installs

    @conditional_file_installs.setter
    def conditional_file_installs(self, value):
        self._conditional_file_installs = value

    def __repr__(self):
        sio = StringIO()
        pprint(self.__dict__, sio)
        return sio.getvalue()