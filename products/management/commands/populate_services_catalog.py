from django.core.management.base import BaseCommand
from products.models import Service
from django.contrib.auth import get_user_model


CATALOG_SERVICES = [
    {
        "name": "Celular",
        "description": "Limpieza interna, revisión general, optimización básica y chequeo de funcionamiento.",
        "price": 55000,
        "service_key_candidates": ["celular", "telefono", "tel", "cel"],
    },
    {
        "name": "Laptop",
        "description": "Mantenimiento preventivo con limpieza, revisión térmica y optimización del sistema.",
        "price": 95000,
        "service_key_candidates": ["laptop", "notebook", "portatil"],
    },
    {
        "name": "Tablet",
        "description": "Revisión general, limpieza de polvo y optimización para mejor rendimiento.",
        "price": 70000,
        "service_key_candidates": ["tablet", "tab"],
    },
    {
        "name": "Audífonos",
        "description": "Limpieza, revisión de puertos y pruebas de audio para mejorar calidad.",
        "price": 30000,
        "service_key_candidates": ["audifonos", "audif", "audífonos", "headphone", "earphone"],
    },
    {
        "name": "Revisión Técnica General",
        "description": "Diagnóstico rápido para detectar fallas y recomendar el siguiente paso.",
        "price": 25000,
        "service_key_candidates": ["revision_tecnica", "revision", "revisi", "tecnica", "técnica"],
    },
    {
        "name": "Limpieza Profunda",
        "description": "Limpieza interna completa (polvo/acumulación) y mantenimiento preventivo extendido.",
        "price": 45000,
        "service_key_candidates": ["limpieza_profunda", "limpieza", "profunda", "deep"],
    },
]


class Command(BaseCommand):
    help = "Populate Service table with the default catalog services (if empty)."

    def handle(self, *args, **options):
        if Service.objects.exists():
            self.stdout.write(self.style.WARNING("Service table already has data. Nothing to do."))
            return

        User = get_user_model()
        # We need a seller UserProfile for Service.seller.
        # Try to use a known seller; otherwise fall back to any user that has a profile.
        seller_profile = None
        for username in ["elian", "jhontru", "jhontrujillo"]:
            u = User.objects.filter(username=username).first()
            if u and hasattr(u, "profile") and u.profile:
                seller_profile = u.profile
                break

        if seller_profile is None:
            # If still not found, pick the first user with profile
            any_user = User.objects.all().first()
            if any_user and hasattr(any_user, "profile"):
                seller_profile = any_user.profile

        if seller_profile is None:
            raise RuntimeError("Could not resolve a seller profile to create Service entries.")

        created = 0
        for s in CATALOG_SERVICES:
            Service.objects.create(
                name=s["name"],
                description=s["description"],
                price=s["price"],
                seller=seller_profile,
            )
            created += 1

        self.stdout.write(self.style.SUCCESS(f"Created {created} services in catalog."))

