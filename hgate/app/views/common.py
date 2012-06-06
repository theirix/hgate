import hashlib
import os
from django.core.urlresolvers import reverse
from hgate import settings

#helper functions

def prepare_tree(tree, group=""):
    res = ""
    for (key, value) in tree:
        if isinstance(value, list):
            reps_in_group = len(value)
            res += "<li><span>%s (%d)</span><ul>%s</ul></li>" % (
                key, reps_in_group, prepare_tree(value, group + key + "/"))
        else:
            res += "<li><a href='%s'>%s</a></li>" % (reverse("repository", args=[group + key]), key)
    return res


def md5_for_file(file_name, block_size=2 ** 20):
    f = open(file_name, "rb")
    md5 = hashlib.md5()
    while True:
        data = f.read(block_size)
        if not data:
            break
        md5.update(data)
    f.close()
    return md5.hexdigest()

def prepare_path(name, group, groups):
    """
    Resolves absolute path for a single repository or a repository in a group.
    """
    res = ""
    if group == "-":
        res = settings.REPOSITORIES_ROOT + os.path.sep + name
    else:
        for (gr_name, gr_path) in  groups:
            if gr_name == group:
                res = gr_path.replace("*", "")
                if not res.endswith(os.path.sep):
                    res += os.path.sep
                res += name
                break
    return res

