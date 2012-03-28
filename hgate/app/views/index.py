import os
from hgate.app import modhg
from hgate.app.views.decorators import render_to, require_access
import hgate.settings as settings
from hgate.app.forms import CreateRepoForm, ManageGroupsForm, FileHashForm
from hgate.app.modhg.HGWeb import HGWeb
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.contrib import messages
from django.utils.translation import ugettext_lazy as _
from common import prepare_tree, md5_for_file

__author__ = 'hawaiian'

#page handlers
@render_to('index.html')
@require_access(menu='home')
def index(request):
    hgweb = HGWeb(settings.HGWEB_CONFIG)
    _tree = modhg.repository.get_tree(hgweb.get_paths_and_collections())
    tree = prepare_tree(_tree)
    groups = hgweb.get_groups()
    # unzipping collections
    unzipped_collections = zip(*hgweb.get_collections())
    if unzipped_collections:
        collections = unzipped_collections[0]
    else:
        collections = []
    hgweb_cfg_hash = md5_for_file(settings.HGWEB_CONFIG)

    create_repo_form = CreateRepoForm(groups, hgweb_cfg_hash)
    groups_form = ManageGroupsForm(hgweb_cfg_hash)
    delete_group_form = FileHashForm(hgweb_cfg_hash)
    edit_group_form_prefix = "edit_group"
    edit_group_form = ManageGroupsForm(hgweb_cfg_hash, prefix=edit_group_form_prefix)

    model = {"tree": tree, "groups": add_amount_of_repos_to_groups(groups, _tree),
             "collections": collections}

    if request.method == 'POST':
        if "create_group" in request.POST:
            groups_form = ManageGroupsForm(hgweb_cfg_hash, request.POST)
            if groups_form.is_valid():
                name = groups_form.cleaned_data['name']
                path = groups_form.cleaned_data['path']
                try:
                    modhg.repository.create_group(path, name)
                    messages.success(request, _("New group was added."))
                except modhg.repository.RepositoryException as e:
                    messages.warning(request, _("Group was not created: %s" % str(e)) )
                return HttpResponseRedirect(reverse('index'))
        elif "create_repo" in request.POST:
            create_repo_form = CreateRepoForm(groups, hgweb_cfg_hash, request.POST)
            if create_repo_form.is_valid():
                name = create_repo_form.cleaned_data['name']
                group = create_repo_form.cleaned_data['group']
                repo_path = prepare_path(name, group, groups)
                try:
                    modhg.repository.create(repo_path, name, group == "-")
                    messages.success(request, _("New repository was created."))
                    if group == "-":
                        redirect_path = reverse("repository", args=[name])
                    else:
                        redirect_path = reverse("repository", args=[group + os.path.sep + name])
                except modhg.repository.RepositoryException as e:
                    messages.warning(request, str(e))
                    return HttpResponseRedirect(reverse('index'))

                return HttpResponseRedirect(redirect_path)
        elif "delete_group" in request.POST:
            delete_group_form = FileHashForm(hgweb_cfg_hash, request.POST)
            if delete_group_form.is_valid():
                name = request.POST.get("group_name")
                path = dict(groups)[name]
                try:
                    modhg.repository.delete_group(path, name)
                    messages.success(request, _("Group '%s' was deleted successfully.") % name)
                except modhg.repository.RepositoryException as e:
                    messages.warning(request, str(e))
                return HttpResponseRedirect(reverse('index'))
        elif "old_group_name" in request.POST: # edit group request
            edit_group_form = ManageGroupsForm(hgweb_cfg_hash, request.POST, prefix=edit_group_form_prefix)
            old_name = request.POST.get("old_group_name")
            old_path = request.POST.get("old_group_path")
            if edit_group_form.is_valid():
                name = edit_group_form.cleaned_data['name']
                path = edit_group_form.cleaned_data['path']
                if (old_name != name and name not in zip(*groups)[0]) or (name == old_name and path != old_path):
                    hgweb.del_paths(old_name)
                    try:
                        modhg.repository.create_group(path, name)
                        messages.success(request, _("Group '%s' was changed." % old_name))
                    except modhg.repository.RepositoryException as e:
                        messages.warning(request, str(e))
                elif name == old_name and path == old_path:
                    pass#do nothing
                else:
                    messages.warning(request,
                        _("There is already a group with such a name. Group '%s' wasn`t changed.") % old_name)
                return HttpResponseRedirect(reverse('index'))
            else:
                model["old_group_name"] = old_name
                model["old_group_path"] = old_path

    model["groups_form"] = groups_form
    model["edit_group_form"] = edit_group_form
    model["repo_form"] = create_repo_form
    model["delete_group_form"] = delete_group_form

    return model

# helpers

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
