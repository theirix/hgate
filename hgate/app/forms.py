import re
from django import forms
from django.utils.translation import ugettext_lazy as _
import app.modhg.usersb as users
import settings


class RepositoryForm(forms.Form):
    allow_read = forms.CharField(label= _("allow_read"), initial=None)
    allow_push = forms.CharField(label= _("allow_push"), initial=None)
    deny_read = forms.CharField(label= _("deny_read"), initial=None)
    deny_push = forms.CharField(label=_("deny_push"), initial=None)
    push_ssl = forms.BooleanField(label=_("push_ssl"), initial=None)

    classes = {}

    def set_default(self, hgweb, hgrc):
        for field in self.fields:
            self.classes[field] = "r_val_default"
        if hgweb is not None:
            for field in self.fields:
                self._set_value(hgweb, field, "r_val_global")
        if hgrc is not None:
            for field in self.fields:
                self._set_value(hgrc, field, "r_val_local")

    def _set_value(self, conf, field_name, css_class):
        value = conf.get_web_key(field_name)
        if value is not None:
            self.fields[field_name].initial = value
            self.classes[field_name] = css_class

class AddUser(forms.Form):
    login = forms.CharField(label=_("Login"), max_length=40, required=True)
    password1 = forms.CharField(label=_("Password"), max_length=20, required=True, widget=forms.PasswordInput)
    password2 = forms.CharField(label=_("Re-enter password"), max_length=20, required=True, widget=forms.PasswordInput)

    def clean_password2(self):
        password1 = self.cleaned_data.get("password1", "")
        password2 = self.cleaned_data["password2"]
        if password1 != password2:
            raise forms.ValidationError(_("Passwords should be the same"))
        return password2

    def clean_login(self):
        login = self.cleaned_data["login"]
        if(users.exists(settings.AUTH_FILE, login)):
            raise forms.ValidationError(_("User exists"))
        return login

class EditUser(forms.Form):
    password1 = forms.CharField(label=_("Password"), max_length=20, required=True, widget=forms.PasswordInput)
    password2 = forms.CharField(label=_("Re-enter password"), max_length=20, required=True, widget=forms.PasswordInput)

    def clean_password2(self):
        password1 = self.cleaned_data.get("password1", "")
        password2 = self.cleaned_data["password2"]
        if password1 != password2:
            raise forms.ValidationError(_("Passwords should be the same"))
        return password2

class CreateRepoForm(forms.Form):
    def __init__(self, default_groups, *args, **kwargs):
        super(CreateRepoForm, self).__init__(*args, **kwargs)

        self.fields['group'].choices = [("-","-")] + default_groups

    def clean_name(self):
        _name = self.cleaned_data['name'].strip()
        if re.search(r"[\*\:\?\/\\]", _name): #found one of (*:?/\)
            raise forms.ValidationError(_("Don`t use special characters any of (*:?/\)"))
        return _name


    name = forms.CharField(label = _("Repository name"), max_length=100)
    group = forms.ChoiceField(label = _("Group"))

class ManageGroupsForm(forms.Form):
    name = forms.CharField(label = _("Group name"), max_length=100)
    path = forms.CharField(label = _("Path"))

    def clean_path(self):
        _path = self.cleaned_data['path'].strip()
        if not re.search(r"([\/]\*{1,2})$", _path):
            raise forms.ValidationError(_("Path should be ended with /* or /**"))
        return _path
