from setup.basemodel import BaseModel
from django.db import models


class Category(BaseModel):
    name = models.CharField(max_length=100)


class Product(BaseModel):
    STATUS = [
        ('active', 'Active (In Stock)'),
        ('inactive', 'Out of Stock'),
    ]
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, null=True, blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.PositiveIntegerField()
    image = models.ImageField(blank=True)

    def __str__(self):
        return f"Name: {self.name} Price: {self.price}"