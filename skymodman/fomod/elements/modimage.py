from io import StringIO
from pprint import pprint

class ModImage:
    def __init__(self, path:str = "screenshot.png", show_image:bool = True, show_fade:bool = True, height:int = -1):
        self._path = path
        self._show_image = show_image
        self._show_fade = show_fade
        self._height = height

    @property
    def path(self) -> str:
        # TODO: should this be a "real" path? like os.path?
        return self._path

    @property
    def show_image(self) -> bool:
        return self._show_image

    @property
    def show_fade(self) -> bool:
        return self._show_fade


    @property
    def height(self) -> int:
        return self._height

    def __repr__(self):
        sio = StringIO()
        pprint(self.__dict__, sio)
        return sio.getvalue()