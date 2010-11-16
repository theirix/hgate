from django.shortcuts import render_to_response
from django.template import RequestContext
from hgate.modhg.HGWeb import HGWeb
import settings
import modhg

def prepare_tree(tree):
    res = ""
    for (key, value) in tree.iteritems():
        if isinstance(value,dict):
            res += "<li><span>"+key+"</span><ul>"+prepare_tree(value)+"</ul></li>"
        else:
            res+="<li>"+key+"</li>"
    return res

def index(request):
    hgweb = HGWeb(settings.HGWEB_CONFIG)
    tree = prepare_tree(modhg.repository.get_tree(hgweb.get_paths()))
    groups = hgweb.get_groups()
    return render_to_response('index.html', {"tree": tree, "groups": groups},
                              context_instance = RequestContext(request))