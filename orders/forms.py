from django import forms
from .models import WarrantyClaim


class WarrantyClaimForm(forms.ModelForm):
    class Meta:
        model = WarrantyClaim
        fields = [
            "damage_type",
            "damage_description",
            "condition_when_received",
            "claim_type",
            "observations",
        ]
        widgets = {
            "damage_type": forms.RadioSelect(),
            "condition_when_received": forms.RadioSelect(),
            "claim_type": forms.RadioSelect(),
            "damage_description": forms.Textarea(
                attrs={
                    "rows": 3,
                    "placeholder": " Describe el daño...",
                    "style": "width: 100%; padding: 10px; border-radius: 6px; border: 1px solid #ddd;",
                }
            ),
            "observations": forms.Textarea(
                attrs={
                    "rows": 3,
                    "placeholder": " Observaciones adicionales...",
                    "style": "width: 100%; padding: 10px; border-radius: 6px; border: 1px solid #ddd;",
                }
            ),
        }
