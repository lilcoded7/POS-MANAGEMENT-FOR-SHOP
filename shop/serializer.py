from rest_framework import serializers
from shop.models.activate_accounts import ActivateAccount

class ActivateAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = ActivateAccount
        fields = '__all__'