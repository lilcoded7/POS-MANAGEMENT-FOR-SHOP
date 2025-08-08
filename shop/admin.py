from django.contrib import admin
from shop.models.orders import Order
from shop.models.order_items import OrderItem
from shop.models.products import Product, Category
# Register your models here.

class OrderAdmin(admin.ModelAdmin):
    list_display = ['status', 'total_price']


class OrderItemAdmin(admin.ModelAdmin):
    list_display = ['order', 'product', 'quantity', 'price']

class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'description', 'price', 'status']


admin.site.register(Order)
admin.site.register(OrderItem)
admin.site.register(Product)
admin.site.register(Category)