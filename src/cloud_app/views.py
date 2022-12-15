from django.shortcuts import render
from django.http import HttpResponse

def home_view(request, *args, **kwargs):
    return render(request, 'home_page.html', {})

def log_in_view(request, *args, **kwargs):
    return render(request, 'log_in.html', {})

def user_patient_view(request, *args, **kwargs):
    return render(request, 'user_patient.html', {})