from django.conf.urls.defaults import *
from hgate.views import index, repo, repository
# Uncomment the next two lines to enable the admin:
# from django.contrib import admin
# admin.autodiscover()
import settings

urlpatterns = patterns('',
    url(r'^$', index, name='index'),
    url(r'repo/(?P<repo_path>.*)', repo),
    url(r'repository/$', repository, name='repository'),
    url(r'^(?P<path>.*)$', 'django.views.static.serve', {'document_root': settings.MEDIA_ROOT}),
    # Example:
    # (r'^mercurial/', include('mercurial.foo.urls')),

    # Uncomment the admin/doc line below to enable admin documentation:
    # (r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    # (r'^admin/', include(admin.site.urls)),
)
