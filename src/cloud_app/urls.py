from django.urls import path
from . import views

urlpatterns = [
    path('', views.home_view, name='home_page'),
    path('', views.log_in_view, name='log_in'),
    path('', views.user_patient_view, name='home_page'),
]