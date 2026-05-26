"""Rute URL untuk alur autentikasi dan verifikasi."""

from django.urls import path

from . import views


urlpatterns = [
    path("signin/", views.sign_in, name="signin"),
    path("signup/", views.sign_up, name="signup"),
    path("auth/google/", views.google_sign_in, name="google_signin"),
    path("forgot-password/", views.forgot_password, name="forgot_password"),
    path("reset/<uidb64>/<token>/", views.password_reset_confirm, name="password_reset_confirm"),
    path("email-unverified/", views.email_unverified, name="email_unverified"),
    path("resend-verification/", views.resend_verification, name="resend_verification"),
    path("verify-email/<uidb64>/<token>/", views.verify_email, name="verify_email"),
    path("logout/", views.sign_out, name="logout"),
]
