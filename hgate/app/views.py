from django.shortcuts import render_to_response
from django.template import RequestContext
from app.forms import RepositoryForm, CreateRepoForm
from app.modhg.HGWeb import HGWeb
import settings
import modhg
from django.http import HttpResponseRedirect
import os

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
            name = create_repo_form.cleaned_data['name']
            group = create_repo_form.cleaned_data['group']
            repo_path = prepare_path(name, group, groups)
            is_created = modhg.repository.create(repo_path)
            if(is_created):
                if(group == "-"):
                    hgweb.add_paths(name, repo_path)
                    redirect_path = "repo/" + name
                else:
                    redirect_path = "repo/" + group + "/" + name
            return HttpResponseRedirect('/' + redirect_path)
    else:
        create_repo_form = CreateRepoForm(default_groups=groups)

    return render_to_response('index.html', {"tree": tree, "repo_form": create_repo_form},
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
