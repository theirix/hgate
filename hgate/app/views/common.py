import hashlib
from django.core.urlresolvers import reverse

__author__ = 'hawaiian'

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

