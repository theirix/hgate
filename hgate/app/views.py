import os
from hgate.app.forms import FileHashForm
import modhg
import settings
import app.modhg.usersb as users
from app.forms import RepositoryForm, CreateRepoForm, AddUser, EditUser, ManageGroupsForm, FileHashForm
from app.modhg.HGWeb import HGWeb
from app.modhg.repository import get_absolute_repository_path
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.contrib import messages
from django.utils.translation import ugettext_lazy as _
from app.views_utils import check_access_local_hgrc, add_amount_of_repos_to_groups, prepare_path, check_users_file, prepare_tree, check_configs_access, md5_for_file, render_to, require_access

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
                    messages.warning(request, str(e))
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

@render_to('repository.html')
@require_access(menu='hgweb')
def hgweb(request):
    return _repo(request)

@render_to('repository.html')
@require_access(menu='repository')
def repo(request, repo_path):
    return _repo(request, repo_path)

def _repo(request, repo_path=""):
    hgweb = HGWeb(settings.HGWEB_CONFIG)
    tree = prepare_tree(modhg.repository.get_tree(hgweb.get_paths_and_collections()))
    is_global = repo_path == ""
    hgrc = None
    form = None
    hgrc_path = None
    model = {"tree": tree, "global": is_global}
    if not is_global:
        try:
            model["repo_path"] = repo_path
            full_repository_path = get_absolute_repository_path(repo_path)
            hgrc_path = os.path.join(full_repository_path, ".hg", "hgrc")
            check_access_local_hgrc(request, hgrc_path)
            hgrc = HGWeb(hgrc_path, True)
            file_hash = md5_for_file(hgrc_path)
        except ValueError:
            hgrc = None
            file_hash = None
    else:
        file_hash = md5_for_file(settings.HGWEB_CONFIG)

    repo_field_delete_form = FileHashForm(file_hash)

    if request.method == 'POST':
        if 'save' in request.POST:
            form = RepositoryForm(file_hash, request.POST)
            if form.is_valid():
                if is_global:
                    form.export_values(hgweb, request.POST)
                    file_hash = md5_for_file(settings.HGWEB_CONFIG)
                    messages.success(request, _("Global settings saved successfully."))
                else:
                    form.export_values(hgrc, request.POST)
                    file_hash = md5_for_file(hgrc_path)
                    repo_field_delete_form = FileHashForm(file_hash)
                    messages.success(request, _("Repository settings saved successfully."))
        elif 'delete_field' in request.POST and hgrc is not None:
            if request.method == 'POST':
                repo_field_delete_form = FileHashForm(file_hash, request.POST)
                if repo_field_delete_form.is_valid():
                    parameter = request.POST.get('parameter')
                    print parameter
                    hgrc.del_web_key(parameter)
                    return HttpResponseRedirect(reverse("repository", args=[repo_path]))
    # re-set errors if any occurs in the is_valid method.
    errors = None
    if form is not None:
        errors = form._errors
    form = RepositoryForm(file_hash)
    form._errors = errors
    form.set_default(hgweb, hgrc)

    model["form"] = form
    model["repo_field_delete_form"] = repo_field_delete_form
    return model


@render_to('users.html')
@require_access(menu='users')
def user_index(request):
    is_w_access = check_users_file(request)
    users_file_hash = md5_for_file(settings.AUTH_FILE)
    form = AddUser(users_file_hash)
    delete_user_form = FileHashForm(users_file_hash)
    hgweb = HGWeb(settings.HGWEB_CONFIG)
    tree = prepare_tree(modhg.repository.get_tree(hgweb.get_paths_and_collections()))
    model = {"tree": tree}
    if request.method == "POST":
        if "delete_user" in request.POST:
            delete_user_form = FileHashForm(users_file_hash, request.POST)
            if delete_user_form.is_valid() and is_w_access:
                login = request.POST.get("login")
                users.remove(settings.AUTH_FILE, login)
                messages.success(request, _("User '%s' was deleted.") % login)
                return HttpResponseRedirect(reverse('users_index'))
        elif "add_user" in request.POST:
            form = AddUser(users_file_hash, request.POST)
            if form.is_valid() and is_w_access:
                login = form.cleaned_data['login']
                password = form.cleaned_data['password2']
                users.add(settings.AUTH_FILE, login, password)
                messages.success(request, _("User '%s' was added.") % login)
                return HttpResponseRedirect(reverse('users_index'))
    user_list = users.login_list(settings.AUTH_FILE)
    model["delete_user_form"] = delete_user_form
    model["form"] = form
    model["users"] = user_list
    return model


@render_to('useredit.html')
@require_access(menu='users')
def user(request, action, login):
    users_file_hash = md5_for_file(settings.AUTH_FILE)
    hgweb = HGWeb(settings.HGWEB_CONFIG)
    tree = prepare_tree(modhg.repository.get_tree(hgweb.get_paths_and_collections()))
    model = {"tree": tree}
    is_w_access = check_users_file(request)
    if action == "edit":
        # todo: check if login exists
        if request.method == "POST":
            form = EditUser(users_file_hash, request.POST)
            if form.is_valid() and is_w_access:
                password = form.cleaned_data['password2']
                users.update(settings.AUTH_FILE, login, password)
                messages.success(request, _("Password changed successfully."))
                return HttpResponseRedirect(reverse('users:action:login', kwargs={'action': action, "login": login}))
        else:
            form = EditUser(users_file_hash)
        model["form"] = form
        model["login"] = login
        model["permissions"] = users.permissions(login)
        return model
