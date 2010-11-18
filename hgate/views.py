from django.shortcuts import render_to_response
from django.template import RequestContext
from hgate.modhg.HGWeb import HGWeb
import settings
import modhg

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
    return render_to_response('index.html', {"tree": tree, "groups": groups},
                              context_instance=RequestContext(request))

def repo(request, repo_path):
    hgweb = HGWeb(settings.HGWEB_CONFIG)
    tree = prepare_tree(modhg.repository.get_tree(hgweb.get_paths()))

    return render_to_response('index.html', {"tree": tree, "repo_path": repo_path},
                              context_instance=RequestContext(request))
