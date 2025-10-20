import os
import sys

sys.path.append('/var/www/vhost/trident.peeldev.com/trident')  
sys.path.append('/var/www/vhost/trident.peeldev.com/venv/lib/python3.12/site-packages') 

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'trident.settings')

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
