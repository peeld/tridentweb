from django.contrib import admin
from .models import Product, Event

import traceback


try:
    from django.contrib import admin
except Exception:
    traceback.print_exc()


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('product_name', 'price')
    search_fields = ('product_name', 'description')


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ['title', 'date']

    def image_tag(self, obj):
        if obj.image:
            return f'<img src="{obj.image.url}" width="100"/>'
        return "-"

    image_tag.allow_tags = True
    image_tag.short_description = 'Image'

