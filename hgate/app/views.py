from django.shortcuts import render_to_response
from django.template import RequestContext
from app.forms import RepositoryForm, CreateRepoForm
from app.modhg.HGWeb import HGWeb
import settings
import modhg
from django.http import HttpResponseRedirect
import os
from django.contrib import messages
from hgate.app.modhg.repository import RepositoryException
from hgate.app.forms import ManageGroupsForm

def prepare_tree(tree, group=""):
    res = ""
    for (key, value) in tree.iteritems():
        if isinstance(value, dict):
            res += "<li><span>" + key + "</span><ul>" + prepare_tree(value, group + key + "/") + "</ul></li>"
        else:
            res += "<li><a href='/repo/" + group + key + "'>" + key + "</a></li>"
    return res

def prepare_path(name, group, groups):
    res = ""
    if(group == "-"):
        res = settings.REPOSITORIES_ROOT + os.path.sep + name
    else:
        for (gr_name, gr_path) in  groups:
            if(gr_name == group):
                res = gr_path.replace("*", "") + name
                break

    return res

def index(request):
    hgweb = HGWeb(settings.HGWEB_CONFIG)
    tree = prepare_tree(modhg.repository.get_tree(hgweb.get_paths()))
    groups = hgweb.get_groups()

    if request.method == 'POST':
        create_repo_form = CreateRepoForm(groups, request.POST)
        if create_repo_form.is_valid():
            redirect_path = ""
            name = create_repo_form.cleaned_data['repo_name']
            group = create_repo_form.cleaned_data['repo_group']
            repo_path = prepare_path(name, group, groups)
            try:
                modhg.repository.create(repo_path, name, group == "-")
                messages.success(request, 'New repository was created.')
                if(group == "-"):
                    redirect_path = "repo/" + name
                else:
                    redirect_path = "repo/" + group + "/" + name
            except RepositoryException as e:
                messages.warning(request, e.message)

            return HttpResponseRedirect('/' + redirect_path)
    else:
        create_repo_form = CreateRepoForm(default_groups=groups)

    groups_form = ManageGroupsForm()

    return render_to_response('index.html', {"tree": tree, "repo_form": create_repo_form, "groups_form": groups_form,
                                             "groups": groups},
                              context_instance=RequestContext(request))

def repo(request, repo_path):
    hgweb = HGWeb(settings.HGWEB_CONFIG)
    tree = prepare_tree(modhg.repository.get_tree(hgweb.get_paths()))

    model = {"tree": tree, "repo_path": repo_path}

    if request.method == 'POST':
        form = RepositoryForm(request.POST)
        if form.is_valid():
            return HttpResponseRedirect('/')
    else:
        form = RepositoryForm()
        model["form"] = form

    return render_to_response('form.html', model,
                              context_instance=RequestContext(request))
