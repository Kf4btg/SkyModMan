from PyQt5.QtWidgets import QWidget, QLabel, QProgressBar, QHBoxLayout, \
    QApplication
from PyQt5.QtCore import Qt, pyqtProperty, QTimer


class LabeledProgressBar(QWidget):

    def __init__(self,
                 label_text="Progress:",
                 label_font_size=10,
                 bar_width=100,
                 use_bar=None,
                 label_on_left=True,
                 show_bar_text=False,
                 *args, **kwargs):

        super().__init__(*args, **kwargs)

        if use_bar:
            self.bar = use_bar
        else:
            self.bar = QProgressBar(self)
        self.bar.reset()
        self.bar.setFixedWidth(bar_width)
        self.bar.setTextVisible(show_bar_text)

        self.label = QLabel(label_text, self)
        self.label.setAlignment(Qt.AlignRight)

        self.setStyleSheet("QLabel {font-size: %dpt}" % label_font_size)

        layout = QHBoxLayout()
        layout.setContentsMargins(0,0,0,0)

        if label_on_left:
            layout.addWidget(self.label)
            layout.addWidget(self.bar)
        else:
            layout.addWidget(self.bar)
            layout.addWidget(self.label)

        self.setLayout(layout)

    @pyqtProperty(int)
    def value(self):
        return self.bar.value()

    @value.setter
    def value(self, val):
        self.bar.setValue(val)

    def setValue(self, progress_value):
        self.bar.setValue(progress_value)

    @pyqtProperty(str)
    def label_text(self):
        return self.label.text()

    @label_text.setter
    def label_text(self, text):
        self.label.setText(text)





