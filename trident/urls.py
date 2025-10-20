from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('tridentapp.urls')),
    path("accounts/", include("django.contrib.auth.urls")),
]


""" defaults:
/accounts/login/   - loads
/accounts/logout/  - errors?
/accounts/password_change/  - password_change_form.html
/accounts/password_change/done/    - bad template
/accounts/password_reset/  - WORKS
/accounts/password_reset/done/ - WORKS
/accounts/reset/<uidb64>/<token>/  - 
/accounts/reset/done/  - works
"""

