import re
from django import forms
from django.utils.translation import ugettext_lazy as _
import app.modhg.usersb as users
import settings

class RepositoryForm(forms.Form):
    allow_read = forms.CharField(label= _("Allow read"), max_length=100)
    allow_push = forms.CharField(label= _("Allow push"), max_length=100)
    deny_read = forms.CharField(label= _("Deny read"), max_length=100)
    deny_push = forms.CharField(label=_("Deny push"), max_length=100)
    put_ssl = forms.BooleanField(label=_("Put ssl"))

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
            raise forms.ValidationError("Don`t use special characters any of (*:?/\)")
        return _name


    name = forms.CharField(label = _("Repository name"), max_length=100)
    group = forms.ChoiceField(label = _("Group"))
