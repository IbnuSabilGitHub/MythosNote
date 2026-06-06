"""Form autentikasi untuk masuk, daftar, dan pemulihan sandi."""

from typing import Any

from django import forms
from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.forms import SetPasswordForm
from django.contrib.auth.password_validation import validate_password

from .validators import validate_real_email


User = get_user_model()


class SignInForm(forms.Form):
    """Masuk pakai email dan password."""

    email = forms.EmailField()
    password = forms.CharField(strip=False, widget=forms.PasswordInput, max_length=128)

    def __init__(self, request: Any = None, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.request = request
        self.user = None
        self.inactive_user = None

    def clean(self) -> dict[str, Any]:
        """Autentikasi berdasarkan email dan password."""
        cleaned_data = super().clean()
        email = cleaned_data.get("email", "").strip().lower()
        password = cleaned_data.get("password")

        if email and password:
            self.inactive_user = User.objects.filter(email__iexact=email, is_active=False).first()
            if self.inactive_user and self.inactive_user.check_password(password):
                raise forms.ValidationError("Akun belum aktif. Verifikasi email dulu.")

            self.user = authenticate(
                self.request,
                email=email,
                password=password,
            )
            if self.user is None:
                raise forms.ValidationError("Email atau password salah.")

        return cleaned_data


class SignUpForm(forms.ModelForm):
    """Buat akun email/password untuk verifikasi."""

    password = forms.CharField(strip=False, widget=forms.PasswordInput, max_length=128)
    password_confirm = forms.CharField(strip=False, widget=forms.PasswordInput, max_length=128)

    class Meta:
        model = User
        fields = ["email"]

    def clean_email(self) -> str:
        """Validasi format email tanpa membocorkan status akun."""

        return validate_real_email(self.cleaned_data["email"])

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
        
        seed = user.email.split("@", 1)[0].replace(".", "_")[:140] or "user"
        username = seed
        suffix = 1
        while User.objects.filter(username__iexact=username).exists():
            suffix += 1
            username = f"{seed}_{suffix}"
        user.username = username
        
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


class ProfileUpdateForm(forms.ModelForm):
    """Form untuk memperbarui profil user."""

    first_name = forms.CharField(
        max_length=150,
        required=True,
        widget=forms.TextInput(attrs={
            "class": "block w-full rounded-lg border border-neutral-800 bg-neutral-950 px-4 py-2.5 font-manrope text-sm text-zinc-100 placeholder-stone-600 focus:border-primary focus:outline-none",
            "placeholder": "Nama Lengkap Anda"
        })
    )

    class Meta:
        model = User
        fields = ["first_name"]
