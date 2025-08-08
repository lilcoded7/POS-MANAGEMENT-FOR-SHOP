from shop.models.orders import Order
from django.db import models
from setup.basemodel import BaseModel


class Report(BaseModel):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, null=True, blank=True)
    context = models.TextField()
    dec = models.TextField(null=True, blank=True)

    def __str__(self):
        return f"{self.context} "
