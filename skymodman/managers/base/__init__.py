"""Contains the generic bases for the managers used by the application.
These should contain no application-specific functionality."""

from .base_database import BaseDBManager
from .base_config import BaseConfigManager



class Submanager:
    """
    All sub-managers will be subclasses of this class and will be
    instantiated by the Main Manager.
    """

    def __init__(self, mcp, *args, **kwargs):
        """

        :param skymodman.managers.modmanager.ModManager mcp:
        """
        self.mainmanager = mcp
        super().__init__(*args, **kwargs)