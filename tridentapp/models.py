from django.db import models
from django.contrib.auth.models import User


class Event(models.Model):
    """ Event tickets can be purchased to be attended on a specific date """
    title = models.CharField(default='', max_length=255)
    date = models.DateTimeField()
    livestream_url = models.URLField(null=True, blank=True)
    content = models.TextField(default='', null=True, blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    purchasers = models.ManyToManyField(User, blank=True, related_name="purchased_events")

    def __str__(self):
        return f"{self.date} - {self.title}"


class Product(models.Model):
    """ A product is purchased and assigned to a user, e.g. a subscription """
    product_name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    purchasers = models.ManyToManyField(User, blank=True, related_name="purchased_products")

    def __str__(self):
        return self.product_name



