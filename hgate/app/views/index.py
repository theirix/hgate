from hgate.app import modhg
from hgate.app.views.decorators import render_to, require_access
import hgate.settings as settings
from hgate.app.forms import CreateRepoForm, ManageGroupsForm, DeleteGroupForm
from hgate.app.modhg.HGWeb import HGWeb
from common import prepare_tree, md5_for_file
#from mercurial import scmutil, util

#page handlers
@render_to('index.html')
@require_access(menu='home')
def index(request):
    hgweb = HGWeb(settings.HGWEB_CONFIG)
    collections = hgweb.get_collections()
    _tree = modhg.repository.get_tree(hgweb.get_paths(), collections)
    tree = prepare_tree(_tree)
    groups = hgweb.get_groups()
    # unzipping collections
    unzipped_collections = zip(*hgweb.get_collections())
    if unzipped_collections:
        collection_names = unzipped_collections[0]
    else:
        collection_names = []
    hgweb_cfg_hash = md5_for_file(settings.HGWEB_CONFIG)
    create_repo_form = CreateRepoForm(groups, hgweb_cfg_hash)
    groups_form = ManageGroupsForm(hgweb_cfg_hash)
    delete_group_form = DeleteGroupForm(hgweb_cfg_hash)
    EDIT_GROUP_FORM_PREFIX = "edit_group"
    edit_group_form = ManageGroupsForm(hgweb_cfg_hash, prefix=EDIT_GROUP_FORM_PREFIX)

    model = {"tree": tree,
             "groups": _ext_groups_with_amount_of_repos_and_collection_flag(groups, collection_names, _tree),
             "default_path": settings.REPOSITORIES_ROOT}

    if request.method == 'POST':
        if "create_group" in request.POST:
            groups_form = ManageGroupsForm(hgweb_cfg_hash, request.POST)
            if groups_form.is_valid():
                return groups_form.create_group(request)
        elif "create_repo" in request.POST:
            create_repo_form = CreateRepoForm(groups, hgweb_cfg_hash, request.POST)
            if create_repo_form.is_valid():
                return create_repo_form.create_repository(request, groups)
        elif "delete_group" in request.POST:
            delete_group_form = DeleteGroupForm(hgweb_cfg_hash, request.POST)
            if delete_group_form.is_valid():
                return delete_group_form.delete_group(request, groups)
        elif "old_group_name" in request.POST: # edit group request
            edit_group_form = ManageGroupsForm(hgweb_cfg_hash, request.POST, prefix=EDIT_GROUP_FORM_PREFIX)
            if edit_group_form.is_valid():
                return edit_group_form.edit_group(request, groups, hgweb)
            else:
                old_name = request.POST.get("old_group_name")
                old_path = request.POST.get("old_group_path")
                model["old_group_name"] = old_name
                model["old_group_path"] = old_path

    model["groups_form"] = groups_form
    model["edit_group_form"] = edit_group_form
    model["repo_form"] = create_repo_form
    model["delete_group_form"] = delete_group_form

    return model

# helpers
def _ext_groups_with_amount_of_repos_and_collection_flag(groups, collection_names, tree):
    """
    groups is a list of tuples of (name, path) values. this function adds "count of repos in group" into each tuple.
     this method returns list of tuples of (name, path, count) values.
     @return [(name, path, count), ...]
    """
    counts = []
    is_collection_flags = []
    if not groups: #no groups at all?
        names = []
        paths = []
    else:
        names, paths = zip(*groups)
    _tree = dict(tree)
    for name in names:
        counts.append(len(_tree[name]))
        if name not in collection_names:
            is_collection_flags.append(False)
        else:
            is_collection_flags.append(True)

    return zip(names, paths, counts, is_collection_flags)

