from django.db import models
from setup.basemodel import BaseModel
from django.contrib.auth import get_user_model

User = get_user_model()


class Worker(BaseModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    email = models.EmailField(null=True, blank=True)
    phone_number = models.CharField(max_length=100)
    id_card = models.CharField(max_length=100)
    id_image = models.ImageField()

    def __str__(self):
        return f"Name: {self.name} Phone: {self.phone_number}"
