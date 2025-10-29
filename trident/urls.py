from django.contrib import admin
from django.urls import path, include
from django.conf.urls.static import static
from django.conf import settings

urlpatterns = [
    path('admin/', admin.site.urls),
    path('ckeditor5/', include('django_ckeditor_5.urls')),
    path("accounts/", include("django.contrib.auth.urls")),

    path('', include('tridentapp.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)


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

