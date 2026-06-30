from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.core import validators
from django.core.validators import RegexValidator
from django.core.exceptions import ValidationError
from .models import UserProfile

User = get_user_model()

# Remove default Django username validators to allow custom characters
# This must be done at module import time
from django.contrib.auth.models import User
User._meta.get_field('username').validators = []

# Custom username validator that allows letters, numbers, and './+/-/_' characters
username_validator = RegexValidator(
    regex=r'^[a-zA-Z0-9./+_-]+$',
    message="Ingrese un nombre de usuario válido. Este valor solo puede contener letras, números y caracteres './+/-/_'.",
)

class RegisterForm(forms.Form):
    """Custom registration form that bypasses Django's default username validation"""
    username = forms.CharField(
        max_length=150,
        required=True,
        validators=[validators.MaxLengthValidator(50), username_validator],
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre de usuario'})
    )
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Correo electrónico'})
    )
    password1 = forms.CharField(
        label="Contraseña",
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Contraseña'}),
        validators=[validators.MinLengthValidator(10), validators.MaxLengthValidator(20)]
    )
    password2 = forms.CharField(
        label="Confirmar contraseña",
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Confirmar contraseña'})
    )

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if username:
            # Check if username already exists
            if User.objects.filter(username=username).exists():
                raise ValidationError("Ya existe un usuario con ese nombre de usuario.")
        return username

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email and User.objects.filter(email=email).exists():
            raise ValidationError("El correo actualmente pertenece a una cuenta ya creada.")
        return email

    def clean_password2(self):
        password1 = self.cleaned_data.get('password1')
        password2 = self.cleaned_data.get('password2')
        
        if password1 and password2 and password1 != password2:
            raise ValidationError("Las dos contraseñas no coinciden.")
        
        return password2

    def save(self):
        username = self.cleaned_data.get('username')
        email = self.cleaned_data.get('email')
        password = self.cleaned_data.get('password1')

        # Seguridad: bloqueo backend por correo único (aunque el formulario no haya validado)
        # Normalizamos a lower para evitar duplicados por mayúsculas/minúsculas.
        normalized_email = (email or "").strip().lower()
        if normalized_email and User.objects.filter(email__iexact=normalized_email).exists():
            raise ValidationError("El correo actualmente pertenece a una cuenta ya creada.")

        user = User.objects.create_user(
            username=username,
            email=normalized_email,
            password=password,
        )

        UserProfile.objects.create(user=user)
        return user


