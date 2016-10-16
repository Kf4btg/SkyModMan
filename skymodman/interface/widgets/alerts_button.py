from PyQt5 import QtWidgets, QtGui
from PyQt5.QtWidgets import QTreeWidgetItem, QLabel
from PyQt5.QtCore import Qt


class AlertsButton(QtWidgets.QToolButton):
    """Contains the functionality for the button on the main window
    which shows a menu containing the active alerts (errors) that the
    user should be aware of"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # noinspection PyTypeChecker,PyArgumentList
        self.setIcon(
            QtGui.QIcon.fromTheme("dialog-warning"))
        self.setText("Alerts")
        self.setToolButtonStyle(Qt.ToolButtonFollowStyle)
        self.setToolTip("View Alerts")
        self.setStatusTip(
            "There are issues which require your attention!")
        self.setPopupMode(
            QtWidgets.QToolButton.InstantPopup)

        # create a menu to hold the widget
        self.setMenu(QtWidgets.QMenu(self))

        self.view_widget = self._setup_widget()
        self.view_widget.setObjectName("alerts_view_widget")

        # create the action that contains the popup
        self.show_popup_action = QtWidgets.QWidgetAction(self)

        # set popup view as default widget
        self.show_popup_action.setDefaultWidget(self.view_widget)

        # add the action to the menu of the alerts button;
        # this causes the "menu" to consist wholly of the display widget
        self.menu().addAction(self.show_popup_action)

    def _setup_widget(self):
        vw = QtWidgets.QTreeWidget(self)
        # AbstractItemView.SelectionMode.NoSelection == 0
        vw.setSelectionMode(0)
        vw.setMinimumWidth(400)
        vw.setColumnCount(2)
        vw.setHeaderHidden(True)

        # hide the sub-itembranches that don't line up correctly with the
        # top-aligned labels (note:: setting background: transparent
        # on every ::branch makes the expansion arrow disappear
        # for some reason. There may be a better way around that, but
        # this is acceptable for now)
        vw.setStyleSheet(
            """
            QTreeWidget::branch:!has-children {
                background: transparent;
            }
            """
        )

        # accessing the static property via the instance cause it's easy
        vw.setSizeAdjustPolicy(vw.AdjustToContents)

        return vw

    def clear_widget(self):
        """Clear the contained alerts"""
        self.view_widget.clear()

    def update_widget(self, alert_list):
        """Pass the set of alerts from the main manager to update
        what is shown in the drop-down menu"""

        # get a bold font to use for labels
        bfont = QtGui.QFont()
        bfont.setBold(True)
        for a in sorted(alert_list, key=lambda al: al.label):
            # the label/title as top-level item
            alert_title = QTreeWidgetItem(self.view_widget,
                                          [a.label])
            alert_title.setFirstColumnSpanned(True)

            # underneath the label, one can expand the item
            # to view the description and suggested fix
            desc = QTreeWidgetItem(alert_title, ["Desc:"])
            desc.setFont(0, bfont)
            desc.setTextAlignment(0, Qt.AlignTop)

            ## some QLabel shenanigans to work around the lack of
            ## word wrap in QTreeWidget

            # -F-I-X-M-E-: the label still only seems to 2 lines of
            # text at most; a long-ish description can have its last
            # few words cut off, depending on font size and width of
            # the menu widget.
            # ...update: setting the text interaction flags to
            #    TextSelectableByMouse makes all the text visible...
            #    and adds a bunch of empty space at the bottom of the
            #    label. Just can't win.
            lbl_desc = QLabel(a.desc)
            lbl_desc.setWordWrap(True)
            lbl_desc.setAlignment(Qt.AlignTop)
            lbl_desc.setTextInteractionFlags(Qt.TextSelectableByMouse)
            self.view_widget.setItemWidget(desc, 1, lbl_desc)

            # ditto
            fix = QTreeWidgetItem(alert_title, ["Fix:"])
            fix.setTextAlignment(0, Qt.AlignTop)
            fix.setFont(0, bfont)

            lbl_fix = QLabel(a.fix)
            lbl_fix.setWordWrap(True)
            lbl_fix.setAlignment(Qt.AlignTop)
            lbl_fix.setTextInteractionFlags(Qt.TextSelectableByMouse)

            self.view_widget.setItemWidget(fix, 1, lbl_fix)
            alert_title.setExpanded(True)

    def adjust_display_size(self):
        """AFTER the action for this button has been made visible,
        adjust the display dimensions of the menu and widget"""

        # adjust size of display treewidget and containing menu;
        # have to set both Min and Max on the menu to get it to
        # resize correctly
        self.view_widget.adjustSize()
        h = self.view_widget.size().height()
        m = self.menu()
        m.setMinimumHeight(h)
        m.setMaximumHeight(h)