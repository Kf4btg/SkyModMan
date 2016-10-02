from functools import partial
from collections import defaultdict, namedtuple
import os

from PyQt5.QtWidgets import QDialog, QFileDialog, QDialogButtonBox
from PyQt5.QtCore import pyqtSlot as Slot, pyqtSignal as Signal

from skymodman import Manager, constants, exceptions
from skymodman.constants.keystrings import UI, Dirs as D
from skymodman.log import withlogger

from skymodman.interface import app_settings, ui_utils
from skymodman.interface.dialogs import checkbox_message, message
from skymodman.interface.designer.uic.preferences_dialog_ui import \
    Ui_Preferences_Dialog
from skymodman.utils.fsutils import check_path



# because I'm lazy
PLP = constants.ProfileLoadPolicy

# main manager instance
MManager = Manager()

## text and style sheets for indicator labels
_label_spec = namedtuple("_label_spec", "text style")

_path_error_labels = {
    'invalid': _label_spec(text="Path not found",
                           style="QLabel {color: red; font-size: 10pt;}"),
    'missing': _label_spec(text = "Path is required",
                           style =
                            "QLabel { "
                                "color: orange; "
                                "font-size: 10pt; "
                                "font-style: italic; "
                            "}"),
    'notabs': _label_spec(text = "Path must be absolute",
                          # same style as invalid
                          style="QLabel {color: red; font-size: 10pt;}")
}

