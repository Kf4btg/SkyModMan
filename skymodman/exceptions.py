class Error(Exception):
    pass

class DependencyError(Error):
    pass

#----------------------------
class InvalidConfigKeyError(Error):
    def __init__(self, key: str):
        self.key = key
    def __str__(self):
        return "'{}' is not a valid configuration key.".format(self.key)

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