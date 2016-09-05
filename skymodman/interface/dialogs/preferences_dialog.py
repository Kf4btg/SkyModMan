from functools import partial
import os

from PyQt5.QtWidgets import QDialog, QFileDialog, QDialogButtonBox
from PyQt5.QtCore import pyqtSlot, pyqtSignal #QStringListModel, Qt

from skymodman.managers import modmanager
from skymodman.interface import app_settings, ui_utils
from skymodman.interface.dialogs import message, checkbox_message
from skymodman.interface.designer.uic.preferences_dialog_ui import \
    Ui_Preferences_Dialog
from skymodman.utils import withlogger
from skymodman.utils.fsutils import check_path, create_dir
from skymodman import constants, exceptions
from skymodman.constants.keystrings import UI, Dirs as D



# because I'm lazy
PLP = constants.ProfileLoadPolicy

Manager = modmanager.Manager()
# ref to the ConfigManager
# Config = Manager.Config

## text and style sheets for indicator labels
_invalid_path_str = "Path not found"
_invalid_path_style = "QLabel {color: red; font-size: 10pt;}"

_missing_path_str = "Path is required"
_missing_path_style = "QLabel {color: orange; font-size: 10pt; " \
                      "font-style: italic; }"

_notabs_path_str = "Path must be absolute"

