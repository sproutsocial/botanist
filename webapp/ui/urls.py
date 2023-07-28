from django.urls import path

from . import views

urlpatterns = [
    path("", views.index),
    path("search/", views.search),
    path("search/results.json", views.search_json),
]
