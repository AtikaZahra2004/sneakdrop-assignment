import json
import uuid

from django.db import transaction
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt

from . import services
from .models import Hold, Waitlist


def home(request):
    user = request.GET.get('user', '').strip()
    msg = request.GET.get('msg', '')

    with transaction.atomic():
        services.process_expiry()
        left = services.pairs_left()

    html = "<h2>Sneaker Drop</h2>"
    html += f"<p>Pairs left: <b>{left}</b></p>"
    if msg:
        html += f"<p>Message: <b>{msg}</b></p>"

    html += """
    <form method="get">
        Your user id: <input name="user" value="{u}">
        <button>Check my status</button>
    </form><hr>
    """.format(u=user)

    if user:
        hold = Hold.objects.filter(user_id=user, status=Hold.ACTIVE).first()
        entry = Waitlist.objects.filter(user_id=user).first()
        bought = services.paid_count(user)

        html += f"<p>User: <b>{user}</b> | Pairs bought: {bought}/2</p>"

        if hold:
            secs = int((hold.expires_at - timezone.now()).total_seconds())
            html += f"<p>Your hold ends in: <b id='t'>{secs}</b> seconds</p>"
            html += """
            <form method="post" action="/pay/">
                <input type="hidden" name="hold_id" value="{h}">
                <input type="hidden" name="user_id" value="{u}">
                <button>Pay now (fake)</button>
            </form>
            <script>
              var s = {s};
              setInterval(function(){{
                s = s - 1;
                if (s < 0) {{ location.reload(); }}
                document.getElementById('t').innerText = s;
              }}, 1000);
            </script>
            """.format(h=hold.id, u=user, s=secs)
        elif entry:
            pos = Waitlist.objects.filter(id__lte=entry.id).count()
            html += f"<p>You are in the waiting line. Your place: <b>{pos}</b></p>"
            html += "<p>(Page refresh karte raho, hold milte hi yahan dikhega)</p>"
        else:
            html += """
            <form method="post" action="/buy/">
                <input type="hidden" name="user_id" value="{u}">
                <button>Buy</button>
            </form>
            """.format(u=user)

    return HttpResponse(html)


@csrf_exempt
def buy_view(request):
    user = request.POST.get('user_id', '').strip()
    if not user:
        return redirect('/')
    result = services.buy(user)
    return redirect(f'/?user={user}&msg={result}')


@csrf_exempt
def pay_view(request):
    """Fake payment company: webhook ko 'payment succeeded' message bhejta hai."""
    user = request.POST.get('user_id', '')
    hold_id = request.POST.get('hold_id')
    result = services.payment_webhook(str(uuid.uuid4()), hold_id, 'succeeded')
    return redirect(f'/?user={user}&msg={result}')


@csrf_exempt
def webhook_view(request):
    """Payment company yahan JSON bhejti hai: event_id, hold_id, status."""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST only'}, status=405)
    try:
        data = json.loads(request.body)
        result = services.payment_webhook(
            data['event_id'], data['hold_id'], data['status']
        )
    except (ValueError, KeyError):
        return JsonResponse({'error': 'bad request'}, status=400)
    return JsonResponse({'result': result})