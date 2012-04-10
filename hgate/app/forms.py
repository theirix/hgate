import os
import re
from django import forms
from django.contrib import messages
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.utils.translation import ugettext_lazy as _
from hgate.app import modhg
from hgate.app.modhg import repository
from hgate.app.modhg.repository import RepositoryException
from hgate.app.views.common import prepare_path
import modhg.usersb as users
from hgate import settings

class FileHashForm(forms.Form):
    file_hash = forms.CharField(widget=forms.HiddenInput())

    def __init__(self, file_hash="", *args, **kwargs):
        super(FileHashForm, self).__init__(*args, **kwargs)
        self.fields['file_hash'].widget.attrs['value'] = file_hash

    def clean(self):
        old_hash = self.cleaned_data['file_hash']
        new_hash = self.fields['file_hash'].widget.attrs['value']
        if old_hash != new_hash:
            self.data = self.data.copy() # make QueryDict mutable
            self.data['file_hash'] = new_hash
            raise forms.ValidationError(_("Configuration file was changed, please try again."))
        return self.cleaned_data

class DeleteGroupForm(FileHashForm):
    def __init__(self, file_hash, *args, **kwargs):
        super(DeleteGroupForm, self).__init__(file_hash, *args, **kwargs)


    def delete_group(self, request, groups):
        name = request.POST.get("group_name")
        is_collection = request.POST.get("is_collection")
        path = dict(groups)[name]
        try:
            modhg.repository.delete_group(path, name, is_collection == 'True')
            messages.success(request, _("Group '%s' was deleted successfully.") % name)
        except modhg.repository.RepositoryException as e:
            messages.warning(request, str(e))
        return HttpResponseRedirect(reverse('index'))

class RepositoryForm(FileHashForm):
    allow_read = forms.CharField(label=_("allow_read"), initial=None, required=False)
    allow_push = forms.CharField(label=_("allow_push"), initial=None, required=False)
    deny_read = forms.CharField(label=_("deny_read"), initial=None, required=False)
    deny_push = forms.CharField(label=_("deny_push"), initial=None, required=False)
    style = forms.CharField(label=_("style"), initial=None, required=False)
    allow_archive = forms.CharField(label=_("allow_archive"), initial=None, required=False)
    baseurl = forms.CharField(label=_("baseurl"), initial=None, required=False)
    push_ssl = forms.ChoiceField(label=_("push_ssl"), required=False, choices=(('true', 'true'), ('false', 'false')))

    classes = {}

    def __init__(self, file_hash, *args, **kwargs):
        super(RepositoryForm, self).__init__(file_hash, *args, **kwargs)
        self.filtered_keys = self.fields.keys()
        # file hash field does not play in repository form logic.
        self.filtered_keys.remove('file_hash')

    def set_default(self, hgweb, hgrc):
        for field in self.filtered_keys:
            self.classes[field] = "r_val_default"
        if hgweb is not None:
            for field in self.filtered_keys:
                self._set_value(hgweb, field, "r_val_global")
        if hgrc is not None:
            for field in self.filtered_keys:
                self._set_value(hgrc, field, "r_val_local")

    def _set_value(self, conf, field_name, css_class):
        value = conf.get_web_key(field_name)
        if value is not None:
            if self.fields[field_name] is forms.BooleanField:
                if value == 'true':
                    self.fields[field_name].initial = 'true'
                else:
                    self.fields[field_name].initial = 'false'
            else:
                self.fields[field_name].initial = value
            self.classes[field_name] = css_class

    def export_values(self, hgrc, post):
        for field in self.filtered_keys:
            self._export_value(hgrc, field, post)

    def _export_value(self, hgrc, field_name, post):
        if field_name in post:
            hgrc.set_web_key(field_name, self.cleaned_data[field_name])


class AddUser(FileHashForm):
    login = forms.CharField(label=_("Login"), max_length=40, required=True)
    password1 = forms.CharField(label=_("Password"), max_length=20, required=True, widget=forms.PasswordInput)
    password2 = forms.CharField(label=_("Re-enter password"), max_length=20, required=True, widget=forms.PasswordInput)

    def __init__(self, file_hash, *args, **kwargs):
        super(AddUser, self).__init__(file_hash, *args, **kwargs)

    def clean_password2(self):
        password1 = self.cleaned_data.get("password1", "")
        password2 = self.cleaned_data["password2"]
        if password1 != password2:
            raise forms.ValidationError(_("Passwords should be the same"))
        return password2

    def clean_login(self):
        login = self.cleaned_data["login"]
        if users.exists(settings.AUTH_FILE, login):
            raise forms.ValidationError(_("User exists"))
        return login


