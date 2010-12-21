from ConfigParser import ConfigParser, NoOptionError
import os

__author__ = 'Shedar'

class HGWeb:
    """
    Global config management class
    """

    def __init__(self, path):
        """ @path: string path to hgweb.config file """
        if not os.path.exists(path):
            raise ValueError("Can't load main config file")
        self._file_name = path
        self._parser = ConfigParser()
        self._parser.read(path)

    def get_paths(self):
        return self._parser.items("paths")

    def get_groups(self):
        paths = self.get_paths()
        groups = []
        for path in paths:
            if path[1].endswith("*"):
                groups.append(path)
        return groups

    def get_path(self, key):
        try:
            return self._parser.get("paths", key)
        except NoOptionError:
            return None

    def add_paths(self, key, path):
        self._parser.set("paths", key, path)
        self._parser.write(open(self._file_name, "w"))

    def del_paths(self, key):
        self._parser.remove_option("paths", key)
        self._parser.write(open(self._file_name, "w"))

    def get_web(self):
        return self._parser.items("web")

    def get_web_key(self, key):
        try:
            return self._parser.get("web", key)
        except NoOptionError:
            return None

    def set_web_key(self, key, value):
        self._parser.set("web", key, value)
        self._parser.write(open(self._file_name, "w"))
