from .views import home, user_home, events, purchase_product, purchase_event, pay_event
from .views import PasswordResetSESView, stripe_webhook, payment_confirmation
from .views import event_info, event_register, directions, register, activate
from django.urls import path

handler404 = "tridentapp.views.handler404"

urlpatterns = [

    # Forgot password form (SES-powered)
    path( 
        "accounts/password-reset/",
        PasswordResetSESView.as_view(),
        name="password_reset"
    ),

    path('', home, name="home"),
    path('user/', user_home, name='user_home'),
    path('events/', events, name="events"),
    path('directions/', directions, name="directions"),
    path('event_info/<int:event_id>', event_info, name="event_info"),
    path("register/", register, name="register"),
    path("activate/<uidb64>/<token>/", activate, name="activate"),
    path('product/purchase/<int:product_id>/', purchase_product, name='purchase_product'),
    path('event/<int:event_id>/purchase/', purchase_event, name='purchase_event'),
    path('event/<int:event_id>/pay/', pay_event, name='pay_event'),
    path('event_register/<int:event_id>/', event_register, name='event_register'),
    path("stripe/webhook/", stripe_webhook, name="stripe_webhook"),
    path("payment/confirmation/", payment_confirmation, name="payment_confirmation"),

]


