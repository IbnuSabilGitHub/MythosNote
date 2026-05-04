from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from django.contrib.auth.models import User
from django.contrib import messages


def home(request):
    return render(request, 'home.html')


def sign_in(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('home')
        else:
            messages.error(request, 'Username atau password salah.')

    return render(request, 'signin.html', {"hide_nav": True})


def sign_up(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        password_confirm = request.POST.get('password_confirm')

        if password != password_confirm:
            messages.error(request, 'Password tidak cocok.')
            return render(request, 'signup.html', {"hide_nav": True})

        if User.objects.filter(username=username).exists():
            messages.error(request, 'Username sudah terdaftar.')
            return render(request, 'signup.html', {"hide_nav": True})

        if User.objects.filter(email=email).exists():
            messages.error(request, 'Email sudah terdaftar.')
            return render(request, 'signup.html', {"hide_nav": True})

        user = User.objects.create_user(username=username, email=email, password=password)
        login(request, user)
        messages.success(request, 'Akun berhasil dibuat!')
        return redirect('home')

    return render(request, 'signup.html', {"hide_nav": True})


def forgot_password(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        password_confirm = request.POST.get('password_confirm')

        try:
            user = User.objects.get(username=username, email=email)
        except User.DoesNotExist:
            messages.error(request, 'Username atau email tidak ditemukan.')
            return render(request, 'forgot_password.html', {"hide_nav": True})

        if password != password_confirm:
            messages.error(request, 'Password tidak cocok.')
            return render(request, 'forgot_password.html', {"hide_nav": True})

        user.set_password(password)
        user.save()
        messages.success(request, 'Password berhasil direset. Silakan login.')
        return redirect('signin')

    return render(request, 'forgot_password.html', {"hide_nav": True})
