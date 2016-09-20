# from contextlib import contextmanager
from configparser import ConfigParser as _parser
import os
from copy import deepcopy

from skymodman.utils import fsutils
from skymodman import exceptions

class BaseConfigManager:

    def __init__(self,
                 template,
                 environ_vars=list(),
                 config_file=None,
                 *args, **kwargs):
        """

        :param config_file: the on-disk managed file.
        :param dict[str, dict[str, str]] template: a 'mock' version of the config file; i.e. a
            dictionary with 1 level of nested dicts where each
            dict corresponds to a section in the configuration.
            Should contain sane default values.
        :param environ_vars: an iterable of strings corresponding to
            possible environmental variables.
        """

        # noinspection PyArgumentList
        super().__init__(*args, **kwargs)

        # make sure its a string
        self._cfile = str(config_file)

        self.template = template # should be considered 'read-only'

        # keep a dictionary that is effectively an in-memory version
        # of the main config file
        self.current_values = deepcopy(template) # type: dict [str, dict [str, str]]

        # hold all environment variables and their values (if any) here.
        self._environment = {k:os.getenv(k, "") for k in environ_vars}

        # self._pause_writing = False

    ##=============================================
    ## Properties
    ##=============================================

    @property
    def config_file(self):
        return self._cfile

    @config_file.setter
    def config_file(self, file):
        self._cfile = str(file)

    @property
    def env(self):
        """Return the environment-variables mappings"""
        return self._environment

    def getenv(self, varname):
        """
        An analog to os.getenv()

        :param varname:
        :return: the value of the environment variable specified by
            `varname`, or None if the variable is not known
        """

        # return None if not present
        return self._environment.get(varname)

    ##=============================================
    ## Config file
    ##=============================================

    def create_config_file(self):
        """
        Called if the main config file does not exists in the expected
        location. Creates the file using the default values from the
        config template.
        """

        config = _parser()

        for sec, kvlist in self.template.items():
            config[sec] = {}
            for key, value in kvlist.items():
                config[sec][key] = value

        self.write_config(config)

    def read_config(self):
        """
        Return a ConfigParser instance initialized from the main
        config file
        """

        config = _parser()
        config.read(self.config_file)
        return config

    def write_config(self, parser):
        """
        Given a ConfigParser instance, write its contents to the main
        config file in an atomic fashion.

        :param _parser parser:
        """

        with fsutils.open_atomic(self.config_file) as cfile:
            parser.write(cfile)

    ##=============================================
    ## Getting values
    ##=============================================

    def get_value(self, section, key):
        """
        Returns the current value for the config entry referenced by
        the given section and key

        :param str section:
        :param str key:
        """
        # print("<==Method Call: BaseConfig.get_value(", section, key, ")")

        try:
            s = self.current_values[section]
        except KeyError:
            raise exceptions.InvalidConfigSectionError(section)

        try:
            return s[key]
        except KeyError:
            raise exceptions.InvalidConfigKeyError(key, section)

    @staticmethod
    def _get_value_from(parser, section, key):
        """
        Use the given configParser instance to obtain the value. Assumes
        that section and key are valid, and raises MissingConfigKeyError
        if they are not present in the configparser

        :param _parser parser:
        :param str section:
        :param str key:
        """
        # print("<==Static Call: BaseConfig._get_value_from(",parser, section, key, ")")

        try:
            s = parser[section]
        except KeyError:
            raise exceptions.MissingConfigSectionError(section)

        try:
            return s[key]
        except KeyError:
            raise exceptions.MissingConfigKeyError(key, section)

    def load_value_from(self, parser, section, key):
        """
        Load a value from the given config parser instance
        and store it locally for retrieval w/ get_value()

        :param parser:
        :param str section:
        :param str key:
        """
        # print("<==Method Call: BaseConfig.load_value_from(",parser, section, key, ")")

        self._set_value(section, key,
                        self._get_value_from(parser, section, key))

    def default_value(self, section, key):
        """
        Using the config manager's template, return the default value
        for the entry under the given section and key.

        :param str section:
        :param str key:
        """
        # print("<==Method Call: BaseConfig.default_value(", section, key, ")")

        return self.template[section][key]

    ##=============================================
    ## Changing values
    ##=============================================

    @staticmethod
    def _set_value_on(parser, section, key, value):
        """
        Wraps assigning a value to the given ConfigParser instance
        in custom exception handlers

        :param parser:
        :param str section:
        :param str key:
        :param str value:
        """
        # print("<==Static Call: BaseConfig._set_value_on(", parser, section, key, value, ")")

        # because 'option values must be strings', make sure we're not
        # trying to store None
        # if value is None:
        #     value = ""

        try:
            s = parser[section]
        except KeyError:
            raise exceptions.InvalidConfigSectionError(section)

        try:
            s[key] = value
        except KeyError:
            raise exceptions.InvalidConfigKeyError(key, section)

    def _set_value(self, section, key, value):
        """
        Wraps assigning a value to the current_values collection
        in custom exception handlers

        :param str section:
        :param str key:
        :param str value:
        """
        # print("<==Method Call: BaseConfig._set_value(", section, key, value, ")")

        self._set_value_on(self.current_values, section, key, value)

    def update_value(self, section, key, value):
        """
        Update a value specified by the given `section` and `key` and
        save the config file.

        :param str section:
        :param str key:
        :param str value:
        """
        # print("<==Method Call: BaseConfig.update_value(", section, key, value, ")")

        conf = self.read_config()
        self._set_value_on(conf, section, key, value)
        self._set_value(section, key, value)

        self.write_config(conf)

    # @contextmanager
    # def update_values(self):
    #     """A context manager that allows one to update as many
    #     values as desired without saving the config.
    #
    #     When invoked, yields a ConfigParser instance initialized from
    #     the current file. This can be used to update the values as
    #     needed.
    #
    #     When the context manager exits, all the updated values will be
    #     written to the config file."""
    #
    #     self._pause_writing = True
    #
    #     config = self.read_config()
    #
    #     yield config
    #
    #     self._pause_writing = False
    #
    #     self.write_config(config)




