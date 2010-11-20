__author__ = 'Sergey'

from django import forms
from django.utils.translation import ugettext_lazy as _

class RepositoryForm(forms.Form):
    allow_read = forms.CharField(label= _("Allow read"), max_length=100)
    allow_push = forms.CharField(label= _("Allow push"), max_length=100)
    deny_read = forms.CharField(label= _("Deny read"), max_length=100)
    deny_push = forms.CharField(label=_("Deny push"), max_length=100)
    put_ssl = forms.BooleanField(label=_("Put ssl"))