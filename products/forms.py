from django import forms

from .models import Product, ProductDetails, FormRequest, Service


class ProductForm(forms.ModelForm):
    # Checkbox: si no viene en POST, Django lo interpreta como False.
    is_damaged = forms.BooleanField(required=False, initial=False, label="¿Producto dañado?")

    # Garantía: para permitir edición parcial, que no falle si no se envía.
    warranty_months = forms.ChoiceField(required=False)
    warranty_type = forms.ChoiceField(required=False)
    warranty_details = forms.CharField(
        required=False,
        widget=forms.Textarea(
            attrs={
                "class": "form-control",
                "rows": 3,
                "placeholder": "Detalles de la garantía...",
            }
        ),
    )

    # "Más detalles del producto" (ProductDetails)
    referencias = forms.CharField(required=False, widget=forms.Textarea(
        attrs={"class": "form-control", "rows": 3, "placeholder": "Referencias del producto..."}
    ))
    especificaciones_tecnicas = forms.CharField(required=False, widget=forms.Textarea(
        attrs={"class": "form-control", "rows": 3, "placeholder": "Especificaciones técnicas..."}
    ))
    caracteristicas = forms.CharField(required=False, widget=forms.Textarea(
        attrs={"class": "form-control", "rows": 3, "placeholder": "Características..."}
    ))
    contenido_caja = forms.CharField(required=False, widget=forms.Textarea(
        attrs={"class": "form-control", "rows": 3, "placeholder": "Contenido de la caja..."}
    ))
    compatibilidades = forms.CharField(required=False, widget=forms.Textarea(
        attrs={"class": "form-control", "rows": 3, "placeholder": "Compatibilidades..."}
    ))
    dimensiones = forms.CharField(required=False, widget=forms.Textarea(
        attrs={"class": "form-control", "rows": 3, "placeholder": "Dimensiones..."}
    ))
    materiales = forms.CharField(required=False, widget=forms.Textarea(
        attrs={"class": "form-control", "rows": 3, "placeholder": "Materiales..."}
    ))
    garantia_detalle = forms.CharField(required=False, widget=forms.Textarea(
        attrs={"class": "form-control", "rows": 3, "placeholder": "Garantía (detalle adicional)..."}
    ))
    otras_comentarios = forms.CharField(required=False, widget=forms.Textarea(
        attrs={"class": "form-control", "rows": 3, "placeholder": "Otras observaciones..."}
    ))

    class Meta:
        model = Product
        exclude = ["seller"]
        widgets = {
            "name": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Nombre del producto"}
            ),
            "description": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "placeholder": "Descripción del producto",
                    "rows": 4,
                }
            ),
            "price": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "step": "0.01",
                    "placeholder": "Precio",
                    "min": "0",
                }
            ),
            "image_url": forms.URLInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "https://ejemplo.com/imagen.jpg",
                }
            ),
            "category": forms.Select(attrs={"class": "form-control"}),
            "stock": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Cantidad en stock",
                    "min": "0",
                }
            ),
            "image": forms.ClearableFileInput(attrs={"class": "form-control"}),
            "is_featured": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "is_service": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "is_damaged": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "warranty_months": forms.Select(attrs={"class": "form-control"}),
            "warranty_type": forms.Select(attrs={"class": "form-control"}),
            "warranty_details": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                    "placeholder": "Detalles de la garantía...",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Prefill de ProductDetails si existe
        instance = getattr(self, "instance", None)
        if instance and getattr(instance, "pk", None):
            try:
                details = instance.details
            except ProductDetails.DoesNotExist:
                details = None

            if details:
                self.fields["referencias"].initial = details.referencias
                self.fields["especificaciones_tecnicas"].initial = details.especificaciones_tecnicas
                self.fields["caracteristicas"].initial = details.caracteristicas
                self.fields["contenido_caja"].initial = details.contenido_caja
                self.fields["compatibilidades"].initial = details.compatibilidades
                self.fields["dimensiones"].initial = details.dimensiones
                self.fields["materiales"].initial = details.materiales
                self.fields["garantia_detalle"].initial = details.garantia_detalle
                self.fields["otras_comentarios"].initial = details.otras_comentarios

    def save(self, commit=True):
        product = super().save(commit=commit)

        # Guardar/crear details
        details_data = {
            "referencias": self.cleaned_data.get("referencias", ""),
            "especificaciones_tecnicas": self.cleaned_data.get("especificaciones_tecnicas", ""),
            "caracteristicas": self.cleaned_data.get("caracteristicas", ""),
            "contenido_caja": self.cleaned_data.get("contenido_caja", ""),
            "compatibilidades": self.cleaned_data.get("compatibilidades", ""),
            "dimensiones": self.cleaned_data.get("dimensiones", ""),
            "materiales": self.cleaned_data.get("materiales", ""),
            "garantia_detalle": self.cleaned_data.get("garantia_detalle", ""),
            "otras_comentarios": self.cleaned_data.get("otras_comentarios", ""),
        }

        details, _ = ProductDetails.objects.get_or_create(product=product)
        for k, v in details_data.items():
            setattr(details, k, v)
        details.save()

        return product


