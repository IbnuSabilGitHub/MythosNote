"""Validator email domain/MX."""

from django.core.exceptions import ValidationError
from email_validator import EmailNotValidError, validate_email


ERROR_INVALID_EMAIL = "Email atau domain email tidak valid."


def validate_real_email(email: str) -> str:
    """Validasi format email + domain + MX. Return email normalisasi."""
    try:
        result = validate_email(email, check_deliverability=True)
        return result.normalized
    except EmailNotValidError as exc:
        raise ValidationError(ERROR_INVALID_EMAIL) from exc
