from collections import namedtuple

# db_fields = ["ordinal", "directory", "name", "modid", "version", "enabled"]

ModEntry = namedtuple("ModEntry", ['enabled', 'name', 'modid', 'version', 'directory', 'ordinal'])