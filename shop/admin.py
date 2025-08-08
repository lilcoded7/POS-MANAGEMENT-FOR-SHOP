from django.contrib import admin
from shop.models.orders import Order
from shop.models.order_items import OrderItem
from shop.models.products import Product, Category
from shop.models.workers import Worker
from shop.models.reports import Report
from shop.models.cancel_order import CancelOrder
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
admin.site.register(Worker)
admin.site.register(Report)
admin.site.register(CancelOrder)