from django.db import models
from django.contrib.auth.models import User
from django.conf import settings
import random
import string

class UserProfile(models.Model):
    ROLE_CHOICES = [
        ('cliente', 'Cliente'),
        ('vendedor', 'Vendedor'),
        ('admin', 'Administrador'),
    ]
    
    SUBROLE_CHOICES = [
        ('general', 'General'),
        ('cajero', 'Cajero'),
        ('inventario', 'Inventario'),
        ('gerente', 'Gerente'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pendiente de verificación'),
        ('verified', 'Verificado'),
        ('blocked', 'Bloqueado'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    phone = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    postal_code = models.CharField(max_length=20, blank=True)
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True, help_text="Foto de perfil")
    
    # Role system
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='cliente')
    subrole = models.CharField(max_length=20, choices=SUBROLE_CHOICES, default='general')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='cliente')
    
    # Verification
    verification_code = models.CharField(max_length=6, blank=True, null=True)
    code_expires_at = models.DateTimeField(blank=True, null=True)
    is_verified = models.BooleanField(default=False)
    approved_by_admin = models.BooleanField(default=False)
    
    # Vendor specific fields
    store_name = models.CharField(max_length=200, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Perfil de {self.user.username} ({self.get_role_display()})"
    
    def generate_verification_code(self):
        """Generate a 6-digit verification code"""
        self.verification_code = ''.join(random.choices(string.digits, k=6))
        from django.utils import timezone
        from datetime import timedelta
        self.code_expires_at = timezone.now() + timedelta(minutes=30)
        self.save()
        return self.verification_code
    
    def send_verification_whatsapp(self):
        """Generate and log verification code for admin manual approval (Twilio removed)"""
        code = self.generate_verification_code()
        print(f"🔐 TECHSTORE - Nuevo vendedor requiere aprobación")
        print(f"👤 Usuario: {self.user.username}")
        print(f"🏪 Tienda: {self.store_name or 'No especificada'}")
        print(f"📱 Teléfono: {self.phone}")
        print(f"✋ CÓDIGO DE VERIFICACIÓN: {code}")
        print(f"⏰ Expira: {self.code_expires_at}")
        print("Para aprobar: Login admin -> admin_vendors -> Approve")
        print("-" * 60)
        return True, code
    
    def is_admin(self):
        return self.role == 'admin' or self.user.is_superuser
    
    def is_vendedor(self):
        return self.role == 'vendedor' and self.is_verified and self.approved_by_admin
    
    def is_cliente(self):
        return self.role == 'cliente'

class Complaint(models.Model):
    name = models.CharField(max_length=150, verbose_name="Nombre del usuario")
    email = models.EmailField(verbose_name="Correo del usuario")
    motivo = models.CharField(max_length=200, verbose_name="Motivo de la queja")
    destinatario = models.CharField(
        max_length=10,
        choices=[('admin', 'Administrador'), ('seller', 'Vendedor')],
        verbose_name="A quien va dirigida"
    )
    mensaje = models.TextField(verbose_name="Mensaje")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de creación")
    deadline = models.DateField(verbose_name="Plazo de respuesta")
    is_resolved = models.BooleanField(default=False, verbose_name="Resuelta")

    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True,
        verbose_name="Usuario (opcional)"
    )

    def save(self, *args, **kwargs):
        if self.created_at and not self.deadline:
            from datetime import timedelta
            self.deadline = self.created_at.date() + timedelta(days=7)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Queja de {self.name} ({self.destinatario}) - {self.motivo[:50]}"

    class Meta:
        verbose_name = "Queja"
        verbose_name_plural = "Quejas"
        ordering = ['-created_at']

