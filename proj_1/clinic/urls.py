from django.urls import path
from clinic import views


urlpatterns = [
    path('', views.dashboard, name='dashboard'),
]