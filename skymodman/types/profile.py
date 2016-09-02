from pathlib import Path
from configparser import ConfigParser as confparser

from skymodman import exceptions
from skymodman.constants import FALLBACK_PROFILE
from skymodman.constants.keystrings import (Section as kstr_section,
                                            Dirs as kstr_dirs,
                                            INI as kstr_ini)
from skymodman.utils import withlogger, open_for_safe_write


ProfileFiles = (MODINFO, LOADORDER, INIEDITS, OVERWRITE, HIDDEN, SETTINGS) = (
    "modinfo.json", "loadorder.json", "iniedits.json",
    "overwrites.json", "hiddenfiles.json", "settings.ini")


# from skymodman.utils import humanizer
# @humanizer.humanize
@withlogger
class Profile:
    """
    Represents a User profile with customized mod combinations, ini edits, loadorder, etc.
    """
    __default_settings = {
        kstr_section.FILEVIEWER: {
            kstr_ini.ACTIVEONLY: True,
        },
        kstr_section.OVERRIDES: {
            kstr_dirs.SKYRIM: "",
            kstr_dirs.MODS: "",
            kstr_dirs.VFS: "",
        },
        # whether a listed override is currently active
        kstr_section.OVR_ENABLED: {
            kstr_dirs.SKYRIM: False,
            kstr_dirs.MODS:   False,
            kstr_dirs.VFS:    False,
        }
    }


    def __init__(self, profiles_dir, name=FALLBACK_PROFILE,
                 copy_profile=None, create_on_enoent=True):
        """

        :param Path profiles_dir:
        :param str name:
        :param Profile copy_profile:
        :param bool create_on_enoent: Whether to create the profile folder if it does not already exist
        """

        self.name = name

        self.folder = profiles_dir / name # type: Path

        if not self.folder.exists():
            if create_on_enoent:
                # create the directory if it doesn't exist
                self.folder.mkdir()

                # since we're creating a new profile, check to see if
                # we're cloning an already existing one
                if copy_profile is not None:
                    import shutil
                    for fpath in (copy_profile.folder / fname for fname in ProfileFiles):
                        #copy the other profile's files to our new profile dir
                        shutil.copy(str(fpath), str(self.folder))
                    del shutil
            else:
                raise exceptions.ProfileDoesNotExistError(name)

        for f in [self.folder / p for p in ProfileFiles]:

            if not f.exists():
                # if the file doesn't exist (perhaps because this is a new profile)
                # create empty placeholder for it
                f.touch()
                if f.name == SETTINGS:
                    # put default vals in the ini file
                    c = confparser()
                    c.read_dict(self.__default_settings)
                    with f.open('w') as ini:
                        c.write(ini)

        # we don't worry about the json files, but we need to load in
        # the values from the ini file and store it.
        self._config = self.load_profile_settings()
        # self.LOGGER << "Loaded profile-specific settings: {}".format(self.settings)


    @property
    def Config(self):
        # has a capital C to differentiate from path properties
        return self._config

    @property
    def modinfo(self) -> Path:
        return self.folder / MODINFO

    @property
    def loadorder(self) -> Path:
        return self.folder / LOADORDER

    @property
    def iniedits(self) -> Path:
        return self.folder / INIEDITS

    @property
    def overwrites(self) -> Path:
        return self.folder / OVERWRITE

    @property
    def hidden_files(self):
        return self.folder / HIDDEN

    @property
    def settings(self):
        return self.folder / SETTINGS

    def diroverride(self, dirkey):
        """Return the value of the profile's override for the given
        directory. If no override has been made or `dir_key` cannot
        be found in the profile's config, return an empty string.
        """
        return self.get_setting(kstr_section.OVERRIDES, dirkey) or ""

    def setoverride(self, dirkey, path):
        """
        Set a path override. Note that no path verification is performed
        here.

        :param dirkey: From constants.kstr_dirs
        :param path: should refer to a real path on the filesystem
        """

        self.save_setting(kstr_section.OVERRIDES, dirkey, path)

    def override_enabled(self, dirkey, setenabled=None):
        """

        :param dirkey:
        :param setenabled: If omitted, return the current enabled
            status of the given override. if True or False, update the
            enabled status to that value and return it.
        :return:
        """

        if setenabled is None:
            return self.get_setting(kstr_section.OVR_ENABLED, dirkey)
        elif setenabled:
            self.save_setting(kstr_section.OVR_ENABLED, dirkey, True)
        else:
            self.save_setting(kstr_section.OVR_ENABLED, dirkey, False)
        return self.get_setting(kstr_section.OVR_ENABLED, dirkey)

    def rename(self, new_name):
        """

        :param str new_name:
        :return:
        """
        if self.name.lower() == FALLBACK_PROFILE.lower():
            raise exceptions.DeleteDefaultProfileError()

        new_dir = self.folder.with_name(new_name) #type: Path

        ## if the folder exists or if it matches (case-insensitively)
        ##  one of the other profile dirs, raise exception
        if new_dir.exists() or \
            new_name.lower() in [f.name.lower() for f in self.folder.parent.iterdir()]:
            raise exceptions.ProfileExistsError(new_name)

        ## rename the directory (doesn't affect path obj)
        self.folder.rename(new_dir)

        ## verify that rename happened successfully
        if not new_dir.exists() or self.folder.exists():
            raise exceptions.ProfileError(
                self.name,
                "Error while renaming profile '{name}' to '{new_name}'"
                    .format(name=self.name, new_name=new_name))

        ## update reference
        self.folder = new_dir
        self.name = new_name

    def delete_files(self):
        """
        Delete all the files in this profile's directory.
        """
        for f in [self.folder / p for p in ProfileFiles]:
            if f.exists():
                f.unlink()

    def load_profile_settings(self):
        config = confparser()
        config.read(str(self.settings))

        # for now, just turn the config parser into a dict and return it;
        # the checks below should deal with most of the conversions we'd need
        # to worry about
        sett={}
        for sec, sub in self.__default_settings.items():
            sett[sec]={}
            for k,v in sub.items():
                if isinstance(v, bool):
                    # fallback to default vals if key or section is missing
                    sett[sec][k] = config.getboolean(sec, k, fallback=v)
                elif isinstance(v, int):
                    sett[sec][k] = config.getint(sec, k, fallback=v)
                elif isinstance(v, float):
                    sett[sec][k] = config.getfloat(sec, k, fallback=v)
                else:
                    # strings for everyone else
                    sett[sec][k] = config.get(sec, k, fallback=v)
        return  sett

    def get_setting(self, section, name):
        """
        Get a config setting from the profile

        :param section:
        :param name:
        :return: value of the setting or None if the section or name
            was not present in the config
        """

        try:
            return self._config[section][name]
        except KeyError as e:
            self.LOGGER.exception(e)
            return None

    def save_setting(self, section, name, value):
        """Change a setting value and write the updated values to disk"""
        assert section in self._config
        assert name in self._config[section]

        self._config[section][name] = value

        self._save_profile_settings()

    def _save_profile_settings(self):
        """Overwrite the settings file with the current values"""

        config = confparser()
        config.read_dict(self._config)

        with open_for_safe_write(self.settings) as ini:
            config.write(ini)

