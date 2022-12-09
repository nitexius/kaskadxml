from django.conf.urls import url
from . import views

urlpatterns = [
    url(r'^index_dgu/$', views.index, name='index_dgu'),
]
