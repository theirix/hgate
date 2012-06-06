import os
from django.utils.datastructures import SortedDict
from hgate.app import modhg
from hgate.app.views.decorators import render_to, require_access
from hgate import settings
import hgate.app.modhg.usersb as users
from hgate.app.forms import AddUser, EditUser, FileHashForm
from hgate.app.modhg.HGWeb import HGWeb
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.contrib import messages
from django.utils.translation import ugettext_lazy as _
from common import prepare_tree, md5_for_file

#page handlers
@render_to('users.html')
@require_access(menu='users')
def user_index(request):
    is_w_access = _check_users_file(request)
    users_file_hash = md5_for_file(settings.AUTH_FILE)
    form = AddUser(users_file_hash)
    delete_user_form = FileHashForm(users_file_hash)
    hgweb = HGWeb(settings.HGWEB_CONFIG)
    tree = prepare_tree(modhg.repository.get_tree(hgweb.get_paths(), hgweb.get_collections()))
    model = {"tree": tree}
    if request.method == "POST":
        if "delete_user" in request.POST:
            delete_user_form = FileHashForm(users_file_hash, request.POST)
            if delete_user_form.is_valid() and is_w_access:
                login = request.POST.get("login")
                users.remove(settings.AUTH_FILE, login)
                messages.success(request, _("User '%s' was deleted.") % login)
                return HttpResponseRedirect(reverse('users_index'))
        elif "add_user" in request.POST:
            form = AddUser(users_file_hash, request.POST)
            if form.is_valid() and is_w_access:
                login = form.cleaned_data['login']
                password = form.cleaned_data['password2']
                users.add(settings.AUTH_FILE, login, password)
                messages.success(request, _("User '%s' was added.") % login)
                return HttpResponseRedirect(reverse('users_index'))
    user_list = users.login_list(settings.AUTH_FILE)
    model["delete_user_form"] = delete_user_form
    model["form"] = form
    model["users"] = user_list
    return model


@render_to('useredit.html')
@require_access(menu='users')
def user(request, action, login):
    users_file_hash = md5_for_file(settings.AUTH_FILE)
    hgweb = HGWeb(settings.HGWEB_CONFIG)
    tree = prepare_tree(modhg.repository.get_tree(hgweb.get_paths(), hgweb.get_collections()))
    model = {"tree": tree}
    is_write_access = _check_users_file(request)
    if action == "edit":
        # todo: check if login exists
        if request.method == "POST":
            form = EditUser(users_file_hash, request.POST)
            if form.is_valid() and is_write_access:
                password = form.cleaned_data['password2']
                users.update(settings.AUTH_FILE, login, password)
                messages.success(request, _("Password changed successfully."))
                return HttpResponseRedirect(reverse("users", args=[action, login]))
        else:
            form = EditUser(users_file_hash)
        model["form"] = form
        model["login"] = login
        # sorting permissions dict by key
        permissions = users.permissions(login)
        permissions = sorted(permissions.items(), key=lambda elem: elem[0])
        model["permissions"] = SortedDict(permissions)
        return model

# helpers

def _check_users_file(request):
    ret_val = True
    if not os.access(settings.AUTH_FILE, os.W_OK):
        messages.warning(request, _("No write access for users file by path: ") + settings.AUTH_FILE)
        ret_val = False
    return ret_val