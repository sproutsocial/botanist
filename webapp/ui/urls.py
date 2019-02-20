from django.conf.urls import url

import views

urlpatterns = [
    url(r'^$', views.index),
    url(r'^search/$', views.search),
    url(r'^search/results.json$', views.search_json),
    #url(r'^admin/', include(admin.site.urls)),
]