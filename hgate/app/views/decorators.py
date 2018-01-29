import os
import copy
from django.contrib import messages
from hgate import settings
from django.utils.translation import ugettext_lazy as _
from django.shortcuts import render_to_response
from django.template import RequestContext

def _check_configs_access(request):
    """
    checks existing and 'rwx' of next files:
    - root directory and 'rx';
    - global hg config and 'rw'.
    adds error message if any.
    @return False if any error, True if all ok
    """
    ret_val = True
    if not os.access(settings.HGWEB_CONFIG, os.F_OK):
        messages.error(request, _("Main configuration file does not exist by specified path: ") + settings.HGWEB_CONFIG)
        ret_val = False
    elif not os.access(settings.HGWEB_CONFIG, os.R_OK or os.W_OK):
        messages.error(request,
            _("No access to read or write mercurial`s global configuration file by path: ") + settings.HGWEB_CONFIG)
        ret_val = False
    if not os.access(settings.REPOSITORIES_ROOT, os.F_OK):
        messages.error(request,
            _("Root directory of repositories does not exist by path: ") + settings.REPOSITORIES_ROOT)
        ret_val = False
    elif not os.access(settings.REPOSITORIES_ROOT, os.R_OK or os.X_OK):
        messages.error(request,
            _("No read or execute access to the root directory of repositories by path: ") + settings.REPOSITORIES_ROOT)
        ret_val = False
    if not os.access(settings.AUTH_FILE, os.F_OK or os.R_OK):
        messages.error(request, _("No users file or no read access by path: ") + settings.AUTH_FILE)
        ret_val = False
    return ret_val


def require_access(menu):
    def access_checker(func):
        def wrapper(request, *args, **kw):
            if _check_configs_access(request):
                return func(request, *args, **kw)
            else:
                return {'menu': menu}, 'errors.html'
        return wrapper
    return access_checker


def render_to(template):
    """
    Decorator for Django views that sends returned dict to render_to_response
    function.

    Template name can be decorator parameter or TEMPLATE item in returned
    dictionary.  RequestContext always added as context instance.
    If view doesn't return dict then decorator simply returns output.

    Parameters:
     - template: template name to use
     - mimetype: content type to send in response headers

    Examples:
    # 1. Template name in decorator parameters

    @render_to('template.html')
    def foo(request):
        bar = Bar.object.all()
        return {'bar': bar}

    # equals to
    def foo(request):
        bar = Bar.object.all()
        return render_to_response('template.html',
                                  {'bar': bar},
                                  context_instance=RequestContext(request))


    # 2. Template name as TEMPLATE item value in return dictionary.
         if TEMPLATE is given then its value will have higher priority
         than render_to argument.

    @render_to()
    def foo(request, category):
        template_name = '%s.html' % category
        return {'bar': bar, 'TEMPLATE': template_name}

    #equals to
    def foo(request, category):
        template_name = '%s.html' % category
        return render_to_response(template_name,
                                  {'bar': bar},
                                  context_instance=RequestContext(request))

    """

    def renderer(func):
        def wrapper(request, *args, **kw):
            output = func(request, *args, **kw)
            if isinstance(output, (list, tuple)):
                outc = copy.copy(output[0])
                outc['hgweb_url'] = settings.HGWEB_URL
                return render_to_response(output[1], outc, RequestContext(request))
            elif isinstance(output, dict):
                output['hgweb_url'] = settings.HGWEB_URL
                return render_to_response(template, output, RequestContext(request))
            return output

        return wrapper

    return renderer
