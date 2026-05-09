"""Form autentikasi untuk masuk, daftar, dan pemulihan sandi."""

from typing import Any

from django import forms
from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.forms import SetPasswordForm
from django.contrib.auth.password_validation import validate_password


User = get_user_model()


class SignInForm(forms.Form):
    """Masuk pakai username atau email dan password."""

    username = forms.CharField(max_length=254, min_length=3)
    password = forms.CharField(strip=False, widget=forms.PasswordInput)

    def __init__(self, request: Any = None, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.request = request
        self.user = None

    def clean(self) -> dict[str, Any]:
        """Autentikasi berdasarkan identifier dan password."""
        cleaned_data = super().clean()
        identifier = cleaned_data.get("username", "").strip()
        password = cleaned_data.get("password")

        if identifier and password:
            auth_username = identifier
            if "@" in identifier:
                user = User.objects.filter(email__iexact=identifier).first()
                auth_username = user.get_username() if user else identifier

            self.user = authenticate(
                self.request,
                username=auth_username,
                password=password,
            )
            if self.user is None:
                raise forms.ValidationError("Email/username atau password salah.")

        return cleaned_data


class SignUpForm(forms.ModelForm):
    """Buat akun email/password untuk verifikasi."""

    password = forms.CharField(strip=False, widget=forms.PasswordInput)
    password_confirm = forms.CharField(strip=False, widget=forms.PasswordInput)

    class Meta:
        model = User
        fields = ["username", "email"]

    def clean_email(self) -> str:
        """Cek email belum terdaftar."""
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("Email sudah terdaftar.")
        return email

    def clean_username(self) -> str:
        """Cek username unik dan sesuai panjang."""
        username = self.cleaned_data["username"].strip()
        if len(username) < 3 or len(username) > 20:
            raise forms.ValidationError("Username harus 3-20 karakter.")
        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError("Username sudah terdaftar.")
        return username

    def clean(self) -> dict[str, Any]:
        """Cek konfirmasi password dan kekuatan password."""
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        password_confirm = cleaned_data.get("password_confirm")

        if password and password_confirm and password != password_confirm:
            self.add_error("password_confirm", "Password tidak cocok.")
        if password:
            validate_password(password)

        return cleaned_data

    def save(self, commit: bool = True) -> Any:
        """Simpan user baru dengan password yang benar."""
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        user.set_password(self.cleaned_data["password"])
        if commit:
            user.save()
        return user


class ForgotPasswordForm(forms.Form):
    """Minta email reset tanpa bocorkan akun."""

    email = forms.EmailField()


class PasswordResetConfirmForm(SetPasswordForm):
    """Set password baru setelah token valid."""

    def clean_new_password1(self) -> str:
        """Tolak password baru yang sama dengan password lama."""
        password = self.cleaned_data.get("new_password1", "")
        if password and self.user.check_password(password):
            raise forms.ValidationError("Password baru tidak boleh sama dengan password lama.")
        return password
