from django.db import models


class Hold(models.Model):
    ACTIVE = 'ACTIVE'
    PAID = 'PAID'
    EXPIRED = 'EXPIRED'

    user_id = models.CharField(max_length=50)
    status = models.CharField(max_length=10, default=ACTIVE)
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)


class Waitlist(models.Model):
    user_id = models.CharField(max_length=50, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)


class PaymentEvent(models.Model):
    event_id = models.CharField(max_length=100, unique=True)