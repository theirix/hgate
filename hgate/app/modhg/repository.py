import os
from mercurial import hg, ui
import shutil
from hgate.app.modhg.HGWeb import HGWeb
from hgate import settings
from django.utils.translation import ugettext_lazy as _


class RepositoryException(Exception):
    """
    Custom exception for repository module
    """
    pass


def delete_group(path, name, is_collection = False, delete_content = True):
    """
    Deletes group: deletes name from [paths] section of it is collection or from [collections] section;
    Also deletes directory tree py path.
    """
    hgweb = HGWeb(settings.HGWEB_CONFIG)
    try:
        if not is_collection:
            hgweb.del_paths(name) # may throw IOError
            path = path.rstrip('*')
        else:
            hgweb.del_collections(name) # may throw IOError
        if delete_content:
            shutil.rmtree(path) #, ignore_errors=True - to ignore any problem like "Permission denied".
            os.makedirs(path)
        # def onerror  function to hahdle errors or handle exception shutil.Error
    except (IOError, shutil.Error) as e:
        raise RepositoryException(_("There is a problem while deleting group: %s") % str(e))


def create_group(path, name, is_collection = False):
    hgweb = HGWeb(settings.HGWEB_CONFIG)
    groups = hgweb.get_groups()
    if not groups  or  not (
    name in zip(*groups)[0]): # zip(*groups)[0] - groups is a list of tuples, so unzip it and take list of keys
        try:
            if not is_collection:
                _path = path.rstrip('*')
                if not os.path.exists(_path):
                    os.makedirs(_path) #may be OSError
                hgweb.add_paths(name, path) #may be IOError
            else:
                if not os.path.exists(path):
                    os.makedirs(path) #may be OSError
                hgweb.add_collections(name, path) #may be IOError
        except (OSError, IOError) as e:
            raise RepositoryException("Error: %s" % str(e))
    else:
        raise RepositoryException(_("There is already a group with such a name."))


def create(path, name, has_no_group=False):
    """
    http://mercurial.selenic.com/wiki/MercurialApi#Repositories
    """
    if is_repository(path):
        raise RepositoryException(
            _("There is already such a repository.")) #make here something more informative or exception
    uio = ui.ui()
    try:
        hg.repository(uio, path, create=True)
    except Exception as e: #probably more specific exception is needed
        raise RepositoryException(
            _("Repository [%(path)s] is not created, because of error: %(cause)s") % {"path": path, "cause": str(e)})

    if has_no_group: #another one try-except block for this
        hgweb = HGWeb(settings.HGWEB_CONFIG)
        hgweb.add_paths(name, path)


def delete(path, item_name=""):
    """
    Deletes single repository with it directory tree.
    """
    if not is_repository(path):
        raise RepositoryException(_("There is no repository by path: [%s]") % path)
    try:
        shutil.rmtree(path) #, ignore_errors=True - to ignore any problem like "Permission denied"
    except (shutil.Error, OSError) as e: #probably more specific exception is needed
        raise RepositoryException(
            _("Failed to delete [%(path)s], because of error: %(cause)s") % {"path": path, "cause": str(e)})
    if item_name != "": # no group
        hgweb = HGWeb(settings.HGWEB_CONFIG)
        hgweb.del_paths(item_name)


def rename(old_path, new_path, old_item_name="", new_item_name=""):
    if not is_repository(old_path):
        raise RepositoryException(_("There is no repository by path: [%s]") % old_path)
    if os.path.exists(new_path) and not os.path.isdir(new_path):
        raise RepositoryException(_("There is file by path: [%s]") % new_path)
    elif os.path.exists(new_path) and not os.access(new_path, os.R_OK or os.W_OK):
        raise RepositoryException(_("There is no access rights by path: [%s]") % new_path)

    try:
        shutil.move(old_path, new_path)
    except (shutil.Error, OSError) as e:
        raise RepositoryException(
            _("Repository [%(old_path)s] is not moved to [%(new_path)s], because of error: %(cause)s") % {
                "old_path": old_path, "new_path": new_path, "cause": str(e)})
    if old_item_name != "": # no group
        hgweb = HGWeb(settings.HGWEB_CONFIG)
        hgweb.del_paths(old_item_name)
        hgweb.add_paths(new_item_name, new_path)


def is_repository(path):
    path = os.path.join(path, ".hg")
    return os.path.exists(path) and os.path.isdir(path)


def get_absolute_repository_path(key):
    """
    Resolves absolute path to repository. Waits 'key' or 'group_name/key'.
    """
    hgweb = HGWeb(settings.HGWEB_CONFIG)
    path = hgweb.get_path(key)
    if path:
        return path
    paths = hgweb.get_paths_and_collections()
    values = [key.replace(path_item, val.strip("*").rstrip("/"), 1)\
              for path_item, val in paths\
              if key == path_item or key.startswith(path_item)]
    if not len(values):
        raise RepositoryException(_("Invalid repository name."))
    return values[0]

def get_group(key):
    hgweb = HGWeb(settings.HGWEB_CONFIG)
    path = hgweb.get_path(key)
    if path:
        return "-"
    paths = hgweb.get_paths_and_collections()
    values = [path_item\
              for path_item, val in paths\
              if key == path_item or key.startswith(path_item)]
    if not len(values):
        raise RepositoryException(_("Invalid repository name."))
    return values[0]


def get_tree(paths, collections):
    tree = {}
    groups_tree = {}
    # handling paths
    for (name, path) in paths:
        if path.endswith("*"):
            groups_tree[name] = _scan(path, path.endswith("**"))
        else:
            if is_repository(path):
                tree[name.strip(os.sep)] = path
        # handling collections
    for (name, path) in collections:
        groups_tree[name] = _scan(path, True)
    groups_tree = sorted(groups_tree.items())
    tree = sorted(tree.items())
    return groups_tree + tree


def _scan(dir_path, deep):
    # todo if subdirectory contains dirs ended with '*' produced error.
    result = {}
    groups_tree = {}
    dir_path = dir_path.rstrip("*")
    if not os.path.exists(dir_path) or not os.path.isdir(dir_path):
        return result
    dir_list = os.listdir(dir_path)
    for current_dir in dir_list:
        path = os.path.join(dir_path, current_dir)
        if is_repository(path):
            result[current_dir] = current_dir
        elif deep:
            sub_tree = _scan(path, deep)
            if len(sub_tree) > 0:
                groups_tree[current_dir] = sub_tree
    groups_tree = sorted(groups_tree.items())
    result = sorted(result.items())
    return groups_tree + result
