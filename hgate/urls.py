from django.conf.urls.defaults import *
from app.views.index import index
from app.views.repo import repo, hgweb
from app.views.usersv import user, user_index
# Uncomment the next two lines to enable the admin:
# from django.contrib import admin
# admin.autodiscover()
import settings

urlpatterns = patterns('',
    url(r'^$', index, name='index'),
    url(r'repo/(?P<repo_path>.*)', repo, name='repository'),
    url(r'hgweb/?$', hgweb, name='hgweb'),
    url(r'users/?$', user_index, name='users_index'),
    url(r'users/(?P<action>[^/]+)/(?P<login>.*)', user, name='users'),
    url(r'^i18n/', include('django.conf.urls.i18n')),
    url(r'^(?P<path>.*)$', 'django.views.static.serve', {'document_root': settings.MEDIA_ROOT}),

    # Uncomment the admin/doc line below to enable admin documentation:
    # (r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    # (r'^admin/', include(admin.site.urls)),
)