# noinspection PyArgumentList
@withlogger
class PreferencesDialog(QDialog, Ui_Preferences_Dialog):
    """
    Display a modal window allowing the user to modify general settings
    for the application.
    """

    profilePolicyChanged = Signal(int, bool)

    beginModifyPaths = Signal()
    """emitted when changes to configured paths are about to be applied"""
    endModifyPaths = Signal()
    """emitted after changes to configured paths have been applied"""

    def __init__(self, profilebox_model, profilebox_index, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # setup initial UI
        self.setupUi(self)

        ## Default Path values
        self.paths={f:MManager.Folders[f].get_path() for f in D}
        self.defpaths = {f:MManager.Folders[f].get_default() for f in D}

        ## associate text boxes with directories
        self.path_boxes = {
            D.PROFILES: self.le_profdir,
            D.SKYRIM:   self.le_dirskyrim,
            D.MODS:     self.le_dirmods,
            D.VFS:      self.le_dirvfs
        }

        ## and the corresponding 'choose-folder' buttons
        self.path_choosers = {
            D.PROFILES: self.btn_choosedir_profiles,
            D.SKYRIM:   self.btn_choosedir_skyrim,
            D.MODS:     self.btn_choosedir_mods,
            D.VFS:      self.btn_choosedir_vfs
        }

        # create a dict that will hold the current value of a text box
        # (for comparing old->new text when user manually edits box)
        self.current_text = { }

        ## associate checkboxes w/ preference names
        self.checkboxes = {
            UI.RESTORE_WINSIZE: self.cbox_restore_size,
            UI.RESTORE_WINPOS:  self.cbox_restore_pos
        }

        ## Setup Profile Load Policy radiobuttons
        self.radios = {
            PLP.last:    self.rad_load_last_profile,
            PLP.default: self.rad_load_default_profile,
            PLP.none:    self.rad_load_no_profile
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


        if profilebox_index >= 0:
            # show the currently-active profile on the profile tab
            self.combo_profiles.setCurrentIndex(profilebox_index)
        else:
            # since it's possible that there may not be an active profile,
            # fallback to showing the default profile.
            self.combo_profiles.setCurrentIndex(self.combo_profiles.findData(constants.FALLBACK_PROFILE))

        # store the currently-selected Profile object
        self._selected_profile = MManager.Profiler[self.combo_profiles.currentData()]

        # track when the user makes config changes so the buttons
        # can be enabled/disabled as needed
        # actually, right now it's enabled when anything is clicked/
        # edited and only disabled after Apply is clicked
        self._unchanged = True


        # mapping of profiles to values of overrides
        # dict [profile_name: (path, enabled)]
        self._override_paths = defaultdict(dict)

        # get easier references to ok/apply buttons
        self.btn_apply = self.prefs_btnbox.button(QDialogButtonBox.Apply)
        self.btn_ok = self.prefs_btnbox.button(QDialogButtonBox.Ok)

        # initially disabled
        self.btn_apply.setEnabled(False)

        ## and now finish setting up the UI
        self.setupMoreUI()

    @property
    def _override_mapping(self):
        """get the dir_key:dir_override mapping for the selected profile"""
        return self._override_paths[self._selected_profile.name]

    @property
    def _num_profiles(self):
        """ number of available profiles"""
        return self.combo_profiles.model().rowCount()

    @Slot()
    def _mark_changed(self):
        if self._unchanged:
            self._unchanged = False
            self.btn_apply.setEnabled(True)

    def _mark_unchanged(self):
        self._unchanged = True
        self.btn_apply.setEnabled(False)

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
        # enable Apply button after clicking
        self.cbox_restore_size.toggled.connect(self._mark_changed)

        self.cbox_restore_pos.setChecked(
            app_settings.Get(UI.RESTORE_WINPOS))
        self.cbox_restore_pos.toggled.connect(self._mark_changed)

        # check the appropriate radio button based on current policy;
        # associate a change in the radio selection with updating
        # _selected_plp
        for plp, rb in self.radios.items():
            if plp.value == self._selected_plp:
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

        # so many things are keyed with the app directory
        for d in D:
            dpath = self.paths[d]

            # if the box is empty, show the default
            self.path_boxes[d].setPlaceholderText(self.defpaths[d])

            # if a custom path has been set, show path text
            if dpath != self.defpaths[d]:
                self.path_boxes[d].setText(dpath)

            # connect dir-chooser btns
            self.path_choosers[d].clicked.connect(
                partial(self.choose_directory, d))

            # essentially all but the Profiles dir
            if d in constants.overrideable_dirs:

                # handle indicator labels
                lbl = self.indicator_labels[d]
                if not dpath:
                    self._set_label_status(lbl, 'missing')
                elif not os.path.isabs(dpath):
                    self._set_label_status(lbl, 'notabs')
                elif not check_path(dpath):
                    self._set_label_status(lbl, 'invalid')
                else:
                    # hide the label for valid paths
                    lbl.hide()

                # have the line edits with an indicator label emit a signal
                # when editing is finished that contains their key-string
                self.path_boxes[d].editingFinished.connect(
                    partial(self.on_path_edit, d))

                ##---------------------##
                # override buttons/choosers

                # x is just a shortcut for the stupid-long dict selector
                # x = self._override_paths[self._selected_profile.name]
                x = self._override_mapping

                # record current value of override
                x[d] = self._selected_profile.diroverride(d)

                if x[d].path:
                    self.override_boxes[d].setText(x[d].path)
                else:
                    self.override_boxes[d].clear()

                obtn = self.override_buttons[d]
                is_enabled = x[d].enabled
                # if override is enabled in profile, check the button
                obtn.setChecked(is_enabled)

                # connect toggle signal to profile-config-updater
                obtn.toggled.connect(partial(self.on_override_toggled, d))

                # the buttons are already set to toggle the enable status of
                # the entry field/dir chooser when pressed, so make sure those
                # are in the correct enable state to begin with
                self.override_boxes[d].setEnabled(is_enabled)
                self.override_choosers[d].setEnabled(is_enabled)

                # connect the editFinished signal
                self.override_boxes[d].editingFinished.connect(
                    partial(self.on_override_edit, d))

                # connect override chooser buttons to file dialog
                self.override_choosers[d].clicked.connect(
                    partial(self.choose_override_dir, d))

        # record initial text
        self.current_text = {
            D.PROFILES: self.le_profdir.text(),
            D.SKYRIM:   self.le_dirskyrim.text(),
            D.MODS:     self.le_dirmods.text(),
            D.VFS:      self.le_dirvfs.text()
        }

        # disable profile-dir chooser (no validation is currently
        # performed on it and having an invalid profiles directory would
        # cause some serious problems, so don't allow it to be changed
        # until we implement all that)
        self._gbox_appdirs.setEnabled(False)

        ## apply button ##
        self.btn_apply.clicked.connect(self.on_apply_button_pressed)

        # also apply changes when clicking OK
        # noinspection PyUnresolvedReferences
        self.accepted.connect(self.apply_changes)

    @Slot(int, bool)
    def on_profile_policy_changed(self, value, enabled):
        """

        :param int value: corresponding to a value in
            constants.ProfileLoadPolicy
        :param bool enabled: whether the button associated with this
            value was just enabled or disabled
        """

        if enabled:
            self._selected_plp = value
            self._mark_changed()

    @Slot()
    def change_profile(self):
        """
        Update the data on the profiles tab to reflect the data from
        the selected profile.
        """

        # profile-selector model now only stores strings; pull
        # the object from the Profile Manager
        self._selected_profile = MManager.Profiler[self.combo_profiles.currentData()]
        self.check_default()
        self._update_override_boxes()

    def _update_override_boxes(self):
        """When the selected profile changes, we need to update the
        paths displayed on the profiles tab"""

        first_time_seen = True

        # check if we've seen this profile before
        if self._selected_profile.name in self._override_paths:
            first_time_seen = False

        # either way, get the reference like this:
        opdict = self._override_paths[self._selected_profile.name]
        # if we HAVE seen it before, this will get us the saved info.
        # if we have NOT, this will create the entry for this profile
        # due to defaultdict


        for d in constants.overrideable_dirs:

            # if we haven't seen this profile before, record current
            # value of the profile's override
            if first_time_seen:
                opdict[d] = self._selected_profile.diroverride(d)
            # otherwise, we'll be using the previously stored info

            # now set the text-box to show the current value
            self.override_boxes[d].setText(opdict[d].path or "")

            is_enabled = opdict[d].enabled

            # if override is enabled in profile, check the button
            self.override_buttons[d].setChecked(is_enabled)

            # the buttons are already set to toggle the enable status of
            # the entry field/dir chooser when pressed, so make sure those
            # are in the correct enable state to begin with
            self.override_boxes[d].setEnabled(is_enabled)
            self.override_choosers[d].setEnabled(is_enabled)


    @Slot(bool)
    def set_default_profile(self, checked):
        """
        When the user checks the "default" box next to the profile
        selector, update the config to mark the current profile as
        default. If they uncheck it, mark 'default' as default...
        """

        # this is applied immediately

        if checked:
            if self._selected_profile:
                MManager.set_default_profile(self._selected_profile.name)
        else:
            MManager.set_default_profile(constants.FALLBACK_PROFILE)

    def check_default(self):
        """
        If the active profile is marked as default, check the
        "is_default" checkbox. Otherwise, uncheck it.
        """
        # make sure we have a valid profile
        if self._selected_profile:
            # don't want unchecking this to trigger changing the default profile
            with ui_utils.blocked_signals(self.cbox_default):
                self.cbox_default.setChecked(
                    self._selected_profile.name == MManager.default_profile
                )

        # if there is only 1 profile, disable the checkbox
        self.cbox_default.setEnabled(self._num_profiles > 1)

    @Slot()
    def on_apply_button_pressed(self):
        self.apply_changes()
        self._mark_unchanged()

    @Slot()
    def apply_changes(self):
        """
        Save the user changes to the appropriate config files.
        """
        self.LOGGER << "applying changes"
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

        self.beginModifyPaths.emit()

        for key, path in self.paths.items():
            newpath = self.path_boxes[key].text()
            # skip unchanged items
            if path != newpath:
                self._handle_path_change(key, path, newpath)

        self.endModifyPaths.emit()

        # and now let's do it again for the overrides

        sp = self._selected_profile
        ovrdict = self._override_mapping
        # ovrdict = self._override_paths[sp.name]

        # use values held in the override_paths collection;
        # NOTE: this only updates the profile that is currently selected at the time this method is called. Is this how it should work? Should we save all changes? should we reset any changes made when the profile is changed without hitting apply?
        for d, override_info in ovrdict.items():
            newovrd = override_info.path

            if newovrd == sp.get_override_path(d):
                # no change
                continue

            # don't check for existence (the alerts view will show if
            # the path is invalid)
            if not newovrd or os.path.isabs(newovrd):
                self.LOGGER << "setting profile override"
                # if the selected profile is also the active profile,
                # this will also set the override on the AppFolder
                # and update the alerts-view/anything else that wants
                # to know about the change
                sp.set_override_path(d, newovrd)

    ##=============================================
    ## Updating default paths
    ##=============================================

    @Slot(str)
    def on_path_edit(self, key):
        """
        Called when the user manually edits a path box
        """
        new_path = new_value = self.path_boxes[key].text()
        old_value = self.current_text[key]
        label = self.indicator_labels[key]

        if new_value != old_value:
            # enable 'Apply' button if newly entered text
            # does not match old text
            self._mark_changed()

        # if they cleared the box, the default will be active
        # ...unless there isn't one. then it will be marked missing
        if not new_value:
            new_path = self.defpaths[key]

        # now check 'new_path', whether it's the text entered or
        # the default value
        if not new_path:
            self._set_label_status(label, 'missing')
        else:
            if not os.path.isabs(new_path):
                # then they didn't enter an absolute path
                self._set_label_status(label, 'notabs')

            # if they entered a valid path
            elif os.path.exists(new_path):
                # hide the label cause we're all good
                label.setVisible(False)

            else:  # but if it was invalid...
                self._set_label_status(label, 'invalid')

        # finally, update text-tracker (make sure to use entered text):
        self.current_text[key] = new_value

    def _handle_path_change(self, key, old_path, newpath):
        """Check for a change in the text-entry-box for the path and
        act accordingly: update config, create/move dirs as needed"""

        # allow changing if the path is valid or cleared
        if not newpath:
            # if they unset the path, just change it
            # NOTE: this will reset the path to default!
            self._update_path(key, newpath)

        # if they set a valid newpath, update Manager
        elif os.path.isabs(newpath) and os.path.exists(newpath):

            do_move = remove_old = False
            # if old_path was set, actually exists, and is not empty,
            # ask if they want to copy their existing data
            if old_path and os.path.exists(old_path) and len(os.listdir(old_path))>0:

                # TODO: remember choice. Also for everything else in app
                # TODO: show progress dialog
                do_move, remove_old = checkbox_message(
                    title="Transfer {} Data?".format(
                        MManager.Folders[key].display_name),
                    text="Would you like to move your existing "
                         "data to the new location?",
                    checkbox_text="Also remove original directory",
                    checkbox_checked=False)

            if do_move:
                self._move_and_update_path(key, newpath, remove_old)
            else:
                # if the path is currently unset, invalid, or empty,
                # nothing to move

                self._update_path(key, newpath)

    def _move_and_update_path(self, key, newpath, remove_old):
        """Move the contents of the given AppFolder to a new
        location on disk. If successful, also update the local
        paths property"""
        try:
            MManager.Folders[key].move(newpath, remove_old, False)

        except exceptions.FileDeletionError as e:
            # old dir could not be removed, but all data was copied;
            # path value still updated in this case
            self.LOGGER.exception(e)
            message('warning',
                    "Could not remove original folder.",
                    "The following error occurred:",
                    detailed_text=str(e), buttons='ok',
                    default_button='ok')
            self.paths[key] = MManager.Folders[key].get_path()

        except exceptions.FileAccessError as e:
            # some error with destination path
            self.LOGGER.exception(e)
            message('critical',
                    "Cannot perform move operation.",
                    "The following error occurred:",
                    detailed_text=str(e), buttons='ok',
                    default_button='ok')

        except exceptions.MultiFileError as mfe:
            # destination was ok, but could not copy some/all contents
            # for some reason
            s = ""
            for file, exc in mfe.errors:
                self.LOGGER.exception(exc)
                s += "{0}: {1}\n".format(file, exc)
            message('critical',
                    title="Errors during move operation",
                    text="The move operation may not have fully completed. The following errors were encountered: ",
                    buttons='ok', default_button='ok',
                    detailed_text=s)

        else:
            # no errors!
            self.paths[key] = MManager.Folders[key].get_path()

    def _update_path(self, key, newpath):
        MManager.Folders[key].set_path(newpath)

        self.paths[key] = str(MManager.Folders[key].current_path)

    ##=============================================
    ## Updating overrides
    ##=============================================

    @Slot(str)
    def on_override_edit(self, key):
        """
        Called when an override path is manually edited. Determines if
        the apply button should be activated.

        :param key:
        """
        # TODO: this should probably be called on every change made to
        # the path box, not just on edit finish...or maybe on a short delay

        new_value = self.override_boxes[key].text()

        dovrd = self._override_mapping[key]

        if new_value != dovrd.path:
            self._override_mapping[key] = dovrd._replace(path=new_value)
            self._mark_changed()

    @Slot(str, bool)
    def on_override_toggled(self, dirkey, enabled):
        """
        Update the profile to save the enabled status of the override

        :param dirkey:
        :param enabled:
        """
        om = self._override_mapping

        # update the local mapping
        om[dirkey] = om[dirkey]._replace(enabled=enabled)

        ## XXX: should we wait until Apply to save this? or do it immediately like this?
        self._selected_profile.override_enabled(dirkey, enabled)

    ##=============================================
    ## Choosing directories
    ##=============================================

    @Slot(str)
    def choose_override_dir(self, folder):
        self.choose_directory(folder, True)

    @Slot(str)
    def choose_directory(self, folder, override=False):
        """
        Open the file dialog to allow the user to select a path for
        the given folder.

        :param folder:
        :param override: set to True if this is for a profile
            dir-override
        :return:
        """

        # -f-i-x-m-e-:this doesn't seem to actually show the current folder if there
        # is one...maybe that's a Qt bug, though. Or maybe it's because of the
        # hidden folder in the path?

        # update: ok...so the 'default' dialog was crap and didn't work
        # right. For some reason, adding an option (in this case
        # 'DontResolveSymlinks') caused a different dialog to be used
        # (one that looked more familiar to me) that worked MUCH better
        # and started in the correct directory.
        # Wondering if this was perhaps the 'non-native' dialog and the
        # native one was just bad on my system, I changed the options to
        # include 'UseNonNativeDialog'--but this showed a *different*
        # dialog than the other two, which seemed to be between the
        # others as far as functionality went. Presumably the "good"
        # dialog was the native one, which is reassuring.
        # Anyway, I still don't really know what's going on, but it
        # seems to work ok for now...

        ovrdict = self._override_mapping
        # ovrdict = self._override_paths[self._selected_profile.name]


        start = self._override_mapping[folder].path if override else self.paths[folder]

        # noinspection PyTypeChecker
        chosen = QFileDialog.getExistingDirectory(self,
                                                  "Select directory",
                                                  directory=start or "",
                                                  options=QFileDialog.DontResolveSymlinks)

        if check_path(chosen):

            if override:
                self.override_boxes[folder].setText(chosen)
                ovrdict[folder] = ovrdict[folder]._replace(path=chosen)
            else:
                self.path_boxes[folder].setText(chosen)
                if folder in self.indicator_labels:
                    self.indicator_labels[folder].setVisible(False)
            # enable apply button if needed
            self._mark_changed()


    def _set_label_status(self, qlabel, err_type):
        """
        sets indicator label to show a message according to `err_type`

        :param qlabel:
        :param err_type: valid values are 'invalid', 'missing', 'notabs'
        """
        try:
            spec = _path_error_labels[err_type]
        except KeyError as e:
            # don't crash
            self.LOGGER.error(e)
        else:
            qlabel.setText(spec.text)
            qlabel.setStyleSheet(spec.style)
            qlabel.setVisible(True)

