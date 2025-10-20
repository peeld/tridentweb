

from django.utils import timezone
from django.utils.timezone import now
from django.conf import settings
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from django.contrib.auth import views as auth_views
from django.contrib.auth.models import User
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes
from django.contrib.auth.tokens import default_token_generator
from django.template.loader import render_to_string
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt

from .forms import RegisterForm
from .forms import SESEmailPasswordResetForm
from .models import Event, Product

import pytz
import stripe
import boto3

stripe.api_key = settings.STRIPE_SECRET_KEY


def home(request):
    future_events = Event.objects.filter(date__gt=timezone.now()).order_by('date')
    return render(request, 'home.html', {'events': future_events})


@login_required
def user_home(request):
    products = request.user.purchased_products.all()
    return render(request, "user_home.html", {"products": products})


def register(request):
    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.is_active = False  # deactivate until confirmed
            user.save()
            send_confirmation_email(user, request)
            return render(request, "registration/registration_pending.html")
    else:
        form = RegisterForm()
    return render(request, "registration/register.html", {"form": form})
    
    
def activate(request, uidb64, token):
    try:
        uid = urlsafe_base64_decode(uidb64).decode()
        user = User.objects.get(pk=uid)
    except (User.DoesNotExist, ValueError, TypeError, OverflowError):
        user = None

    if user and default_token_generator.check_token(user, token):
        user.is_active = True
        user.save()
        return redirect("login")  # or dashboard
    else:
        return render(request, "registration/activation_invalid.html")    

    
def send_confirmation_email(user, request):
    token = default_token_generator.make_token(user)
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    confirm_url = request.build_absolute_uri(f"/activate/{uid}/{token}/")

    subject = "Confirm your account"
    body_text = render_to_string("registration/activation_email.txt", {
        "user": user,
        "confirm_url": confirm_url,
    })


    # Create boto3 SES client
    ses_client = boto3.client(
        "ses",
        aws_access_key_id=settings.SES_MOCAPSCHOOL_KEY,
        aws_secret_access_key=settings.SES_MOCAPSCHOOL_SECRET,
        region_name=settings.SES_MOCAPSCHOOL_REGION,
    )

    # Send email using AWS SES API
    ses_client.send_email(
        Source=settings.DEFAULT_FROM_EMAIL,
        Destination={
            "ToAddresses": [user.email],
        },
        Message={
            "Subject": {"Data": subject, "Charset": "UTF-8"},
            "Body": {
                "Text": {"Data": body_text, "Charset": "UTF-8"},
            },
        },
    )    


class PasswordResetSESView(auth_views.PasswordResetView):
    form_class = SESEmailPasswordResetForm
    template_name = "registration/password_reset_form.html"
    email_template_name = "registration/password_reset_email.txt"
    html_email_template_name = "registration/password_reset_email.html"
    subject_template_name = "registration/password_reset_subject.txt"


def events(request):
    """Renders a page listing past livestreams, and identifies current and next upcoming livestreams."""
    pacific = pytz.timezone('America/Los_Angeles')
    current_time = now().astimezone(pacific)
    current_date = current_time.date()
    current_clock_time = current_time.time()

    events = Event.objects.all().order_by('-date')

    past_events = []
    next_event = None
    current_event = None

    for event in events:
        event_dt = event.date.astimezone(pacific)
        event_date = event_dt.date()
        event_time = event_dt.time()

        if event_date == current_date and event_time <= current_clock_time:
            # This is the current livestream (today, and already started)
            current_event = {
                'title': event.title,
                'url': event.livestream_url,
                'start_time': event_dt.isoformat()
            }
        elif event_dt > current_time:
            # This is the next upcoming livestream
            delta = event_dt - current_time
            starts_in = None
            if event_date == current_date:
                hours, remainder = divmod(delta.total_seconds(), 3600)
                minutes = remainder // 60
                starts_in = f"in {int(hours)} hour{'s' if hours != 1 else ''} {int(minutes)} minute{'s' if minutes != 1 else ''}"

            next_livestream = {
                'title': event.title,
                'url': event.livestream_url,
                'redirect_time': event_dt.isoformat(),
                'starts_in': starts_in
            }
        else:
            # This is a past livestream
            past_events.append(event)

    return render(request, 'livestream.html', {
        'livestreams': past_events,
        'next_livestream': next_event,
        'current_livestream': current_event,
    })

