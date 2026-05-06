from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from django.contrib.auth.models import User
from django.contrib import messages
from accounts.decorators import verified_email_required


def home(request):
    """Render the public landing page with auth-aware navigation."""

    return render(request, 'home.html')

@verified_email_required
def project(request):
    """Render the project page, accessible only for verified users."""
    
    return render(request, 'project.html', {'hide_nav': True})
