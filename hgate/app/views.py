import os
import modhg
import settings
import app.modhg.usersb as users
from app.forms import RepositoryForm, CreateRepoForm, AddUser, EditUser, ManageGroupsForm
from app.modhg.HGWeb import HGWeb
from app.modhg.repository import get_absolute_repository_path
from django.core.urlresolvers import reverse
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.http import HttpResponseRedirect
from django.contrib import messages
from django.utils.translation import ugettext_lazy as _
from app.views_utils import add_amount_of_repos_to_groups, prepare_path, check_users_file, prepare_tree, check_configs_access, md5_for_file

#page handlers

def index(request):
    #todo try to make this method smaller
    if not check_configs_access(request):
        return render_to_response('errors.html', {"menu" : "home"}, context_instance=RequestContext(request))
    hgweb = HGWeb(settings.HGWEB_CONFIG)
    _tree = modhg.repository.get_tree(hgweb.get_paths_and_collections())
    tree = prepare_tree(_tree)
    groups = hgweb.get_groups()
    collections = zip(*hgweb.get_collections())[0]

    hgweb_cfg_hash = md5_for_file(settings.HGWEB_CONFIG)

    create_repo_form = CreateRepoForm(groups, hgweb_cfg_hash)
    groups_form = ManageGroupsForm(hgweb_cfg_hash)
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
                return HttpResponseRedirect('.')
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
                        redirect_path = "repo/" + name
                    else:
                        redirect_path = "repo/" + group + "/" + name
                except modhg.repository.RepositoryException as e:
                    messages.warning(request, str(e))
                    return HttpResponseRedirect('.')

                return HttpResponseRedirect(redirect_path)
        elif "delete_group" in request.POST:
            name = request.POST.get("group_name")
            path = dict(groups)[name]
            try:
                modhg.repository.delete_group(path, name)
                messages.success(request, _("Group '%s' was deleted successfully.") % name)
            except modhg.repository.RepositoryException as e:
                messages.warning(request, str(e))
            return HttpResponseRedirect('.')
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
                return HttpResponseRedirect('.')
            else:
                model["old_group_name"] = old_name
                model["old_group_path"] = old_path

    model["groups_form"] = groups_form
    model["edit_group_form"] = edit_group_form
    model["repo_form"] = create_repo_form

    return render_to_response('index.html', model, context_instance=RequestContext(request))
    
def hgrc_delete(request, parameter, repo_path):
    if not check_configs_access(request):
        return render_to_response('errors.html', {"menu" : "home"}, context_instance=RequestContext(request))
    full_repository_path = get_absolute_repository_path(repo_path)
    hgrc_path = os.path.join(full_repository_path, ".hg","hgrc")
    hgrc = HGWeb(hgrc_path, True)
    hgrc.del_web_key(parameter)
    return HttpResponseRedirect(reverse("repository", args=[repo_path]))

def repo(request, repo_path):
    if not check_configs_access(request):
        return render_to_response('errors.html',
                                  {"menu": (lambda is_global: {True: "hgweb", False: "repository"}[is_global])(
                                      repo_path == "")},
                                  context_instance=RequestContext(request))

    def check_access_local_hgrc(request, hgrc_path):
        hgdir = hgrc_path[:hgrc_path.rfind('/hgrc')]
        if (not os.access(hgrc_path, os.F_OK)) and (not os.access(hgdir, os.X_OK or os.R_OK or os.W_OK)):
            messages.error(request, _("No hgrc for this repository. No write access to create hgrc by path: ") + hgdir)
        elif os.access(hgrc_path, os.F_OK) and not os.access(hgrc_path, os.W_OK):
            messages.error(request, _("No access to write mercurial`s local configuration file by path: ") + hgrc_path)
        elif os.access(hgrc_path, os.F_OK) and not os.access(hgrc_path, os.R_OK):
            messages.warning(request, _("No access to read mercurial`s local configuration file by path: ") + hgrc_path)

    hgweb = HGWeb(settings.HGWEB_CONFIG)
    tree = prepare_tree(modhg.repository.get_tree(hgweb.get_paths_and_collections()))
    is_global = repo_path == ""
    hgrc = None
    form = None
    model = {"tree": tree, "global": is_global}
    if not is_global:
        try:
            model["repo_path"] = repo_path
            full_repository_path = get_absolute_repository_path(repo_path)
            hgrc_path = os.path.join(full_repository_path,".hg","hgrc")
            check_access_local_hgrc(request, hgrc_path)
            hgrc = HGWeb(hgrc_path, True)
            file_hash = md5_for_file(hgrc_path)
        except ValueError:
            hgrc = None
            file_hash = None
    else:
        file_hash = md5_for_file(settings.HGWEB_CONFIG)
    if request.method == 'POST':
        form = RepositoryForm(file_hash, request.POST)
        if form.is_valid():
            if is_global:
                form.export_values(hgweb, request.POST)
                messages.success(request, _("Global settings saved successfully."))
            else:
                form.export_values(hgrc, request.POST)
                messages.success(request, _("Repository settings saved successfully."))
    # re-set errors if any occurs in the is_valid method.
    errors = None
    if form is not None:
        errors = form._errors
    form = RepositoryForm(file_hash)
    form._errors = errors
    form.set_default(hgweb, hgrc)
    model["form"] = form
    return render_to_response('repository.html', model,
                              context_instance=RequestContext(request))

def user_index(request):
    if not check_configs_access(request):
        return render_to_response('errors.html', {"menu" : "users"}, context_instance=RequestContext(request))
    is_w_access = check_users_file(request)
    users_file_hash = md5_for_file(settings.AUTH_FILE)
    hgweb = HGWeb(settings.HGWEB_CONFIG)
    tree = prepare_tree(modhg.repository.get_tree(hgweb.get_paths_and_collections()))
    model = {"tree": tree}
    if request.method == "POST":
        form = AddUser(users_file_hash, request.POST)
        if form.is_valid() and is_w_access:
            login = form.cleaned_data['login']
            password = form.cleaned_data['password2']
            users.add(settings.AUTH_FILE, login, password)
            messages.success(request, _("User '%s' was added.") % login)
            form = AddUser(users_file_hash)
    else:
        form = AddUser(users_file_hash)
    user_list = users.login_list(settings.AUTH_FILE)
    model["form"] = form
    model["users"] = user_list
    return render_to_response("users.html", model,
                          context_instance=RequestContext(request))

def user(request, action, login):
    if not check_configs_access(request):
        return render_to_response('errors.html', {"menu" : "users"}, context_instance=RequestContext(request))

    users_file_hash = md5_for_file(settings.AUTH_FILE)
    hgweb = HGWeb(settings.HGWEB_CONFIG)
    tree = prepare_tree(modhg.repository.get_tree(hgweb.get_paths_and_collections()))
    model = {"tree": tree}
    is_w_access = check_users_file(request)
    if action == "delete":
        if is_w_access:
            users.remove(settings.AUTH_FILE, login)
            messages.success(request, _("User '%s' was deleted.") % login)
        return HttpResponseRedirect("../users") #todo: render via url
    elif action == "edit":
        # todo: check if login exists
        if request.method == "POST":
            form = EditUser(users_file_hash, request.POST)
            if form.is_valid() and is_w_access:
                password = form.cleaned_data['password2']
                users.update(settings.AUTH_FILE, login, password)
                messages.success(request, _("Password changed successfully."))
                form = EditUser(users_file_hash)
        else:
            form = EditUser(users_file_hash)
        model["form"] = form
        model["login"] = login
        model["permissions"] = users.permissions(login)
        return render_to_response("useredit.html", model,
                              context_instance=RequestContext(request))
