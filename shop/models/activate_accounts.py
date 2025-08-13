from django.db import models
from setup.basemodel import BaseModel

class ActivateAccount(BaseModel):
    code = models.CharField(max_length=100)
    is_expired = models.BooleanField(default=True)

    