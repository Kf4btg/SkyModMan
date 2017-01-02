class Error(Exception):
    """Base class for all app-specific errors"""

class GeneralError(Error):
    """
    Generic exception that accepts an explanatory string.
    """
    def __init__(self, message:str):
        self.msg = message
    def __str__(self):
        return self.msg

#----------------------------

class DatabaseError(GeneralError):
    """Use for errors encountered during database interaction"""

#----------------------------
class ConfigError(Error):
    """Base class for configuration-related exceptions."""
    def __init__(self, key, section):
        self.section = section
        self.key = key

class InvalidConfigSectionError(GeneralError):
    def __init__(self, section):
        self.section = section
        super().__init__(f"Invalid section header '{section}'")

class ConfigValueUnsetError(ConfigError):
    """The given key and section exist, but do not contain a valid value"""
    def __str__(self):
        return f"Configuration parameter '{self.key}' in section '{self.section}' is unset."
    
class MissingConfigSectionError(GeneralError):
    def __init__(self, section):
        self.section = section
        super().__init__(f"Section header '{section}' not found")

class MissingConfigKeyError(ConfigError):
    """Based on the config-file schema, the application has determined that a key that should be in the config file is not present."""
    def __str__(self):
        return f"Configuration file missing key '{self.key}' from section '{self.section}'."

class InvalidConfigKeyError(ConfigError):
    """
    A key was requested from the configuration file that is not present in the schema
    """
    def __str__(self):
        return f"'{self.key}' is not a valid configuration key for section '{self.section}'."

#---------------------------
class InvalidAppDirectoryError(GeneralError):
    """Raised when one of the important directories required for app-
    function is invalid, unset, or missing."""
    def __init__(self, dir_key, current_value, msg="A required directory is invalid or unset"):
        super().__init__(msg)
        self.dir_key = dir_key
        self.curr_path = current_value

    def __str__(self):
        return "{msg}: directory {which}, currently {what}".format(
            msg=self.msg,
            which=self.dir_key,
            what="'%s'" % self.curr_path if self.curr_path else 'unset'
        )

#---------------------------

class ProfileError(Error):
    """General Error for exceptions related to Profiles."""
    def __init__(self, profilename, msg='{name}'):
        self.profilename = profilename
        self.msg = msg

    def __str__(self):
        return self.msg.format(name=self.profilename)

class ProfileDoesNotExistError(ProfileError):
    """Raised when trying to load a Profile that cannot be found"""
    def __init__(self, profilename):
        super().__init__(profilename,
                         "No profile with the name '{name}' could be found.")

class ProfileExistsError(ProfileError):
    """Raised when attempting to create a profile with the same name
    of one which already exists."""
    def __init__(self, profilename):
        super().__init__(profilename,
                         "A profile matching the name '{name}' already exists.")

class ProfileDeletionError(ProfileError):
    """Raised when a profile could not (fully) deleted"""
    def __init__(self, profilename):
        super().__init__(profilename,
                         "The profile directory for '{name}' could be"
                         " fully removed")

class DeleteDefaultProfileError(ProfileError):
    """Raised when trying to delete the default profile."""
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

class FileDeletionError(FileAccessError):
    """
    Raised when an attempt to delete a file or folder fails
    """


class MultiFileError(Error):
    """
    Raised when errors occur during a multi-file filesystem operation,
    such as moving a number of folders to a new location on the filesystem.
    Contains the collection of errors.
    """
    def __init__(self, errors, message=""):
        """

        :param errors: a list of tuples of form (src, dest, exception)
        :param message: optional message containing additional information.
        """
        self.errors = errors
        self.msg = message

    def __str__(self):
        if self.msg:
            return f"{self.msg}: {self.errors}"
        return str(self.errors)


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
            s+=f"{self.count_not_found} listed mods were not found on disk"
        if self.count_not_listed:
            if s: s+=", and "
            s+=f"{self.count_not_listed} mods found on disk were not recognized"
        return s+"."

#------------------------------
class ArchiverError(Error):
    """Indicates an error during archive extraction."""

#------------------------------
class FomodError(Error):
    pass

class DependencyError(Error):
    """Raised if a mod dependency is not satisfied during installation."""

#------------------------------
class CancelMerge(Error):
    """
    Raised when the user manually cancels a directory-merge operation.
    """

class MergeSkipDir(Error):
    """
    Raised when a conflicting sub-directory is encountered during a
    directory-merge operation. Indicates to caller that the given
    directory is being ignored and only its contents will be moved.
    """