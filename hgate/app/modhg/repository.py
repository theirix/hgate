import os
from mercurial import hg,ui
import shutil
from app.modhg.HGWeb import HGWeb
import settings

__author__ = 'Shedar'


class RepositoryException(Exception):
    """
    Custom exception for repository module
    """
    pass

def delete_group(path, name):
    hgweb = HGWeb(settings.HGWEB_CONFIG)
    try:
        hgweb.del_paths(name)
        shutil.rmtree(path.rstrip('*')) #, ignore_errors=True - to ignore any problem like "Permission denied"
    except Exception as e:
        raise RepositoryException("There is a problem while deleting the group: %s" % str(e))

def create_group(path, name):
    hgweb = HGWeb(settings.HGWEB_CONFIG)
    groups = hgweb.get_groups()
    if not groups  or  not (name in zip(*groups)[0]): # zip(*groups)[0] - groups is a list of tuples, so unzip it and take list of keys
        try:
            _path = path.rstrip('*')
            if not os.path.exists(_path):
                os.makedirs(_path)
            hgweb.add_paths(name, path)
        except Exception as e: #probably more specific exception is needed
            raise RepositoryException("Group wasn`t created because of error: %s" % str(e) )
    else:
        raise RepositoryException("There is already a group with such a name. Group wasn`t created")


def create(path, name="", has_no_group=False):
    """
    http://mercurial.selenic.com/wiki/MercurialApi#Repositories
    """
    if is_repository(path):
        raise RepositoryException("There is already such repository.") #make here something more informative or exception
    uio = ui.ui()
    try:
        hg.repository(uio, path, create=True)
    except Exception as e: #probably more specific exception is needed
        raise RepositoryException("Repository [%s] is not created, because of error: %s" % (path, str(e)))

    if has_no_group: #another one try-except block for this
        hgweb = HGWeb(settings.HGWEB_CONFIG)
        hgweb.add_paths(name, path)

def delete(path, name="", has_no_group=False):
    if not is_repository(path):
        raise RepositoryException("There is no repository by path: [%s]" % (path, ) )
    try:
        shutil.rmtree(path) #, ignore_errors=True - to ignore any problem like "Permission denied"
    except Exception as e: #probably more specific exception is needed
        raise RepositoryException("Repository [%s] is not removed, because of error: %s" % (path, str(e)))
    if has_no_group:
        hgweb = HGWeb(settings.HGWEB_CONFIG)
        hgweb.del_paths(name)

def rename(old_path, new_path, name="", has_no_group=False):
    if not is_repository(old_path):
        raise RepositoryException("There is no repository by path: [%s]" % (old_path, ))
    try:
        shutil.move(old_path, new_path)
    except Exception as e: #probably more specific exception is needed
        raise RepositoryException("Repository [%s] is not moved to [%s], because of error: %s" % (old_path, new_path, str(e)))
    if has_no_group:
        hgweb = HGWeb(settings.HGWEB_CONFIG)
        hgweb.del_paths(name)
        hgweb.add_paths(name, new_path)

def is_repository(path):
    path = os.path.join(path,".hg")
    return os.path.exists(path) and os.path.isdir(path)

def get_absolute_repository_path(key):
    hgweb = HGWeb(settings.HGWEB_CONFIG)
    path = hgweb.get_path(key)
    if path:
        return path
    paths = hgweb.get_paths()
    repo_key = key.lstrip("/")
    values = [key.replace(path_item, val.strip("*").rstrip("/"), 1) \
              for path_item, val in paths \
              if repo_key == path_item or repo_key.startswith(path_item.strip("/")+"/")]
    if len(values) == 0:
        raise RepositoryException("Invalid repository name.")
    return values[0]

def get_tree(paths):
    tree = {}
    for (name, path) in paths:
        if path.endswith("*"):
            tree[name] = _scan(path, path.endswith("**"))
        else:
            if is_repository(path):
                tree[name.strip(os.sep)] = path
    tree = sorted(tree.items())
    return tree

def _scan(dir, deep):
    result = {}
    dir = dir.rstrip("*")
    if not os.path.exists(dir):
        return result
    dir_list = os.listdir(dir)
    for current_dir in dir_list:
        path = os.path.join(dir, current_dir)
        if is_repository(path):
            result[current_dir] = current_dir
        elif deep:
            sub_tree = _scan(path, deep)
            if len(sub_tree) > 0:
                result[current_dir] = sub_tree
    result = sorted(result.items())
    return result
