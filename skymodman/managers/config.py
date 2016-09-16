import configparser
from pathlib import Path
from collections import defaultdict

from skymodman import exceptions
from skymodman.managers.base import Submanager, BaseConfigManager
from skymodman.log import withlogger
from skymodman.utils.fsutils import check_path
from skymodman.constants import EnvVars, FALLBACK_PROFILE, keystrings

# for convenience and quicker lookup
_SECTION_GENERAL = keystrings.Section.GENERAL
_SECTION_DIRS = keystrings.Section.DIRECTORIES

_KEY_LASTPRO = keystrings.INI.LAST_PROFILE
_KEY_DEFPRO  = keystrings.INI.DEFAULT_PROFILE
_KEY_PROFDIR = keystrings.Dirs.PROFILES
_KEY_MODDIR  = keystrings.Dirs.MODS
_KEY_VFSMNT  = keystrings.Dirs.VFS
_KEY_SKYDIR  = keystrings.Dirs.SKYRIM

## config file schema (and default values) ##
_DEFAULT_CONFIG_={
    _SECTION_GENERAL: {
        _KEY_LASTPRO: FALLBACK_PROFILE,
        _KEY_DEFPRO:  FALLBACK_PROFILE
    },
    _SECTION_DIRS: {
        _KEY_PROFDIR: "", #appdirs.user_config_dir(APPNAME) + "/profiles",
        _KEY_SKYDIR: "",
        _KEY_MODDIR: "", #appdirs.user_data_dir(APPNAME) +"/mods",
        _KEY_VFSMNT: "", #appdirs.user_data_dir(APPNAME) +"/skyrimfs",
    }
}


