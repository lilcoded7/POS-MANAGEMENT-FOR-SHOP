from django.db import models
from setup.basemodel import BaseModel
from shop.models.orders import Order
from shop.models.products import Product


class OrderItem(BaseModel):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True)
    quantity = models.PositiveIntegerField(default=1)


    def __str__(self):
        return f"{self.quantity} x {self.product.name}"

    def get_total_product_price(self):
        product_price = self.quantity * self.product.selling_price
        return product_price or 0.00