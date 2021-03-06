from PyQt5 import QtCore, QtWidgets
from PyQt5.QtCore import Qt, pyqtSignal as Signal, pyqtSlot as Slot

from skymodman import exceptions, constants
from skymodman.constants.keystrings import INI
from skymodman.log import withlogger
from skymodman.interface.models import ProfileListModel
from skymodman.interface.dialogs import message

@withlogger
class ProfileHandler(QtCore.QObject):
    """Offloading all the profile-specific operations from the main
    window class to this handler."""

    newProfileLoaded = Signal(str)

    enableProfileActions = Signal(bool, str, bool)

    def __init__(self, parent, *args, **kwargs):

        self._parent = parent # the main window

        super().__init__(parent, *args, **kwargs)

        self.Manager = None

        self._profile_name = None # type: str

        # self.selector_index = -1

        # initialized model that will be used for all components
        # needing a list of available profiles
        self.model = ProfileListModel()

        # Profile Selector combobox
        self._selector = None
        """:type: QtWidgets.QComboBox"""
        # currently selected index in the profile-selector box
        self._selidx = -1

    @property
    def current_index(self):
        return self._selidx

    def setup(self, manager, selector):
        """Once the Manager has been initialized, call this to populate
        the profile list model and associate the selector combobox

        :param QtWidgets.QComboBox selector: """

        self._selector = selector

        if manager:
            self.Manager = manager

            for profile in manager.get_profiles():
                self.model.insertRows(data=profile)

            self._selector.setModel(self.model)

            # start with no selection
            self._selector.setCurrentIndex(-1)

            # call this to make sure the delete button is inactive
            self.check_enable_actions()

            # can't activate this signal until after the selector is populated
            self._selector.currentIndexChanged.connect(
                self.on_profile_select)

            # connect name-changed signal from model to manager

            def on_name_changed(old, new):
                try:
                    self.Manager.rename_profile(new, old)

                except exceptions.ProfileError as pe:
                    message('critical', "Error During Rename Operation",
                            text=str(pe), buttons='ok')


            self.model.profileNameChanged.connect(on_name_changed)


    def check_enable_actions(self):
        """performs checks to determine whether the delete and rename
        actions should be enabled or disabled

        :return: a 3-tuple of (bool, str, bool); first item is whether
            the delete action should be enabled; second item is the tooltip
            for the delete action; 3rd item is whether the rename action
            should be enabled"""

        if self._profile_name is None:
            self.enableProfileActions.emit(
                False, "Remove Profile", False)
        elif self._profile_name.lower() == 'default':
            self.enableProfileActions.emit(
                False, "Cannot Remove Default Profile", False)
        else:
            self.enableProfileActions.emit(True, "Remove Profile", True)

    def selector_index_by_name(self, pname):
        """Get the index in the profile-selector combobox of the profile
        with the given name"""

        return self._selector.findData(pname, Qt.UserRole,
                                    # we know the data stored is a string
                                    Qt.MatchFixedString)

        # self._selector.findText(pname, Qt.MatchFixedString)

    ##=============================================
    ## Profile Action slots
    ##=============================================

    @Slot(int)
    def on_profile_select(self, index):
        """
        When a new profile is chosen from the dropdown list, load all
        the appropriate data for that profile and replace the current
        data with it. Also show a message about unsaved changes to the
        current profile.

        :param int index:
        """

        old_index = self._selidx

        if index == old_index:
            # ignore this; it just means that the user clicked cancel
            # in the "save changes" dialog and we're resetting the
            # displayed profile name.
            self.LOGGER << "Resetting profile name"
            return

        if index < 0:
            # we have a problem...
            self.LOGGER.error("No profile chosen?!")
        else:
            # use userRole to get the 'on-disk' name of the profile
            new_profile = self._selector.currentData(
                Qt.UserRole)

            # if no active profile, just load the selected one.
            # if somehow selected the same profile, do nothing

            if self.Manager.profile and self.Manager.profile.name == new_profile:
                return

            # check for unsaved changes to the mod-list
            reply = self._parent.table_prompt_if_unsaved()

            # only continue to change profile if user does NOT
            # click cancel (or if there are no changes to save)
            if reply == QtWidgets.QMessageBox.Cancel:
                # reset the text in the profile selector;
                # this SHOULDn't enter an infinite loop because,
                # since we haven't yet changed
                # self.profile_selector_index, now 'index' will be
                # the same as 'old_index' at the top of this
                # function and nothing else in the program will
                # change (just the name shown in the profile
                # selector)
                self._selector.setCurrentIndex(old_index)
            else:
                self.LOGGER.info(
                    f"Activating profile '{new_profile}'")

                if self.Manager.activate_profile(new_profile):

                    self.LOGGER << "Resetting views for new profile"

                    # update our variable which tracks the current index
                    self._selidx = index

                    # No => "Don't save changes, drop them"
                    # if reply == QtWidgets.QMessageBox.No:

                    # Whether they clicked "no" or not, we
                    # don't bother reverting, mods list is getting
                    # reset; just disable the buttons
                    # self.mod_table.undo_stack.clear()

                    # update name
                    self._profile_name = new_profile
                    # disable/enable buttons as needed
                    self.check_enable_actions()

                    # tell rest of app about new profile
                    self.newProfileLoaded.emit(new_profile)
                else:
                    self.LOGGER.error("Profile Activation failed.")
                    self._selector.setCurrentIndex(old_index)


    @Slot()
    def on_new_profile_action(self):
        """
        When the 'add profile' button is clicked, create and show a
        small dialog for the user to choose a name for the new profile.
        """

        from skymodman.interface.dialogs.new_profile_dialog \
            import NewProfileDialog

        popup = NewProfileDialog(combobox_model=self.model)

        # display popup, wait for close and check signal
        if popup.exec_() == popup.Accepted:
            # add new profile if they clicked ok
            new_profile = self.Manager.new_profile(popup.final_name,
                                                   popup.copy_from)

            # add profile name to model
            self.model.addProfile(new_profile.name)

            # set new profile as active and load data
            self.load_profile_by_name(new_profile.name)

        del NewProfileDialog


    @Slot()
    def on_remove_profile_action(self):
        """
        Show a warning about irreversibly deleting the profile, then, if
        the user accept the warning, proceed to delete the profile from
        disk and remove its entry from the profile selector.
        """
        profile = self.Manager.profile

        # TODO: while it can probably be safely assumed that currentData() and currentIndex() will refer to the same profile as Manager.profile, it is NOT guaranteed; we should either verify that they are indeed the same or search the model for the profile name (as pulled from the manager) to avoid the issue altogether
        if message('warning', 'Confirm Delete Profile',
                   'Delete "' + profile.name + '"?',
                   'Choosing "Yes" below will remove this profile '
                   'and all saved information within it, including '
                   'customized load-orders, ini-edits, etc. Note '
                   'that installed mods will not be affected. This '
                   'cannot be undone. Do you wish to continue?'):
            self.Manager.delete_profile(
                self._selector.currentData())
            self._selector.removeItem(
                self._selector.currentIndex())

    # this function is overloaded to accept either no argument or
    # a single string argument
    @Slot()
    @Slot(str)
    def on_rename_profile_action(self, profile_name=None):
        """
        Query the user for a new name, then ask the mod-manager backend
        to rename the profile folder.

        :param str profile_name: if provided, rename the profile
            that has this current name; if omitted, rename the active
            profile.
        """

        # if None or ""
        if not profile_name:
            try:
                profile_name = self.Manager.profile.name
            except AttributeError as e:
                # either no profile or no manager;
                self.LOGGER.exception(e)
                # can't really continue, so abort
                return

        # noinspection PyTypeChecker,PyArgumentList
        newname = QtWidgets.QInputDialog.getText(
            self._parent,
            f"Rename Profile '{profile_name}'",
            "New name")[0]

        if newname:
            # just update the model; the ProfileNameChanged signal
            # should handle getting the Manager to do the real work
            if not self.model.rename_profile(profile_name, newname):
                self.LOGGER.error("Profile List model update failed!")

    def load_profile_by_name(self, name):
        """
        Programatically update the profile selector to select the
        profile given by `name`, triggering the ``on_profile_select``
        slot.

        :param name:
        """
        # set new profile as active and load data;
        # search the selector's model for a name that matches the arg
        self._selector.setCurrentIndex(self.selector_index_by_name(name))


    def load_initial_profile(self, load_policy):
        """

        :param int load_policy: thhis is the value of the 'Profile Load Policy'
            preference; it will be 'last', 'default', or 'none'
            (well, actually, an int corresponding the enum value
            representing that state...). Depending on which of these it
            is, load (or don't) the appropriate profile.
        """

        # ref to the enum
        PLP = constants.ProfileLoadPolicy

        if load_policy:
            # convert to enum type from int
            pload_policy = PLP(load_policy)
            to_load = {
                PLP.last:    INI.LAST_PROFILE,
                PLP.default: INI.DEFAULT_PROFILE
            }[pload_policy]
            # get the name of the default/last profile and load its data
            self.load_profile_by_name(
                self.Manager.get_config_value(to_load))