from django import forms
from shop.models.cancel_order import CancelOrder


class CancelOrderForm(forms.Form):
    reason = forms.ModelChoiceField(
        queryset=CancelOrder.objects.all(),
        required=True,
        widget=forms.Select(
            attrs={
                'class': 'form-control',
                'placeholder': 'Select a reason'
            }
        )
    )
    context = forms.CharField(
        required=False,
        widget=forms.Textarea(
            attrs={
                'class': 'form-control',
                'placeholder': 'Optional notes about the cancellation'
            }
        )
    )
