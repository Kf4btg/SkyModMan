

class Submanager:
    """
    All sub-managers will be subclasses of this class and will be
    instantiated by the Main Manager.
    """

    def __init__(self, mcp):
        """

        :param skymodman.managers.modmanager._ModManager mcp:
        """
        self.mainmanager = mcp

