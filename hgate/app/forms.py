import re
from django import forms
from django.utils.translation import ugettext_lazy as _
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

class RepositoryForm(FileHashForm):
    allow_read = forms.CharField(label= _("allow_read"), initial=None, required=False)
    allow_push = forms.CharField(label= _("allow_push"), initial=None, required=False)
    deny_read = forms.CharField(label= _("deny_read"), initial=None, required=False)
    deny_push = forms.CharField(label=_("deny_push"), initial=None, required=False)
    style = forms.CharField(label=_("style"), initial=None, required=False)
    allow_archive = forms.CharField(label=_("allow_archive"), initial=None, required=False)
    baseurl = forms.CharField(label=_("baseurl"), initial=None, required=False)
    push_ssl = forms.ChoiceField(label=_("push_ssl"), required=False, choices=(('true','true'),('false','false')))

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
        self.fields['group'].choices = [("-","-")] + default_groups

    def clean_name(self):
        _name = self.cleaned_data['name'].strip()
        if re.search(r"([\*:\?/\\]|^\.$|^\.\.$)", _name): #found one of (*:?/\) or . or ..
            raise forms.ValidationError(_("Don`t use special characters any of *:?/\ or names '.' and '..'"))
        return _name

    name = forms.CharField(label = _("Repository name"), max_length=100)
    group = forms.ChoiceField(label = _("Group"))

class ManageGroupsForm(FileHashForm):
    is_collection = forms.CharField(widget=forms.HiddenInput(), initial='False')
    name = forms.CharField(label = _("Group name"), max_length=100)
    path = forms.CharField(label = _("Path"))

    def __init__(self, file_hash, *args, **kwargs):
        super(ManageGroupsForm, self).__init__(file_hash, *args, **kwargs)

    def clean_path(self):
        _path = self.cleaned_data['path'].strip()
        is_collection = self.cleaned_data.get('is_collection')
        if not is_collection == 'True' and not re.search(r"([/]\*{1,2})$", _path):
            raise forms.ValidationError(_("Path should be ended with /* or /**"))
        return _path