@login_required
def purchase_product(request, product_id):
    # Get the product or return 404 if not found
    product = get_object_or_404(Product, pk=product_id)

    # Convert price (Decimal) to integer cents
    amount_cents = int(product.price * 100)
    amount_display = f"${product.price:.2f}"

    # Create a Stripe PaymentIntent
    intent = stripe.PaymentIntent.create(
        amount=amount_cents,
        currency="usd",
        automatic_payment_methods={"enabled": True},
        metadata={
            "product": product.id,
            "user_id": request.user.id if request.user.is_authenticated else None,
        },
    )

    return render(request, "payment.html", {
        "client_secret": intent.client_secret,
        "STRIPE_PUBLISHABLE_KEY": settings.STRIPE_PUBLISHABLE_KEY,
        "amount_display": amount_display,
        "item_name": product.product_name,
    })


def purchase_event(request, event_id):
    # Get the product or return 404 if not found
    event = get_object_or_404(Event, pk=event_id)

    # Convert price (Decimal) to integer cents
    amount_cents = int(event.price * 100)
    amount_display = f"${event.price:.2f}"

    # Create a Stripe PaymentIntent
    intent = stripe.PaymentIntent.create(
        amount=amount_cents,
        currency="usd",
        automatic_payment_methods={"enabled": True},
        metadata={
            "event": event.id,
            "user_id": request.user.id if request.user.is_authenticated else None,
        },
    )

    return render(request, "payment.html", {
        "client_secret": intent.client_secret,
        "STRIPE_PUBLISHABLE_KEY": settings.STRIPE_PUBLISHABLE_KEY,
        "amount_display": amount_display,
        "item_name": event.title,
    })


def create_checkout_session(request):
    session = stripe.checkout.Session.create(
        payment_method_types=['card'],
        line_items=[{
            'price_data': {
                'currency': 'usd',
                'product_data': {
                    'name': 'Test product',
                },
                'unit_amount': 2000,  # $20.00
            },
            'quantity': 1,
        }],
        mode='payment',
        success_url='http://127.0.0.1:8000/success/',
        cancel_url='http://127.0.0.1:8000/cancel/',
    )
    return redirect(session.url, code=303)


@csrf_exempt  # Stripe doesn't send CSRF tokens
def stripe_webhook(request):
    payload = request.body
    sig_header = request.META.get("HTTP_STRIPE_SIGNATURE")

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except ValueError:
        # Invalid payload
        return HttpResponse(status=400)
    except stripe.error.SignatureVerificationError:
        # Invalid signature
        return HttpResponse(status=400)

    # Handle the event types you care about
    if event["type"] == "payment_intent.succeeded":
        intent = event["data"]["object"]
        product_id = intent["metadata"].get("product_id")
        user_id = intent["metadata"].get("user_id")

        try:
            product = Product.objects.get(pk=product_id)
        except Product.DoesNotExist:
            return HttpResponse(status=200)

        # Assign product to the user (ManyToMany example)
        if user_id:
            from django.contrib.auth.models import User
            try:
                user = User.objects.get(pk=user_id)
                product.purchasers.add(user)
            except User.DoesNotExist:
                pass

        # Optionally decrement stock
        if product.units > 0:
            product.units -= 1
            product.save()

    elif event["type"] == "payment_intent.payment_failed":
        intent = event["data"]["object"]
        print(f"Payment failed for intent: {intent['id']}")

    # You can handle other event types if needed

    return HttpResponse(status=200)


def handler404(request, exception=None):
    def collect(urls):
        patterns = []
        for u in urls:
            if isinstance(u, URLPattern):
                patterns.append(u)
            elif isinstance(u, URLResolver):
                patterns.extend(collect(u.url_patterns))
        return patterns

    patterns = collect(get_resolver().url_patterns)
    return render(request, "404.html", {"urls": patterns}, status=404)