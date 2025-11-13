from django.contrib import admin
from django.urls import path

from wifi_portal import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.wifi_setup, name='wifi_setup'),
    path('connecting/', views.wifi_connecting, name='wifi_connecting'),
    path('do_connect/', views.wifi_do_connect, name='wifi_do_connect'),
    path('configured/', views.configured, name='configured'),
    path('recipe-status/', views.recipe_status, name='recipe_status'),
]
