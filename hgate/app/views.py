import os
import modhg
import settings
import app.modhg.usersb as users
from app.forms import RepositoryForm, CreateRepoForm, AddUser, EditUser, ManageGroupsForm
from app.modhg.HGWeb import HGWeb
from app.modhg.repository import RepositoryException, get_absolute_repository_path
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.http import HttpResponseRedirect
from django.contrib import messages
from django.utils.translation import ugettext_lazy as _

def prepare_tree(tree, group=""):
    res = ""
    for (key, value) in tree:
        if isinstance(value, list):
            reps_in_group = len(value)
            res += "<li><span>%s (%d)</span><ul>%s</ul></li>" % (key, reps_in_group, prepare_tree(value, group + key + "/"))
        else:
             res += "<li><a href='/repo/%s%s'>%s</a></li>" % (group, key, key)
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


def index(request):
    hgweb = HGWeb(settings.HGWEB_CONFIG)
    _tree = modhg.repository.get_tree(hgweb.get_paths())
    tree = prepare_tree(_tree)
    groups = hgweb.get_groups()

    create_repo_form = CreateRepoForm(default_groups=groups)
    groups_form = ManageGroupsForm()
    edit_group_form_prefix="edit_group"
    edit_group_form = ManageGroupsForm(prefix=edit_group_form_prefix)
    
    model = {"tree": tree, "groups": add_amount_of_repos_to_groups(groups, _tree), "is_hide_edit_group_form": True}
    
    if request.method == 'POST':
        if "create_group" in request.POST:
            groups_form = ManageGroupsForm(request.POST)
            if groups_form.is_valid():
                name = groups_form.cleaned_data['name']
                path = groups_form.cleaned_data['path']
                try:
                    modhg.repository.create_group(path, name)
                    messages.success(request, _("New group was added."))
                except Exception as e:
                    messages.warning(request, str(e))
                return HttpResponseRedirect('/')
        elif "create_repo" in request.POST:
            create_repo_form = CreateRepoForm(groups, request.POST)
            if create_repo_form.is_valid():
                redirect_path = ""
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
                except Exception as e:
                    messages.warning(request, str(e))
                    return HttpResponseRedirect('/')

                return HttpResponseRedirect('/' + redirect_path)
        elif "delete_group" in request.POST:
            name = request.POST.get("group_name")
            path = dict(groups)[name]
            try:
                modhg.repository.delete_group(path, name)
                messages.success(request, _("Group '%s' was deleted successfully.") % name)
            except Exception as e:
                messages.warning(request, str(e))
            return HttpResponseRedirect('/')
        elif "edit_group" in request.POST  and ("old_group_name" in request.POST):
            edit_group_form = ManageGroupsForm(request.POST, prefix=edit_group_form_prefix)
            if edit_group_form.is_valid():
                name = edit_group_form.cleaned_data['name']
                path = edit_group_form.cleaned_data['path']
                old_name = request.POST.get("old_group_name")

                if old_name  == name or (not name in zip(*groups)[0]):
                    hgweb.del_paths(old_name)
                    try:
                        modhg.repository.create_group(path, name)
                        messages.success(request, _("Group '%s' was changed." % name))
                    except Exception as e:
                        messages.warning(request, str(e))
                else:
                    messages.warning(request,
                                     _("There is already a group with such a name. Group '%s' wasn`t changed.") % name)
                return HttpResponseRedirect('/')
            else:
                model["is_hide_edit_group_form"] = False
                model["edited_group"] = request.POST.get("old_group_name")

    model["groups_form"] = groups_form
    model["edit_group_form"] = edit_group_form
    model["repo_form"] = create_repo_form

    return render_to_response('index.html', model, context_instance=RequestContext(request))
    

def repo(request, repo_path):
    hgweb = HGWeb(settings.HGWEB_CONFIG)
    tree = prepare_tree(modhg.repository.get_tree(hgweb.get_paths()))
    is_global = repo_path == ""
    hgrc = None
    model = {"tree": tree, "global": is_global}
    if not is_global:
        try:
            repo_path = "/" + repo_path.strip("/")
            model["repo_path"] = repo_path
            full_repository_path = get_absolute_repository_path(repo_path)
            hgrc_path = os.path.join(full_repository_path,".hg","hgrc")
            hgrc = HGWeb(hgrc_path, True)
        except ValueError:
            hgrc = None
    if request.method == 'POST':
        form = RepositoryForm(request.POST)
        if form.is_valid():
            if is_global:
                form.export_values(hgweb, request.POST)
                messages.success(request, _("Global settings saved successfully."))
            else:
                form.export_values(hgrc, request.POST)
                messages.success(request, _("Repository settings saved successfully."))
    form = RepositoryForm()
    form.set_default(hgweb, hgrc)
    model["form"] = form
    return render_to_response('repository.html', model,
                              context_instance=RequestContext(request))

def user(request, action, login):
    hgweb = HGWeb(settings.HGWEB_CONFIG)
    tree = prepare_tree(modhg.repository.get_tree(hgweb.get_paths()))
    model = {"tree": tree}
    if not action: # main user page
        if request.method == "POST":
            form = AddUser(request.POST)
            if form.is_valid():
                login = form.cleaned_data['login']
                password = form.cleaned_data['password2']
                users.add(settings.AUTH_FILE, login, password)
                messages.success(request, _("User '%s' was added.") % login)
                form = AddUser()
        else:
            form = AddUser()
        user_list = users.list(settings.AUTH_FILE)
        model["form"] = form
        model["users"] = user_list
        return render_to_response("users.html", model,
                              context_instance=RequestContext(request))
    elif action == "delete":
        users.remove(settings.AUTH_FILE,login)
        messages.success(request, _("User '%s' was deleted.") % login)
        return HttpResponseRedirect("../users") #todo: render via url
    elif action == "edit":
        # todo: check if login exists
        if request.method == "POST":
            form = EditUser(request.POST)
            if form.is_valid():
                password = form.cleaned_data['password2']
                users.update(settings.AUTH_FILE, login, password)
                messages.success(request, _("Password changed successfully."))
                form = EditUser()
        else:
            form = EditUser()
        model["form"] = form
        model["login"] = login
        model["permissions"] = users.permissions(login)
        return render_to_response("useredit.html", model,
                              context_instance=RequestContext(request))
