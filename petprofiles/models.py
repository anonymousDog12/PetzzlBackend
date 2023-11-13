from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinLengthValidator, RegexValidator

User = get_user_model()


class PetProfile(models.Model):

    PET_TYPE_CHOICES = (
        ('dog', 'Dog'),
        ('cat', 'Cat'),
        ('bird', 'Bird'),
        ('fish', 'Fish'),
        ('horse', 'Horse'),
        ('rabbit', 'Rabbit'),
        ('turtle', 'Turtle'),
        ('other', 'Other')
    )

    GENDER_CHOICES = (
        ('m', 'Male'),
        ('f', 'Female'),
    )

    # Required fields
    pet_id = models.CharField(
        max_length=63,
        unique=True,
        primary_key=True,
        validators=[
            MinLengthValidator(3),
            RegexValidator(
                regex='^[a-zA-Z0-9-]+$',
                message="Subdomain must be alphanumeric or contain dashes only."
            )
        ]
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    pet_name = models.CharField(max_length=255)
    pet_type = models.CharField(max_length=50, choices=PET_TYPE_CHOICES)

    # Optional fields
    birthday = models.DateField(null=True, blank=True)
    profile_pic_regular = models.URLField(null=True, blank=True)  # 512px
    profile_pic_thumbnail_small = models.URLField(
        null=True, blank=True)  # 100px
    gender = models.CharField(
        max_length=1, choices=GENDER_CHOICES, null=True, blank=True)
    bio = models.TextField(null=True, blank=True)

    # Automatically generated fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.pet_name} ({self.pet_type}) - {self.user.email}"

    class Meta:
        ordering = ['created_at']