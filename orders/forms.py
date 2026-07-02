from django import forms


class OrderVendorMessageForm(forms.Form):
    message = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 5, "style": "width: 100%;"}),
        required=False,
        label="Mensaje del vendedor",
    )

