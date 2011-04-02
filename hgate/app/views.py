import os
import modhg
import settings
import app.modhg.usersb as users
from app.forms import RepositoryForm, CreateRepoForm, AddUser, EditUser, ManageGroupsForm
from app.modhg.HGWeb import HGWeb
from app.modhg.repository import RepositoryException, get_absolute_repository_path
from django.core.urlresolvers import reverse
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.http import HttpResponseRedirect
from django.contrib import messages
from django.utils.translation import ugettext_lazy as _

#helper functions

def prepare_tree(tree, group=""):
    res = ""
    for (key, value) in tree:
        if isinstance(value, list):
            reps_in_group = len(value)
            res += "<li><span>%s (%d)</span><ul>%s</ul></li>" % (key, reps_in_group, prepare_tree(value, group + key + "/"))
        else:
             res += "<li><a href='%s'>%s</a></li>" % (reverse("repository", args=[group+key]), key)
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
    retVal = True
    if not os.access(settings.HGWEB_CONFIG, os.F_OK):
        messages.error(request, _("Main configuration file does not exist by specified path: ") + settings.HGWEB_CONFIG)
        retVal = False
    elif not os.access(settings.HGWEB_CONFIG, os.R_OK or os.W_OK):
        messages.error(request, _("No access to read or write mercurial`s global configuration file by path: ") + settings.HGWEB_CONFIG)
        retVal = False
    if not os.access(settings.REPOSITORIES_ROOT, os.F_OK):
        messages.error(request, _("Root directory of repositories does not exist by path: ") + settings.REPOSITORIES_ROOT)
        retVal = False
    elif not os.access(settings.REPOSITORIES_ROOT, os.R_OK or os.X_OK):
        messages.error(request, _("No read or execute access to the root directory of repositories by path: ") + settings.REPOSITORIES_ROOT)
        retVal = False
    return retVal

#page handlers

def index(request):
    #todo try to make this method smaller
    if not check_configs_access(request):
        return render_to_response('errors.html', {"menu" : "home"}, context_instance=RequestContext(request))
    hgweb = HGWeb(settings.HGWEB_CONFIG)
    _tree = modhg.repository.get_tree(hgweb.get_paths())
    tree = prepare_tree(_tree)
    groups = hgweb.get_groups()

    create_repo_form = CreateRepoForm(default_groups=groups)
    groups_form = ManageGroupsForm()
    edit_group_form_prefix="edit_group"
    edit_group_form = ManageGroupsForm(prefix=edit_group_form_prefix)
    
    model = {"tree": tree, "groups": add_amount_of_repos_to_groups(groups, _tree)}
    
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
                return HttpResponseRedirect('.')
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
                    return HttpResponseRedirect('.')

                return HttpResponseRedirect('./' + redirect_path)
        elif "delete_group" in request.POST:
            name = request.POST.get("group_name")
            path = dict(groups)[name]
            try:
                modhg.repository.delete_group(path, name)
                messages.success(request, _("Group '%s' was deleted successfully.") % name)
            except Exception as e:
                messages.warning(request, str(e))
            return HttpResponseRedirect('.')
        elif "old_group_name" in request.POST:
            edit_group_form = ManageGroupsForm(request.POST, prefix=edit_group_form_prefix)
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
                    except Exception as e:
                        messages.warning(request, str(e))
                elif name == old_name and path == old_path:
                    pass
                else:
                    messages.warning(request,
                                     _("There is already a group with such a name. Group '%s' wasn`t changed.") % old_name)
                return HttpResponseRedirect('.')
            else:
                model["edit_group_error_list"] = edit_group_form.errors

    model["groups_form"] = groups_form
    model["edit_group_form"] = edit_group_form
    model["repo_form"] = create_repo_form

    return render_to_response('index.html', model, context_instance=RequestContext(request))
    
def hgrc_delete(request, parameter, repo_path):
    repo_path = "/" + repo_path.strip("/")
    full_repository_path = get_absolute_repository_path(repo_path)
    hgrc_path = os.path.join(full_repository_path,".hg","hgrc")
    hgrc = HGWeb(hgrc_path, True)
    hgrc.del_web_key(parameter)
    return HttpResponseRedirect(reverse("repository", args=[repo_path]))

def repo(request, repo_path):
    if not check_configs_access(request):
        return render_to_response('errors.html',
                                  {"menu": (lambda is_global: {True: "hgweb", False: "repository"}[is_global])(
                                      repo_path == "")},
                                  context_instance=RequestContext(request))

    def check_access_local_hgrc(hgrc_path, request):
        hgdir = hgrc_path[:hgrc_path.rfind('/hgrc')]
        if (not os.access(hgrc_path, os.F_OK)) and (not os.access(hgdir, os.X_OK or os.R_OK or os.W_OK)):
            messages.error(request, _("No hgrc for this repository. No write access to create hgrc by path: ") + hgdir)
        elif not os.access(hgrc_path, os.W_OK):
            messages.error(request, _("No access to write mercurial`s local configuration file by path: ") + hgrc_path)
        elif not os.access(hgrc_path, os.R_OK):
            messages.warning(request, _("No access to read mercurial`s local configuration file by path: ") + hgrc_path)

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
            check_access_local_hgrc(hgrc_path, request)
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

def user_index(request, action=None, login=None):
    if not check_configs_access(request):
        return render_to_response('errors.html', {"menu" : "users"}, context_instance=RequestContext(request))
    hgweb = HGWeb(settings.HGWEB_CONFIG)
    tree = prepare_tree(modhg.repository.get_tree(hgweb.get_paths()))
    model = {"tree": tree}
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

def user(request, action, login):
    if not check_configs_access(request):
        return render_to_response('errors.html', {"menu" : "users"}, context_instance=RequestContext(request))
    def check_users_file(request):
        if not os.access(settings.AUTH_FILE, os.F_OK or os.R_OK):
            messages.error(request, _("No users file or no read access by path: ") + settings.AUTH_FILE)
        elif not os.access(settings.AUTH_FILE, os.W_OK):
            messages.warning(request, _("No no write access for users file by path: ") + settings.AUTH_FILE)

    check_users_file(request)
    
    hgweb = HGWeb(settings.HGWEB_CONFIG)
    tree = prepare_tree(modhg.repository.get_tree(hgweb.get_paths()))
    model = {"tree": tree}
    if action == "delete":
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
