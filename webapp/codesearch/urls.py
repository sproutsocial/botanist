from django.conf.urls import patterns
from django.conf.urls import url

urlpatterns = patterns(
    '',
    url(r'^$', 'ui.views.index'),
    url(r'^search/$', 'ui.views.search'),
    url(r'^search/results.json$', 'ui.views.search_json'),
    #url(r'^admin/', include(admin.site.urls)),
)