@withlogger
class PreferencesDialog(QDialog, Ui_Preferences_Dialog):
    """
    Display a modal window allowing the user to modify general settings
    for the application.
    """

    profilePolicyChanged = pyqtSignal(int, bool)
    pathEditFinished = pyqtSignal(str)

    def __init__(self, profilebox_model, profilebox_index, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # setup initial UI
        self.setupUi(self)

        ## create mappings for all the component groups using ##
        ## our constant key-strings ##

        ## Default Path values
        # returns empty strings for unset paths
        self.paths={p:Manager.get_directory(p, False) for p in D}

        ## associate text boxes with directories
        self.path_boxes = {
            D.PROFILES: self.le_profdir,
            D.SKYRIM:   self.le_dirskyrim,
            D.MODS:     self.le_dirmods,
            D.VFS:      self.le_dirvfs
        }

        self.path_choosers = {
            D.PROFILES: self.btn_choosedir_profiles,
            D.SKYRIM:   self.btn_choosedir_skyrim,
            D.MODS:     self.btn_choosedir_mods,
            D.VFS:      self.btn_choosedir_vfs
        }

        ## associate checkboxes w/ preference names
        self.checkboxes = {
            UI.RESTORE_WINSIZE: self.cbox_restore_size,
            UI.RESTORE_WINPOS: self.cbox_restore_pos
        }

        ## Setup Profile Load Policy radiobuttons
        self.radios = {
            PLP.last: self.rad_load_last_profile,
            PLP.default: self.rad_load_default_profile,
            PLP.none: self.rad_load_no_profile
        }

        #-- "path is valid" indicator labels

        self.indicator_labels = {
            D.SKYRIM: self.lbl_skydir_status,
            D.MODS:   self.lbl_moddir_status,
            D.VFS:    self.lbl_vfsdir_status
        }

        ## dir-override boxes

        self.override_buttons = {
            D.SKYRIM: self.btn_enable_skydir_override,
            D.MODS:   self.btn_enable_moddir_override,
            D.VFS:    self.btn_enable_vfsdir_override
        }

        self.override_boxes = {
            D.SKYRIM: self.le_skydir_override,
            D.MODS:   self.le_moddir_override,
            D.VFS:    self.le_vfsdir_override
        }

        self.override_choosers = {
            D.SKYRIM: self.btn_choose_skydir_override,
            D.MODS:   self.btn_choose_moddir_override,
            D.VFS:    self.btn_choose_vfsdir_override
        }

        ##-- some data associations --##

        # load and store the current policy
        self._active_plp = self._selected_plp = app_settings.Get(
                             UI.PROFILE_LOAD_POLICY)

        # reuse the main profile-combobox-model for this one here
        self.combo_profiles.setModel(profilebox_model)
        self.combo_profiles.setCurrentIndex(profilebox_index)

        # store the currently-selected Profile object
        self._selected_profile = self.combo_profiles.currentData()
        """:type: skymodman.managers.profiles.Profile"""

        ## and now finish setting up the UI
        self.setupMoreUI()

    def setupMoreUI(self):
        """More adjustments to the UI"""

        # make sure the General tab is showing
        self.prefs_tabwidget.setCurrentIndex(0)


        ##=================================
        ## Tab 1: General/App dirs
        ##---------------------------------

        # -- checkboxes should reflect current settings
        self.cbox_restore_size.setChecked(
            app_settings.Get(UI.RESTORE_WINSIZE))

        self.cbox_restore_pos.setChecked(
            app_settings.Get(UI.RESTORE_WINPOS))

        # check the appropriate radio button based on current policy;
        # associate a change in the radio selection with updating
        # _selected_plp
        for plp, rb in self.radios.items():
            if plp == self._selected_plp:
                rb.setChecked(True)

            # chain each button's toggled(bool) signal to the
            # profilePolicyChanged signal, which includes the value of
            # the button's associated policy
            rb.toggled.connect(partial(self.profilePolicyChanged.emit,
                                       plp.value))

        # noinspection PyUnresolvedReferences
        # and connect this signal to the handler
        # which updates _selected_plp
        self.profilePolicyChanged.connect(
            self.on_profile_policy_changed)


        ##=================================
        ## Tab 3: Profiles
        ##---------------------------------

        # make sure to check the 'default' box if necessary
        self.check_default()

        # we don't care about the value it sends, so we just as easily
        # could have used 'textchanged' rather than index, but this
        # seems lighter/more appropriate
        self.combo_profiles.currentIndexChanged.connect(
            self.change_profile)

        self.cbox_default.toggled.connect(self.set_default_profile)

        ##=================================
        ## The Big Loop
        ##---------------------------------
        ## for each of the application-directories,
        ## setup any UI-element associated with it to
        ## the correct initial status.

        # game-related
        gdirs = (D.SKYRIM, D.MODS, D.VFS)

        # so many things are keyed with the app directory
        for d in D:
            dpath = self.paths[d]
            # show path text
            self.path_boxes[d].setText(dpath)

            # connect dir-chooser btns
            self.path_choosers[d].clicked.connect(
                partial(self.choose_directory, d))

            # essentially all but the Profiles dir
            if d in gdirs:

                # handle indicator labels
                lbl = self.indicator_labels[d]
                if not dpath:
                    self._mark_missing_path(lbl)
                elif not check_path(dpath):
                    self._mark_invalid_path(lbl)
                elif not os.path.isabs(dpath):
                    self._mark_nonabs_path(lbl)
                else:
                    # hide the label for valid paths
                    lbl.hide()

                # have the line edits with an indicator label emit a signal
                # when editing is finished that contains their key-string
                self.path_boxes[d].editingFinished.connect(
                    partial(self.pathEditFinished.emit, d))

                ##---------------------##
                # override buttons/choosers
                self.override_boxes[d].setText(self._selected_profile.diroverride(d, ignore_enabled=True))

                obtn = self.override_buttons[d]
                # if override is enabled in profile, check the button
                obtn.setChecked(self._selected_profile.override_enabled(d))

                # connect toggle signal to profile-config-updater
                obtn.toggled.connect(partial(self.on_override_toggled, d))

                # the buttons are already set to toggle the enable status of
                # the entry field/dir chooser when pressed, so make sure those
                # are in the correct enable state to begin with
                self.override_boxes[d].setEnabled(obtn.isChecked())
                self.override_choosers[d].setEnabled(obtn.isChecked())

                # connect override chooser buttons to file dialog
                self.override_choosers[d].clicked.connect(
                    partial(self.choose_override_dir, d))


        # connect pathEditFinished signal to our validation handler
        # noinspection PyUnresolvedReferences
        self.pathEditFinished.connect(self.on_path_edit)

        ## apply button ##
        # btn_apply = self.prefs_btnbox.button(QDialogButtonBox.Apply)
        self.prefs_btnbox.button(QDialogButtonBox.Apply
                                 ).clicked.connect(self.apply_changes)

        # also apply changes when clicking OK
        # noinspection PyUnresolvedReferences
        self.accepted.connect(self.apply_changes)

    @pyqtSlot(int, bool)
    def on_profile_policy_changed(self, value, enabled):
        """

        :param int value: corresponding to a value in
            constants.ProfileLoadPolicy
        :param bool enabled: whether the button associated with this
            value was just enabled or disabled
        """

        if enabled:
            self._selected_plp = constants.ProfileLoadPolicy(value)

    @pyqtSlot(str)
    def on_path_edit(self, key):
        """
        Called when the user manually edits a path box
        """
        new_value = self.path_boxes[key].text()
        label = self.indicator_labels[key]

        # if they cleared the box, mark it missing
        if not new_value:
            self._mark_missing_path(label)

        elif not os.path.isabs(new_value):
            # then they didn't enter an absolute path
            self._mark_nonabs_path(label)

        # if they entered a valid path
        elif os.path.exists(new_value):
            # hide the label cause we're all good
            label.setVisible(False)

        else: # but if it was invalid...
            # show a messagebox asking if they would like to create it
            if message(title='Path not found',
                       text="Would you like to create this directory?",
                       info_text=new_value):
                create_dir(new_value)

                # and just to make sure...
                if os.path.exists(new_value):
                    label.setVisible(False)
                else:
                    self._mark_invalid_path(label)
            # if they say no, mark it invalid
            else:
                self._mark_invalid_path(label)


    @pyqtSlot()
    def change_profile(self):
        """
        Update the data on the profiles tab to reflect the data from
        the selected profile.
        """
        self._selected_profile = self.combo_profiles.currentData()
        self.check_default()
        self._update_override_boxes()

    def _update_override_boxes(self):
        """When the selected profile changes, we need to update the
        paths displayed on the profiles tab"""

        for d in (D.SKYRIM, D.MODS, D.VFS):
            self.override_boxes[d].setText(
                self._selected_profile.diroverride(d,
                                                   ignore_enabled=True))

            obtn = self.override_buttons[d]
            # if override is enabled in profile, check the button
            obtn.setChecked(self._selected_profile.override_enabled(d))

            # the buttons are already set to toggle the enable status of
            # the entry field/dir chooser when pressed, so make sure those
            # are in the correct enable state to begin with
            self.override_boxes[d].setEnabled(obtn.isChecked())
            self.override_choosers[d].setEnabled(obtn.isChecked())


    @pyqtSlot(bool)
    def set_default_profile(self, checked):
        """
        When the user checks the "default" box next to the profile
        selector, update the config to mark the current profile as
        default. If they uncheck it, mark 'default' as default...
        """
        if checked:
            if self._selected_profile:
                Manager.Config.default_profile = self._selected_profile.name
        else:
            Manager.Config.default_profile = constants.FALLBACK_PROFILE

    def check_default(self):
        """
        If the active profile is marked as default, check the
        "is_default" checkbox. Otherwise, uncheck it.
        """
        # make sure we have a valid profile
        if self._selected_profile:
            # don't want unchecking this to trigger changing the default profile
            with ui_utils.blocked_signals(self.cbox_default):
                self.cbox_default.setChecked(self._selected_profile.name == Manager.Config.default_profile)


    @pyqtSlot(str, bool)
    def on_override_toggled(self, dirkey, enabled):
        """
        Update the profile to save the enabled status of the override

        :param dirkey:
        :param enabled:
        """
        ## XXX: should we wait until Apply to save this? or do it immediately like this?
        self._selected_profile.override_enabled(dirkey, enabled)


    @pyqtSlot()
    def apply_changes(self):
        """
        Save the user changes to the appropriate config files.
        """
        # TODO: disable the OK/Apply buttons when there are no changes to apply.
        # TODO: allow resetting the paths to default

        for pref, cbox in self.checkboxes.items():
            app_settings.Set(pref, cbox.isChecked())

        # check for a change in the profile-load-policy
        if self._active_plp != self._selected_plp:
            app_settings.Set(
                UI.PROFILE_LOAD_POLICY,
                self._selected_plp)

        # check if any of the paths have changed and update accordingly
        for key, path in self.paths.items():
            newpath = self.path_boxes[key].text()

            # skip if unchanged
            if path == newpath: continue

            # allow changing if the path is valid or cleared
            if not newpath:
                # if they unset the path, just change it
                self._update_path(key, newpath)

            # if they set a valid new path, ask if they want to copy
            # their existing data (assuming there is any)
            # TODO: remember choice. Also for everything else in app
            elif os.path.isabs(newpath) and os.path.exists(newpath):
                if not path:
                    # if the path is currently unset, nothing to move
                    self._update_path(key, newpath)
                else:
                    do_move, remove_old = checkbox_message(
                        title="Transfer {} Data?".format(
                            constants.DisplayNames[key]),
                        text="Would you like to move your existing "
                             "data to the new location?",
                        checkbox_text="Also remove original directory",
                        checkbox_checked=True)
                    if do_move:
                        try:
                            Manager.Paths.move_dir(key, newpath, remove_old)
                        except exceptions.FileAccessError as e:
                            message('critical',
                                    "Cannot perform move operation.",
                                    "The following error occurred:",
                                    detailed_text=str(e), buttons='ok',
                                    default_button='ok')
                        except exceptions.MultiFileError as mfe:
                            s=""
                            for file, exc in mfe.errors:
                                s+="{0}: {1}\n".format(file, exc)
                            message('critical',
                                    title="Errors during move operation",
                                    text="The move operation may not have fully completed. The following errors were encountered: ",
                                    buttons='ok', default_button='ok',
                                    detailed_text=s)
                        else:
                            self._update_path(key, newpath)
                    else:
                        self._update_path(key, newpath)

        # and now let's do it again for the overrides
        sp = self._selected_profile
        for d, box in self.override_boxes.items():
            newovrd = box.text()

            if newovrd == sp.diroverride(d):
                continue

            if not newovrd or (os.path.isabs(newovrd)
                               and os.path.exists(newovrd)):
                # we can't just call Manager.set_directory(...,...,True)
                # because that method only sets overrides for the active
                # profile, which is not necessarily the same as the
                # selected profile here
                sp.setoverride(d, newovrd)

    def _update_path(self, key, newpath, is_override=False):
        Manager.set_directory(key, newpath, is_override)
        if not is_override:
            self.paths[key] = newpath


    @pyqtSlot(str)
    def choose_override_dir(self, folder):
        self.choose_directory(folder, True)

    @pyqtSlot(str)
    def choose_directory(self, folder, override=False):
        """
        Open the file dialog to allow the user to select a path for
        the given folder.

        :param folder:
        :param override: set to True if this is for a profile
            dir-override
        :return:
        """

        # fixme: this doesn't seem to actually show the current folder if there
        # is one...maybe that's a Qt bug, though. Or maybe it's because of the
        # hidden folder in the path?

        start = self._selected_profile.diroverride(folder) if override else self.paths[folder]

        # noinspection PyTypeChecker
        chosen = QFileDialog.getExistingDirectory(self,
                                                  "Select directory",
                                                  start or "")

        if check_path(chosen):

            if override:
                self.override_boxes[folder].setText(chosen)
            else:
                self.path_boxes[folder].setText(chosen)
                if folder in self.indicator_labels.keys():
                    self.indicator_labels[folder].setVisible(False)



    def _mark_invalid_path(self, qlabel):
        # takes given indicator label and sets it to 'invalid' status
        qlabel.setText(_invalid_path_str)
        qlabel.setStyleSheet(_invalid_path_style)
        qlabel.setVisible(True)
    def _mark_missing_path(self, qlabel):
        # takes given indicator label and sets it to 'missing' status
        qlabel.setText(_missing_path_str)
        qlabel.setStyleSheet(_missing_path_style)
        qlabel.setVisible(True)
    def _mark_nonabs_path(self, qlabel):
        # takes given indicator label and sets it to 'not absolute' status
        qlabel.setText(_notabs_path_str)
        qlabel.setStyleSheet(_invalid_path_style)
        qlabel.setVisible(True)

