from django.shortcuts import render_to_response
from django.template import RequestContext
from app.forms import RepositoryForm, CreateRepoForm
from app.modhg.HGWeb import HGWeb
import settings
import modhg
#from django.http import HttpResponseRedirect

def prepare_tree(tree, group=""):
    res = ""
    for (key, value) in tree.iteritems():
        if isinstance(value, dict):
            res += "<li><span>" + key + "</span><ul>" + prepare_tree(value, group+key+"/") + "</ul></li>"
        else:
            res += "<li><a href='/repo/"+group+key+"'>" + key + "</a></li>"
    return res

def index(request):
    hgweb = HGWeb(settings.HGWEB_CONFIG)
    tree = prepare_tree(modhg.repository.get_tree(hgweb.get_paths()))
    groups = hgweb.get_groups()

    create_repo_form = CreateRepoForm(groups = groups)

    return render_to_response('index.html', {"tree": tree, "repo_form": create_repo_form},
                              context_instance=RequestContext(request))

def repo(request, repo_path):
    hgweb = HGWeb(settings.HGWEB_CONFIG)
    tree = prepare_tree(modhg.repository.get_tree(hgweb.get_paths()))

    model = {"tree": tree, "repo_path": repo_path}

    if request.method == 'POST':
        form = RepositoryForm(request.POST)
        if form.is_valid():
            True #            return HttpResponseRedirect('index')
    else:
        form = RepositoryForm()
        model["form"] = form

    return render_to_response('form.html', model,
                              context_instance=RequestContext(request))
