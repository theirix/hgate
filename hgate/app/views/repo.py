import os
from hgate import settings
from hgate.app import modhg
from hgate.app.forms import RepositoryForm, FileHashForm, CreateRepoForm
from hgate.app.modhg.HGWeb import HGWeb
from hgate.app.modhg import repository
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.contrib import messages
from django.utils.translation import ugettext_lazy as _
from hgate.app.modhg.repository import RepositoryException
from hgate.app.views.common import prepare_path
from hgate.app.views.decorators import render_to, require_access
from common import prepare_tree, md5_for_file

__author__ = 'hawaiian'

#page handlers
@render_to('repository.html')
@require_access(menu='hgweb')
def hgweb(request):
    hgweb = HGWeb(settings.HGWEB_CONFIG)
    tree = prepare_tree(modhg.repository.get_tree(hgweb.get_paths(), hgweb.get_collections()))
    hgrc = None
    form = None
    model = {"tree": tree, "global": True}
    file_hash = md5_for_file(settings.HGWEB_CONFIG)

    repo_field_delete_form = FileHashForm(file_hash)

    if request.method == 'POST':
        if 'save' in request.POST:
            form = RepositoryForm(file_hash, request.POST)
            if form.is_valid():
                form.export_values(hgweb, request.POST)
                file_hash = md5_for_file(settings.HGWEB_CONFIG)
                messages.success(request, _("Global settings saved successfully."))
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


@render_to('repository.html')
@require_access(menu='repository')
def repo(request, repo_path):
    hgweb = HGWeb(settings.HGWEB_CONFIG)
    tree = prepare_tree(modhg.repository.get_tree(hgweb.get_paths(), hgweb.get_collections()))
    form = None
    model = {"tree": tree, "global": False, "repo_path": repo_path}
    full_repository_path = repository.get_absolute_repository_path(repo_path)
    hgrc_path = os.path.join(full_repository_path, ".hg", "hgrc")
    _check_access_local_hgrc(request, hgrc_path)

    groups = hgweb.get_groups()
    hgweb_cfg_hash = md5_for_file(settings.HGWEB_CONFIG)
    edit_repo_form = CreateRepoForm(default_groups=groups, file_hash=hgweb_cfg_hash,
        data={"name": os.path.split(full_repository_path)[1], "group": repository.get_group(repo_path),
              "file_hash": hgweb_cfg_hash})

    try:
        hgrc = HGWeb(hgrc_path, True)
        file_hash = md5_for_file(hgrc_path)
    except ValueError:
        hgrc = None
        file_hash = None

    delete_repo_form = FileHashForm(file_hash)
    repo_field_delete_form = FileHashForm(file_hash)

    if request.method == 'POST' and hgrc is not None:
        if 'save' in request.POST:
            form = RepositoryForm(file_hash, request.POST)
            if form.is_valid():
                form.export_values(hgrc, request.POST)
                file_hash = md5_for_file(hgrc_path)
                repo_field_delete_form = FileHashForm(file_hash)
                messages.success(request, _("Repository settings saved successfully."))
        elif 'delete_field' in request.POST:
            repo_field_delete_form = FileHashForm(file_hash, request.POST)
            if repo_field_delete_form.is_valid():
                parameter = request.POST.get('parameter')
                hgrc.del_web_key(parameter)
                return HttpResponseRedirect(reverse("repository", args=[repo_path]))
        elif 'sure_delete' in request.POST:
            delete_repo_form = FileHashForm(file_hash, request.POST)
            if delete_repo_form.is_valid():
                try:
                    repository.delete(full_repository_path, repo_path)
                    messages.success(request, _("Repository '%s' deleted successfully.") % repo_path)
                except RepositoryException as e:
                    messages.warning(request,
                        _("Repository '%(repo)s' was not deleted, cause: %(cause).") % {"repo": repo_path,
                                                                                        "cause": unicode(e)})

                return HttpResponseRedirect(reverse("index"))
        elif 'save_repo' in request.POST:
            edit_repo_form = CreateRepoForm(groups, hgweb_cfg_hash, request.POST)
            if edit_repo_form.is_valid():
                name = edit_repo_form.cleaned_data['name']
                group = edit_repo_form.cleaned_data['group']
                new_path = prepare_path(name, group, groups)
                if new_path == full_repository_path:
                    messages.warning(request,
                        _("Repository '%(repo)s' was not moved to the same location: %(location)s.") % {
                            "repo": repo_path, "location": new_path})
                    return HttpResponseRedirect(reverse("repository", args=[repo_path]))
                old_item_name = repo_path if group == "-" else ""
                try:
                    repository.rename(full_repository_path, new_path, old_item_name, name)
                    messages.success(request,
                        _("Repository '%(old_path)s' moved by path '%(new_path)s' successfully.") % {
                            "old_path": full_repository_path,
                            "new_path": new_path})
                    # eval new repo_path, might changed after 'repository.rename'.
                    repo_path = "%s/%s" % (group, name) if group != "-" else name
                    return HttpResponseRedirect(reverse("repository", args=[repo_path]))
                except RepositoryException as e:
                    messages.warning(request,
                        _("Repository '%(repo)s' was not moved: %(cause)s.") % {"repo": repo_path, "cause": unicode(e)})
                    return HttpResponseRedirect(reverse("index"))

    # re-set errors if any occurs in the is_valid method.
    errors = None
    if form is not None:
        errors = form._errors
    form = RepositoryForm(file_hash)
    form._errors = errors
    form.set_default(hgweb, hgrc)

    model["form"] = form
    model["repo_field_delete_form"] = repo_field_delete_form
    model["delete_repo_form"] = delete_repo_form
    model["repo_form"] = edit_repo_form

    return model

# helpers

def _check_access_local_hgrc(request, hgrc_path):
    hgdir = hgrc_path[:hgrc_path.rfind('/hgrc')]
    if (not os.access(hgrc_path, os.F_OK)) and (not os.access(hgdir, os.X_OK or os.R_OK or os.W_OK)):
        messages.error(request, _("No hgrc for this repository. No write access to create hgrc by path: ") + hgdir)
    elif os.access(hgrc_path, os.F_OK) and not os.access(hgrc_path, os.W_OK):
        messages.error(request, _("No access to write mercurial`s local configuration file by path: ") + hgrc_path)
    elif os.access(hgrc_path, os.F_OK) and not os.access(hgrc_path, os.R_OK):
        messages.warning(request, _("No access to read mercurial`s local configuration file by path: ") + hgrc_path)