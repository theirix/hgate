from ConfigParser import ConfigParser, NoOptionError, NoSectionError
import os

__author__ = 'Shedar'

class HGWeb:
    """
    Global config management class
    """

    def __init__(self, path, create = False):
        """ @path: string path to hgweb.config file """
        if not os.path.exists(path):
            if not create:
                raise ValueError("Can't load config file")
            else:
                try:
                    f = open(path, "w")
                    f.close()
                except IOError:
                    raise ValueError("Can't create config file")
        self._file_name = path
        self._parser = ConfigParser()
        self._parser.read(path)

    def get_paths_and_collections(self):
        """finds all paths from section [paths] and paths with appended /** from section [collection]"""
        ret_val = self.get_paths() + self.get_collections()

        return ret_val

    def get_paths(self):
        """ finds all paths from section [paths] """
        if self._parser.has_section("paths"):
            return self._parser.items("paths")
        else :
            return []

    def get_collections(self):
        if self._parser.has_section("collections"):
            # todo: this exposes collections as paths with /** suffix. simple support of collections.
            collections = self._parser.items("collections")
            collections = [ (name, path + "/**") for name, path in collections]
            return collections
        else :
            return []

    def get_groups(self):
        paths = self.get_paths()
        groups = []
        for path in paths:
            if path[1].endswith("*"):
                groups.append(path)
        groups = sorted(groups)
        return groups + self.get_collections()

    def get_path(self, key):
        try:
            return self._parser.get("paths", key)
        except (NoOptionError, NoSectionError):
            return None

    def add_paths(self, key, path):
        if "paths" not in self._parser.sections():
            self._parser.add_section("paths")
        self._parser.set("paths", key, path)
        self._parser.write(open(self._file_name, "w"))

    def del_paths(self, key):
        self._parser.remove_option("paths", key)
        self._parser.write(open(self._file_name, "w"))

    def get_web(self):
        try:
            return self._parser.items("web")
        except (NoOptionError, NoSectionError):
            return None

    def get_web_key(self, key):
        try:
            return self._parser.get("web", key)
        except (NoOptionError, NoSectionError):
            return None

    def set_web_key(self, key, value):
        if "web" not in self._parser.sections():
            self._parser.add_section("web")
        self._parser.set("web", key, value)
        self._parser.write(open(self._file_name, "w"))

    def del_web_key(self, key):
        self._parser.remove_option("web", key)
        self._parser.write(open(self._file_name, "w"))

