from django.db import models
from setup.basemodel import BaseModel



class Order(BaseModel):
    status_choices = [
        ('pending', 'Pending'),
        ('success', 'success'),
        ('wish_list', 'Wish List'),
    ]
    status = models.CharField(max_length=20, choices=status_choices, default='pending')
    total_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    def __str__(self):
        return f"Order #{self.id} by "
    

    def get_total_price(self):
        total_order_price = sum(item.get_total_product_price() for item in self.items.all())
        return total_order_price or 0.00




