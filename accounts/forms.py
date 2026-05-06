from django import forms
from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.forms import SetPasswordForm
from django.contrib.auth.password_validation import validate_password


User = get_user_model()


class SignInForm(forms.Form):
    """Authenticate with either username or email plus password."""

    username = forms.CharField(max_length=254)
    password = forms.CharField(strip=False, widget=forms.PasswordInput)

    def __init__(self, request=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.request = request
        self.user = None

    def clean(self):
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
    """Create local email/password accounts ready for verification."""

    password = forms.CharField(strip=False, widget=forms.PasswordInput)
    password_confirm = forms.CharField(strip=False, widget=forms.PasswordInput)

    class Meta:
        model = User
        fields = ["username", "email"]

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("Email sudah terdaftar.")
        return email

    def clean_username(self):
        username = self.cleaned_data["username"].strip()
        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError("Username sudah terdaftar.")
        return username

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        password_confirm = cleaned_data.get("password_confirm")

        if password and password_confirm and password != password_confirm:
            self.add_error("password_confirm", "Password tidak cocok.")
        if password:
            validate_password(password)

        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        user.set_password(self.cleaned_data["password"])
        if commit:
            user.save()
        return user


class ForgotPasswordForm(forms.Form):
    """Request a password reset email without revealing account existence."""

    email = forms.EmailField()


class PasswordResetConfirmForm(SetPasswordForm):
    """Set a new password after Django token validation succeeds."""

    pass
