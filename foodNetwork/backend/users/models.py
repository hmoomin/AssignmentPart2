from django.contrib.auth.models import AbstractUser
from django.db import models
from products.utils import postcode_to_coords
from django.core.exceptions import ValidationError

class User(AbstractUser):
    ROLE_CHOICES = (
        ('customer', 'Customer'),
        ('producer', 'Producer'),
    )

    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    is_producer = models.BooleanField(default=False)
    address = models.CharField(max_length=255, blank=True)
    postcode = models.CharField(max_length=20, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    latitude = models.FloatField(null=True, blank=True)

def save(self, *args, **kwargs):
    if self.postcode:
        try:
            old = User.objects.get(pk=self.pk)
            postcode_changed = old.postcode != self.postcode
        except User.DoesNotExist:
            postcode_changed = True

        if postcode_changed:
            lat, lon = postcode_to_coords(self.postcode)

            if lat is None or lon is None:
                raise ValidationError("Invalid postcode entered")

            self.latitude = lat
            self.longitude = lon

    super().save(*args, **kwargs)
    