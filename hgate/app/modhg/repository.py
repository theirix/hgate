import os
from mercurial import hg,ui
__author__ = 'Shedar'

def create(path):
    """
    http://mercurial.selenic.com/wiki/MercurialApi#Repositories
    """
    if(is_repository(path)):
        return False #make here something more informative or exception
    if(not os.path.exists(path)):
        os.makedirs(path) #check if this is necessary
    uio = ui.ui()
    hg.repository(uio, path, create=True)
#    raise NotImplementedError()

def delete(path):
    raise NotImplementedError()

def rename(old_path, new_path):
    raise NotImplementedError()

def is_repository(path):
    path = os.path.join(path,".hg")
    return os.path.exists(path) and os.path.isdir(path)

def get_tree(paths):
    tree = {}
    for (name, path) in paths:
        if path.endswith("*"):
            tree[name] = _scan(path, path.endswith("*"))
        else:
            if is_repository(path):
                tree[name.strip(os.sep)] = path
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
    return result
