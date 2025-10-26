from .views import home, user_home, events, purchase_product, purchase_event, register, activate
from .views import PasswordResetSESView, stripe_webhook, payment_confirmation
from django.urls import path

handler404 = "tridentapp.views.handler404"

urlpatterns = [

    # Forgot password form (SES-powered)
    path( 
        "accounts/password-reset/",
        PasswordResetSESView.as_view(),
        name="password_reset"
    ),

    # path('admin/', admin.site.urls),
    path('', home, name="home"),
    path('user/', user_home, name='user_home'),
    path('events/', events, name="events"),
    path("register/", register, name="register"),
    path("activate/<uidb64>/<token>/", activate, name="activate"),
    path('product/purchase/<int:product_id>/', purchase_product, name='purchase_product'),
    path('event/purchase/<int:event_id>/', purchase_event, name='purchase_event'),
    path("stripe/webhook/", stripe_webhook, name="stripe_webhook"),
    path("payment/confirmation/", payment_confirmation, name="payment_confirmation")

]