class FormRequestForm(forms.ModelForm):
    device_model = forms.ModelChoiceField(
        queryset=Product.objects.all(),
        empty_label="Seleccione el producto",
        label="Modelo del dispositivo",
        widget=forms.Select(attrs={
            "class": "form-control-custom",
        }),
        required=True,
    )

    issue_description = forms.CharField(
        widget=forms.Textarea(
            attrs={
                "class": "form-control-custom",
                "rows": 5,
                "placeholder": "Describa el problema detalladamente. ¿Cuándo empezó? ¿Qué síntomas presenta? ¿Ya intentó algo?",
            }
        ),
        label="Descripción del problema",
        required=True,
    )

    images = forms.FileField(
        label="Fotos del dispositivo (opcional)",
        widget=forms.FileInput(attrs={"class": "form-control-custom"}),
        required=False,
        help_text="Puede subir múltiples fotos (máx 5MB total)",
    )

    phone = forms.CharField(
        max_length=20,
        required=True,
        strip=True,
        widget=forms.TextInput(attrs={
            "class": "form-control-custom",
            "placeholder": "+57 312 565 6485",
        }),
        error_messages={"required": "Este campo no puede estar en blanco."},
    )

    email = forms.EmailField(required=False, widget=forms.HiddenInput())
    customer_name = forms.CharField(max_length=200, required=False, widget=forms.HiddenInput())

    service_type = forms.CharField(widget=forms.HiddenInput(), required=False)
    issue_type = forms.CharField(widget=forms.HiddenInput(), required=False)
    service_option = forms.CharField(widget=forms.HiddenInput(), required=False)
    priority = forms.CharField(widget=forms.HiddenInput(), initial="normal", required=False)
    description = forms.CharField(widget=forms.HiddenInput(), required=False)

    class Meta:
        model = FormRequest
        fields = [
            "device_model",
            "issue_description",
            "images",
            "phone",
            "email",
            "customer_name",
            "service_type",
            "issue_type",
            "service_option",
            "priority",
            "description",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["device_model"].label = "📱 Modelo del dispositivo"
        self.fields["issue_description"].label = "🔍 Descripción detallada del problema"
        self.fields["images"].label = "📸 Fotos del problema (opcional)"
        self.fields["phone"].label = "📞 Teléfono de contacto"

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.customer_name = self.cleaned_data.get("customer_name")
        instance.phone = self.cleaned_data["phone"]
        instance.email = self.cleaned_data.get("email", "")
        instance.device = str(self.cleaned_data["device_model"])
        instance.description = self.cleaned_data["issue_description"]

        if self.files.getlist("images"):
            instance.files = [f.name for f in self.files.getlist("images")]

        if commit:
            instance.save()
        return instance


class ServiceForm(forms.ModelForm):
    class Meta:
        model = Service
        exclude = ["seller"]
        widgets = {
            "name": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Nombre del servicio"}
            ),
            "description": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "placeholder": "Descripción del servicio",
                    "rows": 4,
                }
            ),
            "price": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "step": "0.01",
                    "placeholder": "Precio",
                    "min": "0",
                }
            ),
            "image_url": forms.URLInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "https://ejemplo.com/imagen.jpg",
                }
            ),
        }

