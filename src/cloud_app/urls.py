from django.urls import path
from . import views

urlpatterns = [
    path('', views.home_view, name='home_page'),
    path('login/', views.log_in_view, name='login'),
    path('user_patient/', views.user_patient_view, name='user_patient'),
    path('post_sign_in/', views.post_sign_in, name='post_sign_in'),
    path('patient_signup/', views.patient_sign_up, name='patient_signup'),
    path('hcp_signup/', views.hcp_sign_up, name='hcp_signup'),
    path('patient_post_sign_up/', views.patient_post_sign_up, name='patient_post_sign_up'),
    path('hcp_post_sign_up/', views.hcp_post_sign_up, name='hcp_post_sign_up'),
    path('logout/', views.logout, name="logout"),
]

