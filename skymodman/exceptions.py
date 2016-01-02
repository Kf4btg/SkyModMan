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