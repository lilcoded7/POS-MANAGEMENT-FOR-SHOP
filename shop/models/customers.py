from django.db import models
from setup.basemodel import BaseModel


class Customer(BaseModel):
    name = models.CharField(max_length=100, default='Customer')
    phone_number = models.CharField(max_length=100)
    location = models.CharField(max_length=100, null=True, blank=True)  

    def __str__(self):
        return f"Name: {self.name} Phone: {self.phone_number}"