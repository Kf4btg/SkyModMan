"""Collection of pre-constructed Alerts to use when necessary. Using
preconstructed instances prevents duplication of alerts when they
are stored by their hash-value, such as in a set or dict."""

from skymodman.types.alert import Alert as _alert, LOW, NORMAL, HIGH

from skymodman.constants.keystrings import Dirs as _dirs


test_alert = None   # type: _alert
dnf_skyrim = None   # type: _alert
dnf_mods = None     # type: _alert
dnf_vfs = None     # type: _alert


# guess these aren't really constants so much, are they...
def init_alerts(manager):
    """Must be called with the main modmanager instance as a
    parameter in order to properly set up the alerts"""
    global test_alert, dnf_skyrim, dnf_mods, dnf_vfs

    test_alert = _alert(level=NORMAL, label='Test Alert',
                      desc="This is a Test alert",
                      fix="You cannot fix this. Ever.",
                      check=lambda: True)

    ##=============================================
    ## Directory Not Found Alerts
    ##=============================================

    dnf_skyrim = _alert(
        level=HIGH,
        label="Skyrim not found",
        desc="The main Skyrim installation folder could not be found or is not defined.",
        fix="Choose an existing folder in the Preferences dialog.",
        check=lambda: not manager.get_directory(_dirs.SKYRIM))

    dnf_mods = _alert(
        level=HIGH,
        label="Mods Directory not found",
        desc="The mod installation directory could not be found or is not defined.",
        fix="Choose an existing folder in the Preferences dialog.",
        check=lambda: not manager.get_directory(_dirs.MODS)
    )

    dnf_vfs = _alert(
        level=HIGH,
        label="Virtual Filesystem mount not found",
        desc="The mount point for the virtual filesystem could not be found or is not defined.",
        fix="Choose an existing folder in the Preferences dialog.",
        check=lambda: not manager.get_directory(_dirs.VFS)
    )