# @humanize
@withlogger
class ConfigManager(Submanager, BaseConfigManager):

    def __init__(self, mcp, *args, **kwargs):

        # easier reference to pathmanager
        self.paths = mcp.Paths

        # put defaults into template
        _DEFAULT_CONFIG_[_SECTION_DIRS][_KEY_PROFDIR] = self.paths[_KEY_PROFDIR]
        _DEFAULT_CONFIG_[_SECTION_DIRS][_KEY_MODDIR] = self.paths[_KEY_MODDIR]
        _DEFAULT_CONFIG_[_SECTION_DIRS][_KEY_VFSMNT] = self.paths[_KEY_VFSMNT]

        super().__init__(
            template = _DEFAULT_CONFIG_,
            config_file = self.paths.file_main,
            environ_vars = EnvVars,
            mcp=mcp, *args, **kwargs)

        # track errors encountered while loading paths
        self.path_errors=defaultdict(list)

        # list of (section, key) tuples caught from MissingConfig...Errors
        self.missing_keys = []

        # read config file, make sure all required data is present or at default
        self.ensure_default_setup()

    def __getitem__(self, config_var):
        """
        Use dict-access to get the value of any of items in this config instance by property name. E.g:

        >>> config['dir_mods']
        '/path/to/mod/install/directory'
        >>> config['last_profile']
        'default'

        :param str config_var:
        :return: the value or None if the value/key cannot be found
        """

        # since our keys are (as of right now) all unique (the sections
        # are more of a visual aid than anything else), take advantage
        # of that fact to track down the requested value
        for s in self.current_values.values():
            if config_var in s:
                return s[config_var]

        # if all else fails return none
        return None

    @property
    def last_profile(self) -> str:
        """
        :return: Name of most recently active profile
        """
        return self.get_value(_SECTION_GENERAL, _KEY_LASTPRO)

    @last_profile.setter
    def last_profile(self, name):
        """
        Set `name` as the value of the 'lastproifile;' cobfig key
        and write the change to the configuration file

        :param name:
        """
        self.update_value(_SECTION_GENERAL, _KEY_LASTPRO, name)

    @property
    def default_profile(self):
        """
        :return: Name of the profile marked as default
        """
        return self.get_value(_SECTION_GENERAL, _KEY_DEFPRO)

    @default_profile.setter
    def default_profile(self, name):
        """
        Set `name` as the value of the 'default_profile' config key
        and write the change to the configuration file
        :param str name:
        """
        self.update_value(_SECTION_GENERAL, _KEY_DEFPRO, name)

    ##=============================================
    ## Setup and Sanity Checks
    ##=============================================

    def ensure_default_setup(self):
        """
        Make sure that all the required files and directories exist,
        creating them if not.
        """

        ## set up paths ##

        ##=================================
        ## Main Config dir/file
        ##---------------------------------

        ## check that config dir exists, create if missing ##
        self.paths.check_exists('dir_config',
                                use_profile=False,
                                create=True)

        ## check that main config file exists ##
        if not Path(self.config_file).exists():
            #TODO: perhaps just include a default config file and copy it in place.

            self.LOGGER.info("Creating default configuration file.")
            self.create_config_file()


        ## Load settings from main config file ##
        config = self.read_config()

        ##=================================
        ## Profile Directory
        ##---------------------------------

        ## get the configured or default profiles directory:
        # path to directory which holds all the profile info
        # TODO: should this stuff actually be in XDG_DATA_HOME??
        try:
            self.paths.dir_profiles = Path(self._get_value_from(config, _SECTION_DIRS, _KEY_PROFDIR))


        except (exceptions.MissingConfigKeyError,
                    exceptions.MissingConfigSectionError) as e:
            # XXX: on thinking about this, it may actually be beneficial to ignore a missing key here and just implicitly use the default. If the user ever customizes the path in the preferences dialog, we can write it to the config file then. This may prevent accidental changes to the path or even issues if some sort of upgrade changes the default.
            # self.missing_keys.append(exceptions.MissingConfigKeyError(_KEY_PROFDIR, _SECTION_DIRS))
            self.missing_keys.append((e.secton, _KEY_PROFDIR))

            self.LOGGER.warning("Key for profiles directory missing; using default.")
            ## Should be default already

        ## check that profiles dir exists, create if missing ##
        if not self.paths.check_exists('dir_profiles', False, True):
            # if it was missing, also create the folder for the default/fallback profile
            self.LOGGER.info("Creating directory for default profile.")
            (self.paths.dir_profiles / FALLBACK_PROFILE).mkdir()


        ##=================================
        ## Last/Default profile
        ##---------------------------------

        # store {last,default} profile in local clone

        for key in (_KEY_LASTPRO, _KEY_DEFPRO):
            try:
                # attempt to load saved values from config
                self.load_value_from(config, _SECTION_GENERAL, key)

            except (exceptions.MissingConfigKeyError,
                    exceptions.MissingConfigSectionError) as e:
                self.missing_keys.append((e.section, key))

                self.LOGGER << "setting "+key+" to default value"
                self._set_value(_SECTION_GENERAL, key, FALLBACK_PROFILE)

            finally:
                # and now check that the folders for those dirs exist
                self._check_for_profile_dir(key)


        ##=================================
        ## Game-Data Storage Folders*
        ##---------------------------------

        # * &c.

        ## load stored paths of game-data folders
        ## |-> this loads dir_mods, dir_skyrim, dir_vfs
        self._load_data_dirs(config)

        ## check that mods directory exists, but only create it if the
        # location in the config is same as the default
        self.paths.check_exists('dir_mods',
                                use_profile=False,
                                create=self.paths['dir_mods'] ==
                                     _DEFAULT_CONFIG_[_SECTION_DIRS]
                                     [_KEY_MODDIR])

        ## and finally, let's fill in any blank spots in the config.
        ## note that this does NOT overwrite any _invalid_ settings,
        ## non-existing paths, etc. It just fills in the missing
        ## keys with default values. That way, a user may be able
        ## to manually correct an invalid path (say, their external
        ## drive was unmounted) without having to reconfigure the
        ## application afterwards.

        if self.missing_keys:
            for s, k in self.missing_keys:
                # s, k = e.section, e.key

                # check if the section itself is missing
                if s not in config:
                    config[s] = {}

                config[s][k] = self.current_values[s][k]

            with self.paths.file_main.open('w') as f:
                config.write(f)

    def _check_for_profile_dir(self, key):
        """
        Check that profile for the given key (last or default) exists.
        If it doesn't, fallback to the fallback profile for that one.

        :param key:
        """
        pname = self.get_value(_SECTION_GENERAL, key)
        pdir = self.paths.dir_profiles / pname

        if not pdir.exists():
            self.LOGGER.warning("{}: Profile directory '{}' not found".format(key, pname))

            # if the profile is not already the default, set it so.
            if pname != FALLBACK_PROFILE:
                self.LOGGER << "falling back to default."
                self._set_value(_SECTION_GENERAL, key, FALLBACK_PROFILE)

                # and go ahead and recurse this once,
                # to ensure that the default folder is created
                self._check_for_profile_dir(key)
            else:
                self.LOGGER << "creating default profile directory"
                # if it is the default, create the directory
                pdir.mkdir()

    def _load_data_dirs(self, config):
        """
        Lookup the paths for the directories of game-related data (e.g.
        the main Skyrim folder, the mods-installation directory, and the
        virtual fs mount point). If the user has not configured these, use
        the default.

        :param configparser.ConfigParser config:
        """

        for evar, path_key in (
                (EnvVars.SKYDIR, _KEY_SKYDIR),
                (EnvVars.MOD_DIR, _KEY_MODDIR),
                (EnvVars.VFS_MOUNT, _KEY_VFSMNT),
        ):
            p = None  # type: Path

            # first, check if the user has specified an environment variable
            envval = self._environment[evar]
            if envval:
                if check_path(envval):
                    p = Path(envval)
                else:
                    self.path_errors[path_key].append(envval)

            # if they didn't or it didn't exist, pull the config value
            if p is None:
                try:
                    config_val = self._get_value_from(config, _SECTION_DIRS, path_key)
                except exceptions.MissingConfigKeyError as e:
                    self.missing_keys.append((e.section, path_key))
                else:
                    if check_path(config_val):
                        p = Path(config_val)
                    else:
                        self.path_errors[path_key].append(config_val)

            if p is None:
                # if key wasn't in config file for some reason,
                # check that we have a default value (skydir, for example,
                # does not (i.e. the default val is ""))
                def_path = _DEFAULT_CONFIG_[_SECTION_DIRS][
                        path_key]

                # if we have a default and it exists, use that.
                # otherwise log the error
                if check_path(def_path):
                    p = Path(def_path)
                else:
                    # noinspection PyTypeChecker
                    self.path_errors[path_key].append(
                        "default invalid: '{}'".format(def_path))

            # finally, if we have successfully deduced the path, set
            # it on the PathManager
            if p is not None:
                ## use setattr to avoid circular reference during setup
                setattr(self.paths, path_key, p)

            # update config-file mirror
            self._set_value(_SECTION_DIRS, path_key, self.paths[path_key])

        if self.path_errors:
            for att, errlist in self.path_errors.items():
                for err in errlist:
                    self.LOGGER << "Path error [" + att + "]: " + err

        ######################################################################
        #  check env for vfs mount
        ## THIS IS ALREADY DONE ABOVE; just preserving the notes down here...


        # env_vfs = os.getenv(EnvVars.VFS_MOUNT)

        # check to see if the given path is a valid mount point
        # todo: this is assuming that the vfs has already been mounted manually; I'd much rather do it automatically, so I really should just check that the given directory is empty
        # if check_path(env_vfs) and os.path.ismount(env_vfs):
        #     self.paths.dir_vfs = Path(env_vfs)
        # else:
        #     self.paths.dir_vfs = Path(config[_SECTION_GENERAL][_KEY_VFSMNT])

    ##=============================================
    ## Convenience methods for accessing what
    ## are currently our only two sections
    ##=============================================

    def update_dirpath(self, path_key):
        """
        Update the saved value of a configurable directory path
        using the current value from the PathManager (thus the
        PathManager should be updated first; actually, this is called
        from the PathManager itself, so all path changes should go
        through there and one need not worry about ever calling this
        method directly.
        """
        self.update_value(_SECTION_DIRS, path_key, self.paths[path_key])

    ## path information will be queried via the pathmanager

    def update_genvalue(self, key, value):
        """
        Update the value of a General setting

        :param key:
        :param value:
        :return:
        """
        self.update_value(_SECTION_GENERAL, key, value)

    def get_genvalue(self, key):
        """
        Get the value of a setting from the General section of the
        config.

        This is just a shortcut for config_manager.get_value("General", key)

        (though of course contants.keystrings.Section.GENERAL is
        preferred to the raw string "Directories")

        :param key: setting config key
        :return:
        """

        return self.get_value(_SECTION_GENERAL, key)
