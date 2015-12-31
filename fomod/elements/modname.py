from ..enums import Position
from io import StringIO
from pprint import pprint

class ModName:
    def __init__(self, name:str, position: Position = Position.LEFT, color: str= "000000"):
        """
        :param name: The name of this mod
        :param position: valid values are: Left, Right, RightOfImage
        :param color: string representation of a 6-digit RRGGBB color value
        """
        self._name = name
        self._position = position
        self._color = color

    @property
    def name(self) -> str:
        return self._name

    @property
    def position(self) -> Position:
        return self._position

    @property
    def color(self) -> str:
        return self._color

    def __repr__(self):
        sio = StringIO()
        pprint(self.__dict__, sio)
        return sio.getvalue()