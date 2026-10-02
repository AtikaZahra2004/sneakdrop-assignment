from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from .models import Hold, Waitlist, PaymentEvent

TOTAL_STOCK = 20
HOLD_MINUTES = 5
MAX_PURCHASES = 2


def pairs_left():
    used = Hold.objects.filter(status__in=[Hold.ACTIVE, Hold.PAID]).count()
    return TOTAL_STOCK - used


def paid_count(user_id):
    return Hold.objects.filter(user_id=user_id, status=Hold.PAID).count()


def has_active_hold(user_id):
    return Hold.objects.filter(user_id=user_id, status=Hold.ACTIVE).exists()


def new_hold(user_id):
    return Hold.objects.create(
        user_id=user_id,
        expires_at=timezone.now() + timedelta(minutes=HOLD_MINUTES),
    )


def process_expiry():
    """Purane holds expire karo, phir line ke pehle logon ko pair do."""
    Hold.objects.filter(
        status=Hold.ACTIVE, expires_at__lt=timezone.now()
    ).update(status=Hold.EXPIRED)

    while pairs_left() > 0:
        first = Waitlist.objects.order_by('id').first()
        if not first:
            break
        first.delete()
        if not has_active_hold(first.user_id) and paid_count(first.user_id) < MAX_PURCHASES:
            new_hold(first.user_id)


def buy(user_id):
    with transaction.atomic():
        process_expiry()
        if has_active_hold(user_id):
            return 'already_holding'
        if paid_count(user_id) >= MAX_PURCHASES:
            return 'limit_reached'
        if Waitlist.objects.filter(user_id=user_id).exists():
            return 'already_waiting'
        if pairs_left() > 0:
            new_hold(user_id)
            return 'held'
        Waitlist.objects.create(user_id=user_id)
        return 'waitlisted'


def payment_webhook(event_id, hold_id, status):
    with transaction.atomic():
        process_expiry()
        _, created = PaymentEvent.objects.get_or_create(event_id=event_id)
        if not created:
            return 'duplicate_ignored'
        if status != 'succeeded':
            return 'ignored'
        try:
            hold = Hold.objects.get(id=hold_id)
        except Hold.DoesNotExist:
            return 'unknown_hold'
        if hold.status == Hold.PAID:
            return 'already_paid'
        if hold.status != Hold.ACTIVE:
            return 'late_payment_rejected'
        if paid_count(hold.user_id) >= MAX_PURCHASES:
            return 'limit_reached'
        hold.status = Hold.PAID
        hold.save()
        return 'paid'