import os
import settings
from django.contrib import messages
from django.core.urlresolvers import reverse
from django.utils.translation import ugettext_lazy as _

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


def prepare_path(name, group, groups):
    res = ""
    if group == "-":
        res = settings.REPOSITORIES_ROOT + os.path.sep + name
    else:
        for (gr_name, gr_path) in  groups:
            if gr_name == group:
                res = gr_path.replace("*", "") + name
                break
    return res


def add_amount_of_repos_to_groups(groups, tree):
    """
    groups is a list of tuples of (name, path) values. this function adds "count of repos in group" into each tuple.
     this method returns list of tuples of (name, path, count) values.
     @return [(name, path, count), ...]
    """
    counts = []
    if not groups: #no groups at all?
        names = []
        paths = []
    else:
        names, paths = zip(*groups)
    _tree = dict(tree)
    for name in names:
        counts.append(len(_tree[name]))
    return zip(names, paths, counts)


def check_configs_access(request):
    """
    checks existing and 'rwx' of next files:
    - root directory and 'rx';
    - global hg config and 'rw'.
    adds error message if any.
    @return False if any error, True if all ok
    """
    ret_val = True
    if not os.access(settings.HGWEB_CONFIG, os.F_OK):
        messages.error(request, _("Main configuration file does not exist by specified path: ") + settings.HGWEB_CONFIG)
        ret_val = False
    elif not os.access(settings.HGWEB_CONFIG, os.R_OK or os.W_OK):
        messages.error(request,
            _("No access to read or write mercurial`s global configuration file by path: ") + settings.HGWEB_CONFIG)
        ret_val = False
    if not os.access(settings.REPOSITORIES_ROOT, os.F_OK):
        messages.error(request,
            _("Root directory of repositories does not exist by path: ") + settings.REPOSITORIES_ROOT)
        ret_val = False
    elif not os.access(settings.REPOSITORIES_ROOT, os.R_OK or os.X_OK):
        messages.error(request,
            _("No read or execute access to the root directory of repositories by path: ") + settings.REPOSITORIES_ROOT)
        ret_val = False
    if not os.access(settings.AUTH_FILE, os.F_OK or os.R_OK):
        messages.error(request, _("No users file or no read access by path: ") + settings.AUTH_FILE)
        ret_val = False
    return ret_val


def check_users_file(request):
    ret_val = True
    if not os.access(settings.AUTH_FILE, os.W_OK):
        messages.warning(request, _("No write access for users file by path: ") + settings.AUTH_FILE)
        ret_val = False
    return ret_val

