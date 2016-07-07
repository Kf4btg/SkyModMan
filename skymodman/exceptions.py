class Error(Exception):
    pass

class DependencyError(Error):
    pass

class GeneralError(Error):
    """
    Generic exception that accepts an explanatory string.
    """
    def __init__(self, message:str):
        self.msg = message
    def __str__(self):
        return self.msg

#----------------------------
class ConfigError(Error):
    def __init__(self, key, section):
        self.section = section
        self.key = key

class ConfigValueUnsetError(ConfigError):
    """The given key and section exist, but do not contain a valid value"""
    def __str__(self):
        return "Configuration parameter '{0.key}' in section '{0.section}' is unset.".format(self)

class MissingConfigKeyError(ConfigError):
    """Based on the config-file schema, the application has determined that a key that should be in the config file is not present."""
    def __str__(self):
        return "Configuration file missing key '{0.key}' from section '{0.section}'.".format(self)

class InvalidConfigKeyError(ConfigError):
    """
    A key was requested from the configuration file that is not present in the schema
    """
    def __str__(self):
        return "'{0.key}' is not a valid configuration key for section '{0.section}'.".format(self)

#---------------------------

class ProfileError(Error):
    def __init__(self, profilename, msg='{name}'):
        self.profilename = profilename
        self.msg = msg

    def __str__(self):
        return self.msg.format(name=self.profilename)

class ProfileDoesNotExistError(ProfileError):
    def __init__(self, profilename):
        super().__init__(profilename,
                         "No profile with the name '{name}' could be found.")

class ProfileExistsError(ProfileError):
    def __init__(self, profilename):
        super().__init__(profilename,
                         "A profile matching the name '{name}' already exists.")

class DeleteDefaultProfileError(ProfileError):
    def __init__(self):
        super().__init__('default',
                         "The default profile cannot be deleted or renamed")

#---------------------------
class FileAccessError(GeneralError):
    """
    Generic error for issues encountered when doing filesystem-related operations. pass the filename as the first argument, and use '{file}' in the message arg to refer to it.
    """
    def __init__(self, file, message='{file}'):
        super().__init__(message.format(file=file))

class FilesystemDesyncError(Error):
    """
    Raised when there is a mismatch between the folders extant in
    the installed-mods directory and a user-profile's list of mods.
    """
    def __init__(self, not_found, not_listed):
        """
        :param list[str] not_found: list of mods in the user's list that do were not found on disk (possibly deleted externally)
        :param list[str] not_listed: list of mods in the mod-installation folder that were not found in the user's list (possibly installed since this profile was last loaded)
        :return:
        """
        self.not_found = not_found
        self.not_listed = not_listed
        self.count_not_found = len(not_found)
        self.count_not_listed = len(not_listed)

    def __str__(self):
        s=""
        if self.count_not_found:
            s+="{} listed mods were not found on disk".format(self.count_not_found)
        if self.count_not_listed:
            if s: s+=", and "
            s+="{} mods found on disk were not recognized".format(self.count_not_listed)
        return s+"."

#------------------------------
class ArchiverError(Error):
    pass

#------------------------------
class FomodError(Error):
    pass

#------------------------------
class CancelMerge(Error):
    """
    Raised when the user manually cancels a directory-merge operation.
    """

class MergeSkipDir(Error):
    """
    Raised when a conflicting sub-directory is encountered during a directory-merge operation. Indicates to caller that the given directory is being ignored and only its contents will be moved.
    """