class VendorRegisterForm(forms.Form):
    """Vendor registration form with verification code"""
    username = forms.CharField(
        max_length=150,
        required=True,
        validators=[validators.MaxLengthValidator(150), username_validator],
        widget=forms.TextInput(attrs={
            'class': 'form-control', 
            'placeholder': 'Nombre de usuario'
        })
    )
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control', 
            'placeholder': 'Correo electrónico'
        })
    )
    phone = forms.CharField(
        min_length=10,
        max_length=20,
        required=True,
        validators=[
            # Solo dígitos (sin letras). No permitimos espacios/guiones.
            # Si el usuario escribe un '+', lo normalizamos en clean_phone.
            RegexValidator(
                regex=r'^\+?\d+$',
                message='El número de teléfono solo puede contener dígitos (y opcionalmente + al inicio).',
            ),
        ],
        widget=forms.TextInput(
            attrs={
                'class': 'form-control',
                'placeholder': 'Número de teléfono (mín 10, máx 20 dígitos)',
                'inputmode': 'numeric',
                'pattern': r'\+?\d{10,20}',
                'maxlength': '20',
            }
        )
    )

    store_name = forms.CharField(
        max_length=200,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control', 
            'placeholder': 'Nombre de la tienda'
        })
    )
    subrole = forms.ChoiceField(
        choices=UserProfile.SUBROLE_CHOICES,
        required=True,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    password1 = forms.CharField(
        label="Contraseña",
        widget=forms.PasswordInput(attrs={
            'class': 'form-control', 
            'placeholder': 'Contraseña'
        }),
        validators=[validators.MinLengthValidator(8), validators.MaxLengthValidator(128)]
    )
    password2 = forms.CharField(
        label="Confirmar contraseña",
        widget=forms.PasswordInput(attrs={
            'class': 'form-control', 
            'placeholder': 'Confirmar contraseña'
        })
    )


    def clean_username(self):
        username = self.cleaned_data.get('username')
        if username:
            if User.objects.filter(username=username).exists():
                raise ValidationError("Este nombre de usuario ya existe.")
        return username

    def clean_phone(self):
        phone = self.cleaned_data.get('phone')
        if not phone:
            return phone

        # Normalizamos para validar/guardar de forma consistente
        phone = phone.replace(' ', '').replace('-', '')

        # Permitimos opcionalmente '+' al inicio, pero rechazamos cualquier otra letra/caracter.
        if phone.startswith('+'):
            normalized = '+' + phone[1:].strip()
        else:
            normalized = phone.strip()

        if not normalized.startswith('+'):
            normalized = '+' + normalized

        # Validación estricta: después del posible '+', solo dígitos.
        digits = normalized[1:]
        if not digits.isdigit():
            raise ValidationError('El número de teléfono solo puede contener dígitos (y opcionalmente + al inicio).')

        # Validar longitudes (incluyendo el '+')
        if len(normalized) < 8:
            raise ValidationError("El número de teléfono debe tener mínimo 8 caracteres.")
        if len(normalized) > 20:
            raise ValidationError("El número de teléfono debe tener máximo 20 caracteres.")

        return normalized





    def clean_password2(self):
        password1 = self.cleaned_data.get('password1')
        password2 = self.cleaned_data.get('password2')
        
        if password1 and password2 and password1 != password2:
            raise ValidationError("Las contraseñas no coinciden.")
        
        return password2

    def save(self):
        username = self.cleaned_data.get('username')
        email = self.cleaned_data.get('email')
        password = self.cleaned_data.get('password1')
        phone = self.cleaned_data.get('phone')
        store_name = self.cleaned_data.get('store_name')
        subrole = self.cleaned_data.get('subrole')

        normalized_email = (email or "").strip().lower()
        if normalized_email and User.objects.filter(email__iexact=normalized_email).exists():
            raise ValidationError("El correo actualmente pertenece a una cuenta ya creada.")

        user = User.objects.create_user(
            username=username,
            email=normalized_email,
            password=password,
        )

        profile = UserProfile.objects.create(
            user=user,
            phone=phone,
            store_name=store_name,
            subrole=subrole,
            role='vendedor',
            status='pending'
        )

        return profile





class UserProfileForm(forms.ModelForm):
    username = forms.CharField(max_length=150, required=True)
    email = forms.EmailField(required=True)
    avatar = forms.ImageField(required=False, help_text="Sube una foto de perfil desde tu computadora")
    
    class Meta:
        model = UserProfile
        fields = ['phone', 'address', 'city', 'postal_code', 'avatar']
        widgets = {
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Número de teléfono'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Dirección', 'rows': 2}),
            'city': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ciudad'}),
            'postal_code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Código postal'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if hasattr(self, 'instance') and self.instance.user:
            self.fields['username'].initial = self.instance.user.username
            self.fields['email'].initial = self.instance.user.email

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if not email:
            return email

        normalized_email = email.strip().lower()
        current_user = getattr(getattr(self, 'instance', None), 'user', None)
        current_user_id = getattr(current_user, 'id', None)

        qs = User.objects.filter(email__iexact=normalized_email)
        if current_user_id is not None:
            qs = qs.exclude(id=current_user_id)

        if qs.exists():
            raise ValidationError("El correo actualmente pertenece a una cuenta ya creada.")

        return normalized_email



class ContactForm(forms.Form):
    name = forms.CharField(
        label="Nombre del usuario",
        max_length=150,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre del usuario'})
    )
    email = forms.EmailField(
        label="Correo del usuario",
        required=True,
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Correo del usuario'})
    )
    motivo = forms.CharField(
        label="Motivo de la queja",
        max_length=200,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Motivo de la queja'})
    )
    destinatario = forms.ChoiceField(
        label="A quien va dirigida la queja",
        choices=[('admin', 'Administrador'), ('seller', 'Vendedor')],
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    mensaje = forms.CharField(
        label="Mensaje",
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 5, 'placeholder': 'Describe tu queja...'})
    )
