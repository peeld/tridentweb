from django.utils import timezone
from django.utils.timezone import now
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_decode
from django.conf import settings
from django.http import HttpResponse
from django.contrib.auth import views as auth_views
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from django.contrib import messages
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes


from .forms import RegisterForm
from .forms import SESEmailPasswordResetForm
from .models import Event, Product, Customer
from .utils import send_new_account_email, send_purchase_email, send_admin_email

import pytz
import stripe
from decimal import Decimal

stripe.api_key = settings.STRIPE_SECRET_KEY


def get_or_create_stripe_customer(user):
    customer_obj, created = Customer.objects.get_or_create(user=user)
    if created or not customer_obj.stripe_customer_id:
        stripe_customer = stripe.Customer.create(
            email=user.email,
            name=user.get_full_name() or user.username,
        )
        customer_obj.stripe_customer_id = stripe_customer.id
        customer_obj.save()
    return customer_obj.stripe_customer_id


def home(request):
    future_events = Event.objects.filter(date__gt=timezone.now()).order_by('date')
    return render(request, 'home.html', {'events': future_events})


def directions(request):
    return render(request, 'directions.html')


@login_required
def user_home(request):
    products = request.user.purchased_products.all()
    events = request.user.purchased_events.all()
    return render(request, "user_home.html", {"products": products, "events": events})


def register(request):
    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.is_active = False  # deactivate until confirmed
            user.save()
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)
            confirm_url = request.build_absolute_uri(f"/activate/{uid}/{token}/")
            send_new_account_email(user, confirm_url)
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


class PasswordResetSESView(auth_views.PasswordResetView):
    form_class = SESEmailPasswordResetForm
    template_name = "registration/password_reset_form.html"
    email_template_name = "registration/password_reset_email.txt"
    html_email_template_name = "registration/password_reset_email.html"
    subject_template_name = "registration/password_reset_subject.txt"


def events(request):
    events = (
        Event.objects.filter(date__gte=timezone.now())
        .order_by("date")
    )

    return render(request, "events.html", {"events": events})


def event_info(request, event_id):
    event = get_object_or_404(Event, pk=event_id)
    return render(request, "event_info.html", {"event": event})


def livestream(request):
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
        'past_events': past_events,
        'next_event': next_event,
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


def event_register(request, event_id):
    event = get_object_or_404(Event, pk=event_id)

    # If user not logged in → redirect to login page with "next" param
    if not request.user.is_authenticated:
        login_url = f"{reverse('login')}?next={request.path}"
        return redirect(login_url)

    # Handle POST registration (after login)
    if request.method == "POST":
        if request.user not in event.purchasers.all():
            event.purchasers.add(request.user)
            messages.success(request, f"You have successfully registered for {event.title}!")
        else:
            messages.info(request, "You are already registered for this event.")
        return redirect("event_info", event_id=event.id)

    # Determine if already registered
    already_registered = request.user in event.purchasers.all()

    return render(request, "event_register.html", {
        "event": event,
        "already_registered": already_registered,
    })


def purchase_event(request, event_id):
    event = get_object_or_404(Event, pk=event_id)
    quantity = int(request.POST.get("quantity", 1))
    promo_code = request.POST.get("promo", "").strip()
    action = request.POST.get("action", "")
    email = request.POST.get("email", "")
    login_error = ""

    # Apply promo if valid for this event
    promo_message = ""
    discount = Decimal('0')
    if promo_code:
        if event.promo_code and promo_code == event.promo_code.upper():
            discount = event.promo_discount
            promo_message = f"{event.promo_discount}% discount applied"
        else:
            promo_message = "Invalid code"

    # Calculate discounted total
    base_price = event.price * quantity
    discounted_price = base_price * (Decimal('1') - discount / Decimal('100'))
    total_display = f"${discounted_price:.2f}"

    if action == "continue":
        # Store chosen data in session and redirect to payment
        request.session["purchase_data"] = {
            "quantity": quantity,
            "promo_code": promo_code,
            "email": email,
        }
        return redirect(reverse("pay_event", args=[event_id]))

    return render(request, "event_purchase.html", {
        "event": event,
        "quantity": quantity,
        "promo_code": promo_code,
        "promo_message": promo_message,
        "amount_display": total_display,
        "login_error": login_error,
        "discounted_price": discounted_price,
        "email": email
    })


def pay_event(request, event_id):
    event = get_object_or_404(Event, pk=event_id)
    data = request.session.get("purchase_data")

    if not data:
        return redirect("purchase_event", event_id=event.id)

    quantity = int(data["quantity"])
    promo_code = data.get("promo_code", "")
    email = data.get("email", "")
    discount = Decimal('0')

    if promo_code and event.promo_code and promo_code == event.promo_code.upper():
        discount = event.promo_discount

    base_price = event.price * quantity
    discounted_price = base_price * (Decimal('1') - discount / Decimal('100'))
    amount_cents = int(discounted_price * 100)
    amount_display = f"${discounted_price:.2f}"

    # Stripe customer
    if request.user.is_authenticated:
        customer_id = get_or_create_stripe_customer(request.user)
        email = request.user.email
    else:
        customer_id = None

    # Create PaymentIntent
    intent = stripe.PaymentIntent.create(
        amount=amount_cents,
        currency="usd",
        customer=customer_id,
        automatic_payment_methods={"enabled": True},
        metadata={
            "email": email,
            "event": event.id,
            "quantity": quantity,
            "user_id": request.user.id if request.user.is_authenticated else None,
            "promo_code": promo_code,
        },
    )

    context = {
        "event": event,
        "quantity": quantity,
        "promo_code": promo_code,
        "email": email,
        "amount_display": amount_display,
        "client_secret": intent.client_secret,
        "STRIPE_PUBLISHABLE_KEY": settings.STRIPE_PUBLISHABLE_KEY,
    }
    return render(request, "event_payment.html", context)


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
        user_id = intent["metadata"].get("user_id")
        quantity = intent["metadata"].get("quantity")
        charges = intent.get("charges", {}).get("data", [])

        # Product
        product_id = intent["metadata"].get("product_id")
        if product_id:
            try:
                product = Product.objects.get(pk=product_id)
            except Product.DoesNotExist:
                return HttpResponse(status=200)

            # Assign product to the user (ManyToMany example)
            if user_id:
                try:
                    user = User.objects.get(pk=user_id)
                    product.purchasers.add(user)
                except User.DoesNotExist:
                    pass

        # Event
        event_id = intent["metadata"].get("event")
        if event_id:
            try:
                event = Event.objects.get(pk=event_id)
            except Event.DoesNotExist:
                return HttpResponse(status=200)

            email = None
            name = None

            # Assign event to user
            if user_id:
                try:
                    user = User.objects.get(pk=user_id)
                    name = user.name
                    email = user.email
                    event.purchasers.add(user)
                except User.DoesNotExist:
                    pass
            else:
                if charges:
                    email = charges[0].get("billing_details", {}).get("email")
                    name = charges[0].get("billing_details", {}).get("name")

            if email:
                send_purchase_email(email, f"{event.title} {event.date}")

            send_admin_email("New Event Purchase", f"{event.title} {quantity} {email} {name} ")

    elif event["type"] == "payment_intent.payment_failed":
        intent = event["data"]["object"]
        print(f"Payment failed for intent: {intent['id']}")

    # You can handle other event types if needed

    return HttpResponse(status=200)


def payment_confirmation(request):
    intent_id = request.GET.get("intent")
    # Optionally show payment details here
    return render(request, "payment_confirmation.html", {"intent_id": intent_id})


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
