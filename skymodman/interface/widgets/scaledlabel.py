from functools import lru_cache

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import QLabel

class ScaledLabel(QLabel):
    """
    A QLabel designed to be used to display QPixmaps. It always
    shows its pixmap contents scaled to its current size while
    preserving the original aspect ratio.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._pixmap = QPixmap(self.pixmap())
        self._scaled_cache_valid = False

    def setScaledPixmap(self, from_file):
        """
        load the image `from_file` into a QPixmap and save in the
        self._pixmap attribute. If the file has been loaded recently,
        a cached version will be used rather than reloading from disk.
        After loading, the pixmap is scaled to the current dimensions
        of the label and displayed.

        :param from_file:
        """
        self._pixmap = get_pixmap_from_file(from_file)

        # if there have been any resize events since we last
        # loaded a pixmap, clear the cached scale-results.
        if not self._scaled_cache_valid:
            self.scale_pixmap.cache_clear()
            self._scaled_cache_valid = True

        self.setPixmap(self.scale_pixmap(from_file))


    @lru_cache(8)
    def scale_pixmap(self, filename):
        """
        If there have been no resize events since the last time
        the pixmap for `filename` was shown, then (assuming it's
        still in the cache), this will returned the saved, already-
        scaled pixmap instead of recomputing it.

        :param filename:
        """
        return scale_pixmap(self._pixmap,
                            self.width(),
                            self.height())

    def resizeEvent(self, event):
        """
        This redraws the current image scaled to the label size.
        It also invalidates the cached results of previous scale
        operations so that loading a previous image will not
        show an image of the incorrect dimensions
        :param event:
        """
        self._scaled_cache_valid = False
        self.setPixmap(scale_pixmap(self._pixmap,
                                    self.width(),
                                    self.height()
                                    ))


def scale_pixmap(pixmap, width, height):
    return pixmap.scaled(width, height, Qt.KeepAspectRatio, Qt.SmoothTransformation)

@lru_cache(16)
def get_pixmap_from_file(file):
    """
    This uses an lru-cache to prevent reloading an image from disk
    if it has been recently loaded. Size is limited to 16 to prevent
    mods with many large images from devouring up RAM.
    :param file:
    """
    return QPixmap(file)
