from django.urls import path

import views

urlpatterns = [
    path("", views.index),
    path("search/", views.search),
    path(r"search/results.json", views.search_json),
]