class EditUser(FileHashForm):
    password1 = forms.CharField(label=_("Password"), max_length=20, required=True, widget=forms.PasswordInput)
    password2 = forms.CharField(label=_("Re-enter password"), max_length=20, required=True, widget=forms.PasswordInput)

    def __init__(self, file_hash, *args, **kwargs):
        super(EditUser, self).__init__(file_hash, *args, **kwargs)

    def clean_password2(self):
        password1 = self.cleaned_data.get("password1", "")
        password2 = self.cleaned_data["password2"]
        if password1 != password2:
            raise forms.ValidationError(_("Passwords should be the same"))
        return password2


class CreateRepoForm(FileHashForm):
    def __init__(self, default_groups, file_hash, *args, **kwargs):
        super(CreateRepoForm, self).__init__(file_hash, *args, **kwargs)
        self.fields['group'].choices = [("-", "-")] + default_groups

    def clean_name(self):
        _name = self.cleaned_data['name'].strip()
        if re.search(r"([\*:\?/\\]|^\.$|^\.\.$)", _name): #found one of (*:?/\) or . or ..
            raise forms.ValidationError(_("Don`t use special characters any of *:?/\ or names '.' and '..'"))
        return _name

    name = forms.CharField(label=_("Repository name"), max_length=100)
    group = forms.ChoiceField(label=_("Group"))

    def create_repository(self, request, groups):
        name = self.cleaned_data['name']
        group = self.cleaned_data['group']
        repo_path = prepare_path(name, group, groups)
        try:
            modhg.repository.create(repo_path, name, group == "-")
            messages.success(request, _("New repository was created."))
            if group == "-":
                redirect_path = reverse("repository", args=[name])
            else:
                redirect_path = reverse("repository", args=[group + os.path.sep + name])
        except modhg.repository.RepositoryException as e:
            messages.warning(request, str(e))
            return HttpResponseRedirect(reverse('index'))

        return HttpResponseRedirect(redirect_path)

    def rename(self, request, repo_path, groups, full_repository_path):
        name = self.cleaned_data['name']
        group = self.cleaned_data['group']
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


class ManageGroupsForm(FileHashForm):
    is_collection = forms.CharField(widget=forms.HiddenInput(), initial='False')
    name = forms.CharField(label=_("Group name"), max_length=100)
    path = forms.CharField(label=_("Path"))

    def __init__(self, file_hash, *args, **kwargs):
        super(ManageGroupsForm, self).__init__(file_hash, *args, **kwargs)

    def clean_path(self):
        _path = self.cleaned_data['path'].strip()
        is_collection = self.cleaned_data.get('is_collection')
        if not is_collection == 'True' and not re.search(r"([/]\*{1,2})$", _path):
            raise forms.ValidationError(_("Path should be ended with /* or /**"))
        return _path

    def create_group(self, request):
        name = self.cleaned_data['name']
        is_collection = self.cleaned_data['is_collection']
        path = self.cleaned_data['path']
        try:
            modhg.repository.create_group(path, name, is_collection == 'True')
            messages.success(request, _("New group was added."))
        except modhg.repository.RepositoryException as e:
            messages.warning(request, _("Group was not created: %s") % unicode(e))
        return HttpResponseRedirect(reverse('index'))

    def edit_group(self, request, groups, hgweb):
        old_name = request.POST.get("old_group_name")
        old_path = request.POST.get("old_group_path")
        name = self.cleaned_data['name']
        path = self.cleaned_data['path']
        is_collection = self.cleaned_data['is_collection'] == 'True'
        if (old_name != name and name not in zip(*groups)[0]) or (name == old_name and path != old_path):
            if not is_collection:
                hgweb.del_paths(old_name)
            else:
                hgweb.del_collections(old_name)
            try:
                modhg.repository.create_group(path, name, is_collection)
                messages.success(request, _("Group '%s' was changed.") % old_name)
            except modhg.repository.RepositoryException as e:
                messages.warning(request, str(e))
        elif name == old_name and path == old_path:
            pass#do nothing
        else:
            messages.warning(request,
                _("There is already a group with such a name. Group '%s' wasn`t changed.") % old_name)
        return HttpResponseRedirect(reverse('index'))


class RawModeForm(FileHashForm):
    hgrc = forms.CharField(widget=forms.Textarea(attrs={'rows':20, 'cols':80, 'wrap':"off"}), required=False)
    def __init__(self, file_hash, *args, **kwargs):
        super(RawModeForm, self).__init__(file_hash, *args, **kwargs)


