from django.conf import settings
from django.core.validators import RegexValidator
from django.db import models

phone_validator = RegexValidator(
    r'^\+?\d{7,15}$',
    'Enter a valid phone number (7-15 digits, optional leading +).',
)


class Profile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='profile')
    phone = models.CharField(max_length=16, blank=True, validators=[phone_validator])
    city = models.CharField(max_length=80, blank=True)

    def __str__(self):
        return f'Profile of {self.user.username}'


def get_profile(user):
    """Return the user's profile, creating it if it does not exist yet."""
    return Profile.objects.get_or_create(user=user)[0]
