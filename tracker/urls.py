from django.urls import path
from . import views

urlpatterns = [
    path("", views.index_2_0),
    path("clean", views.clean)
]