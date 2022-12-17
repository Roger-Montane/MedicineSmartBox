from django.urls import path
from . import views

urlpatterns = [
    path('', views.home_view, name='home_page'),
    path('login/', views.log_in_view, name='log_in'),
    path('user_patient', views.user_patient_view, name='user_patient'),
]