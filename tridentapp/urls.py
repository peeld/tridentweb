from .views import home, user_home, events, purchase_product, purchase_event, register, activate
from .views import PasswordResetSESView, stripe_webhook, payment_confirmation, recalculate_event
from .views import event_info
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
    path('event_info/<int:event_id>', event_info, name="event_info"),
    path("register/", register, name="register"),
    path("activate/<uidb64>/<token>/", activate, name="activate"),
    path('product/purchase/<int:product_id>/', purchase_product, name='purchase_product'),
    path('event/purchase/<int:event_id>/', purchase_event, name='purchase_event'),
    path("stripe/webhook/", stripe_webhook, name="stripe_webhook"),
    path("payment/confirmation/", payment_confirmation, name="payment_confirmation"),
    path("api/events/<int:event_id>/recalculate/", recalculate_event, name="recalculate_event"),

]


