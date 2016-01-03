import typing as T

class Error(Exception):
    pass

class DependencyError(Error):
    pass

class ProfileError(Error):
    def __init__(self, profilename):
        self.profilename = profilename

class ProfileExistsError(ProfileError):
    def __str__(self):
        return "A profile with the name '{}' already exists.".format(self.profilename)

class DeleteDefaultProfileError(ProfileError):
    def __str__(self):
        return "The default profile cannot be deleted."

#---------------------------
class FilesystemDesyncError(Error):
    """
    Raised when there is a mismatch between the folders extant in
    the installed-mods directory and a user-profile's list of mods.
    """
    def __init__(self, not_found: T.List[str], not_listed: T.List[str]):
        """
        :param not_found: list of mods in the user's list that do were not found on disk (possibly deleted externally)
        :param not_listed: list of mods in the mod-installation folder that were not found in the user's list (possibly installed since this profile was last loaded)
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

