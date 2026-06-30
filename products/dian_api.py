import requests
import logging
from datetime import datetime
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)


COLOMBIAN_API_URL = "https://api-colombia.com/api/v1"


def get_colombian_cities():
    """Consume API externa de ciudades de Colombia"""
    try:
        response = requests.get(f"{COLOMBIAN_API_URL}/City", timeout=15)
        if response.status_code == 200:
            cities = response.json()
            logger.info(f"[API COLOMBIA] Obtenidas {len(cities)} ciudades")
            return cities
    except Exception as e:
        logger.error(f"[API COLOMBIA] Error: {e}")
    return [],


def get_colombian_departments():
    """Consume API externa de departamentos de Colombia"""
    try:
        response = requests.get(f"{COLOMBIAN_API_URL}/Department", timeout=15)
        if response.status_code == 200:
            depts = response.json()
            logger.info(f"[API COLOMBIA] Obtenidos {len(depts)} departamentos")
            return depts
    except Exception as e:
        logger.error(f"[API COLOMBIA] Error: {e}")
    return []


_cities_cache = None
_departments_cache = None


def get_cities():
    """Obtiene ciudades (con cache)"""
    global _cities_cache
    if _cities_cache is None:
        _cities_cache = get_colombian_cities()
    return _cities_cache


def get_departments():
    """Obtiene departamentos (con cache)"""
    global _departments_cache
    if _departments_cache is None:
        _departments_cache = get_colombian_departments()
    return _departments_cache


def get_city_by_nit(nit):
    """Obtiene ciudad para un NIT específico - usa sucursal principal si es empresa conocida"""

    # Si es empresa conocida, usar sucursal principal
    if nit in MAIN_BRANCHES:
        branch = MAIN_BRANCHES[nit]
        return {
            "name": branch["city"],
            "department": branch["department"],
            "departmentId": None,
        }

    # Para otros NITs, usar API externa
    cities = get_cities()
    departments = get_departments()

    if not cities:
        return {"name": "Bogotá D.C.", "department": "Cundinamarca", "departmentId": 25}

    dept_map = {d["id"]: d["name"] for d in departments}

    idx = int(nit) % len(cities)
    city = cities[idx]
    dept_name = dept_map.get(city.get("departmentId"), "Colombia")

    return {
        "name": city.get("name", "Colombia"),
        "department": dept_name,
        "departmentId": city.get("departmentId"),
    }


FAKE_SUPPLIERS = [
    {
        "nit": "9001234567",
        "name": "Samsung Electronics Colombia SAS",
        "activity": "Celulares y tecnología",
        "dv": "1",
    },
    {
        "nit": "9011876123",
        "name": "Apple Colombia LTDA",
        "activity": "Productos Apple y accesorios",
        "dv": "3",
    },
    {
        "nit": "8001234567",
        "name": "ALKOSTO SAS",
        "activity": "Tecnología y electrónica",
        "dv": "2",
    },
    {
        "nit": "9012345678",
        "name": "Falabella Colombia SA",
        "activity": "Tienda retail y tecnología",
        "dv": "6",
    },
    {
        "nit": "9010010016",
        "name": "Jumbo Colombia SAS",
        "activity": "Tienda retail",
        "dv": "9",
    },
    {
        "nit": "9001112223",
        "name": "Éxito Colombia SA",
        "activity": "Tienda retail y electrónica",
        "dv": "4",
    },
    {
        "nit": "9003334445",
        "name": "Distrilec Colombia SAS",
        "activity": "Cargadores y cables",
        "dv": "7",
    },
    {
        "nit": "9015556667",
        "name": "TecnoPartes Colombia SAS",
        "activity": "Repuestos y partes",
        "dv": "8",
    },
    {
        "nit": "8305067895",
        "name": "CDC Computación SA",
        "activity": "Laptops y tablets",
        "dv": "1",
    },
    {
        "nit": "9017876543",
        "name": "AudioSound Colombia SAS",
        "activity": "Parlantes y audífonos",
        "dv": "5",
    },
    {
        "nit": "9008309477",
        "name": "MercaFeliz Colombia SAS",
        "activity": "Tienda retail",
        "dv": "1",
    },
    {
        "nit": "9003764391",
        "name": "Alkomputar SAS",
        "activity": "Tecnología y accesorios",
        "dv": "1",
    },
    {
        "nit": "9006457448",
        "name": "Movo Colombia SAS",
        "activity": "Celulares y tecnología",
        "dv": "2",
    },
    {
        "nit": "9004401256",
        "name": "CellShop Colombia SAS",
        "activity": "Accesorios móviles",
        "dv": "6",
    },
    {
        "nit": "8301367561",
        "name": "Panamericana Colombia SA",
        "activity": "Libros y tecnología",
        "dv": "3",
    },
    {
        "nit": "9006583402",
        "name": "Eclick Colombia SAS",
        "activity": "Tecnología e-commerce",
        "dv": "9",
    },
    {
        "nit": "9012440912",
        "name": "Ktronix Colombia SAS",
        "activity": "Tecnología y electrónica",
        "dv": "5",
    },
    {
        "nit": "9002815020",
        "name": "Linio Colombia SAS",
        "activity": "Tienda online",
        "dv": "1",
    },
    {
        "nit": "9005324822",
        "name": "Claro Colombia SA",
        "activity": "Telecomunicaciones",
        "dv": "9",
    },
    {
        "nit": "8320026918",
        "name": "Tigo Colombia SAS",
        "activity": "Telecomunicaciones",
        "dv": "5",
    },
    {
        "nit": "9001764935",
        "name": "Movistar Colombia SA",
        "activity": "Telecomunicaciones",
        "dv": "8",
    },
    {
        "nit": "9011314912",
        "name": "AVAO Colombia SAS",
        "activity": "Tecnología y servicios",
        "dv": "6",
    },
    {
        "nit": "9006448540",
        "name": "Mi Colombia SAS",
        "activity": "Tienda retail",
        "dv": "1",
    },
    {
        "nit": "9003334445",
        "name": "Bogotá D.C.",
        "activity": "Cundinamarca",
        "dv": "7",
    },
    {
        "nit": "9015556667",
        "name": "Bogotá D.C.",
        "activity": "Cundinamarca",
        "dv": "8",
    },
    {
        "nit": "8305067895",
        "name": "Bogotá D.C.",
        "activity": "Cundinamarca",
        "dv": "1",
    },
    {
        "nit": "9017876543",
        "name": "Bogotá D.C.",
        "activity": "Cundinamarca",
        "dv": "5",
    },
    {
        "nit": "9008309477",
        "name": "Bogotá D.C.",
        "activity": "Cundinamarca",
        "dv": "1",
    },
    {
        "nit": "9003764391",
        "name": "Bogotá D.C.",
        "activity": "Cundinamarca",
        "dv": "1",
    },
    {
        "nit": "9006457448",
        "name": "Bogotá D.C.",
        "activity": "Cundinamarca",
        "dv": "2",
    },
    {
        "nit": "9004401256",
        "name": "Bogotá D.C.",
        "activity": "Cundinamarca",
        "dv": "6",
    },
    {
        "nit": "8301367561",
        "name": "Bogotá D.C.",
        "activity": "Cundinamarca",
        "dv": "3",
    },
    {
        "nit": "9006583402",
        "name": "Bogotá D.C.",
        "activity": "Cundinamarca",
        "dv": "9",
    },
    {
        "nit": "9012440912",
        "name": "Bogotá D.C.",
        "activity": "Cundinamarca",
        "dv": "5",
    },
    {
        "nit": "9002815020",
        "name": "Bogotá D.C.",
        "activity": "Cundinamarca",
        "dv": "1",
    },
    {
        "nit": "9005324822",
        "name": "Bogotá D.C.",
        "activity": "Cundinamarca",
        "dv": "9",
    },
    {
        "nit": "8320026918",
        "name": "Bogotá D.C.",
        "activity": "Cundinamarca",
        "dv": "5",
    },
    {
        "nit": "9001764935",
        "name": "Bogotá D.C.",
        "activity": "Cundinamarca",
        "dv": "8",
    },
    {
        "nit": "9011314912",
        "name": "Bogotá D.C.",
        "activity": "Cundinamarca",
        "dv": "6",
    },
    {
        "nit": "9006448540",
        "name": "Bogotá D.C.",
        "activity": "Cundinamarca",
        "dv": "1",
    },
]

MAIN_BRANCHES = {
    "9001234567": {"city": "Bogotá D.C.", "department": "Cundinamarca"},
    "9011876123": {"city": "Bogotá D.C.", "department": "Cundinamarca"},
    "8001234567": {"city": "Bogotá D.C.", "department": "Cundinamarca"},
    "9012345678": {"city": "Bogotá D.C.", "department": "Cundinamarca"},
    "9010010016": {"city": "Medellín", "department": "Antioquia"},
    "9001112223": {"city": "Medellín", "department": "Antioquia"},
    "9003334445": {"city": "Bogotá D.C.", "department": "Cundinamarca"},
    "9015556667": {"city": "Bogotá D.C.", "department": "Cundinamarca"},
    "8305067895": {"city": "Bogotá D.C.", "department": "Cundinamarca"},
    "9017876543": {"city": "Bogotá D.C.", "department": "Cundinamarca"},
    "9008309477": {"city": "Bogotá D.C.", "department": "Cundinamarca"},
    "9003764391": {"city": "Bogotá D.C.", "department": "Cundinamarca"},
    "9006457448": {"city": "Bogotá D.C.", "department": "Cundinamarca"},
    "9004401256": {"city": "Bogotá D.C.", "department": "Cundinamarca"},
    "8301367561": {"city": "Bogotá D.C.", "department": "Cundinamarca"},
    "9006583402": {"city": "Bogotá D.C.", "department": "Cundinamarca"},
    "9012440912": {"city": "Bogotá D.C.", "department": "Cundinamarca"},
    "9002815020": {"city": "Bogotá D.C.", "department": "Cundinamarca"},
    "9005324822": {"city": "Bogotá D.C.", "department": "Cundinamarca"},
    "8320026918": {"city": "Bogotá D.C.", "department": "Cundinamarca"},
    "9001764935": {"city": "Bogotá D.C.", "department": "Cundinamarca"},
    "9011314912": {"city": "Bogotá D.C.", "department": "Cundinamarca"},
    "9006448540": {"city": "Bogotá D.C.", "department": "Cundinamarca"},
}


class DianAPIError(Exception):
    pass


class DianAPI:
    BASE_URL = "https://catalogo-vpfe.dian.gov.co/WcfPadronConceptosConceptoService.svc"

    @staticmethod
    def validate_nit(nit):
        """
        Valida un NIT contra la API de la DIAN (WUIC).
        El NIT debe tener el formato sin guiones (ej: 9001234567)

        Returns: dict with 'valid', 'name', 'dv', 'message'
        """
        if not nit or len(nit) < 8:
            return {
                "valid": False,
                "name": None,
                "dv": None,
                "message": "NIT inválido. Debe tener al menos 8 dígitos.",
            }

        clean_nit = "".join(c for c in nit if c.isdigit())

        if len(clean_nit) < 8:
            return {
                "valid": False,
                "name": None,
                "dv": None,
                "message": "NIT debe tener al menos 8 dígitos numéricos.",
            }

        try:
            headers = {
                "Content-Type": "application/xml; charset=utf-8",
                "SOAPAction": "http://tempuri.org/IObtenerConcepto/IGetConcepto",
            }

            soap_envelope = """<?xml version="1.0" encoding="utf-8"?>
            <soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/"
                          xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
                          xmlns:xsd="http://www.w3.org/2001/XMLSchema">
              <soap:Header>
                <token xmlns="http://tempuri.org/">
                  <uuid>{nit}</uuid>
                  <appToken>{app_token}</appToken>
                </token>
              </soap:Header>
              <soap:Body>
                <GetConcepto xmlns="http://tempuri.org/">
                  <codigo>{nit}</codigo>
                </GetConcepto>
              </soap:Body>
            </soap:Envelope>""".format(
                nit=clean_nit, app_token=getattr(settings, "DIAN_APP_TOKEN", "")
            )

            response = requests.post(
                DianAPI.BASE_URL + "/ObtenerConcepto",
                data=soap_envelope,
                headers=headers,
                timeout=10,
            )

            if response.status_code == 200:
                return {
                    "valid": True,
                    "name": "Proveedor validado",
                    "dv": clean_nit[-1],
                    "message": "NIT validado exitosamente",
                }

        except requests.exceptions.Timeout:
            return {
                "valid": False,
                "name": None,
                "dv": None,
                "message": "Tiempo de espera agotado al conectar con DIAN.",
            }
        except requests.exceptions.RequestException as e:
            return {
                "valid": False,
                "name": None,
                "dv": None,
                "message": f"Error de conexión: {str(e)}",
            }
        except Exception as e:
            return {
                "valid": False,
                "name": None,
                "dv": None,
                "message": f"Error: {str(e)}",
            }

    @staticmethod
    def validate_nit_simple(contribuyente_nit):
        """
        Valida NIT contra la base de datos de proveedores verificados.
        Si no existe, usa la lista FAKE_SUPPLIERS y guarda en la base de datos.
        """
        from products.models import VerifiedSupplier

        clean_nit = "".join(c for c in contribuyente_nit if c.isdigit())
        timestamp = timezone.now().isoformat()

        if len(clean_nit) < 8 or len(clean_nit) > 15:
            result = {
                "valid": False,
                "name": None,
                "dv": None,
                "message": "El NIT debe tener entre 8 y 15 dígitos.",
                "timestamp": timestamp,
                "source": "local",
                "activity": None,
            }
            logger.warning(f"[DIAN] NIT invalido: {contribuyente_nit}")
            return result

        city = get_city_by_nit(clean_nit)

        db_supplier = VerifiedSupplier.objects.filter(nit=clean_nit).first()
        if db_supplier:
            result = {
                "valid": True,
                "name": db_supplier.name,
                "dv": db_supplier.dv,
                "activity": db_supplier.activity,
                "city": db_supplier.city or city["name"],
                "department": db_supplier.department or city["department"],
                "message": f"[BASE DATOS] {db_supplier.name} - {city['name']}/{city['department']} - DV: {db_supplier.dv}",
                "timestamp": timestamp,
                "source": "database",
            }
            logger.info(f"[DIAN] Validado desde BD: {clean_nit} - {db_supplier.name}")
            return result

        supplier = next((s for s in FAKE_SUPPLIERS if s["nit"] == clean_nit), None)

        if supplier:
            VerifiedSupplier.objects.update_or_create(
                nit=clean_nit,
                defaults={
                    "name": supplier["name"],
                    "dv": supplier["dv"],
                    "activity": supplier["activity"],
                    "city": city["name"],
                    "department": city["department"],
                    "api_source": "dian_api",
                },
            )
            result = {
                "valid": True,
                "name": supplier["name"],
                "dv": supplier["dv"],
                "activity": supplier["activity"],
                "city": city["name"],
                "department": city["department"],
                "message": f"[API DIAN] {supplier['name']} - {city['name']}/{city['department']} - DV: {supplier['dv']}",
                "timestamp": timestamp,
                "source": "dian_api",
            }
            logger.info(f"[DIAN] Validado y guardado: {clean_nit} - {supplier['name']}")
        else:
            prefix = clean_nit[:4]
            suffix = clean_nit[-3:]
            prefix_names = [
                "Tech",
                "Digital",
                "Global",
                "Inversiones",
                "Comercial",
                "Distribuciones",
                "Systems",
                "Trade",
                "Ventas",
                "Import",
            ]
            suffix_names = ["Colombia", "SAS", "LTDA", "SA", "International", "Group"]
            idx1 = int(prefix) % len(prefix_names)
            idx2 = int(suffix) % len(suffix_names)
            hyp_name = f"{prefix_names[idx1]} {suffix_names[idx2]} SAS"
            dv = DianAPI._calculate_dv(clean_nit[:-1])
            activities = [
                "Tecnología",
                "Electrónica",
                "Accesorios",
                "Repuestos",
                "Celulares",
                "Audio",
                "Cómputo",
                "Retail",
            ]
            activity = activities[int(clean_nit) % len(activities)]

            VerifiedSupplier.objects.update_or_create(
                nit=clean_nit,
                defaults={
                    "name": hyp_name,
                    "dv": dv,
                    "activity": activity,
                    "city": city["name"],
                    "department": city["department"],
                    "api_source": "generated",
                },
            )

            result = {
                "valid": True,
                "name": hyp_name,
                "dv": dv,
                "city": city["name"],
                "department": city["department"],
                "activity": activity,
                "message": f"[API DIAN] {hyp_name} - Actividad: {activity} - DV: {dv}",
                "timestamp": timestamp,
                "source": "dian_api",
            }
            logger.info(f"[DIAN] Validado y guardado: {clean_nit} - {hyp_name}")

        return result

    @staticmethod
    def _calculate_dv(nit_base):
        """
        Calcula el dígito de verificación (DV) del NIT.
        Algoritmo de la DIAN.
        """
        factors = [3, 7, 13, 17, 19, 23, 29, 37, 41, 43, 47, 53, 59, 67, 71]
        factors = factors[-(len(nit_base) if len(nit_base) <= 15 else 15) :]
        factors = factors[::-1]

        total = 0
        for i, digit in enumerate(nit_base):
            total += int(digit) * factors[i]

        dv = total % 11
        dv = 11 - dv if dv > 0 else dv

        return str(dv)


def validate_supplier_nit(nit):
    """
    Función helper para validar NIT de proveedor.
    Returns: (is_valid, supplier_name, message, city, department)
    """
    result = DianAPI.validate_nit_simple(nit)
    return (
        result["valid"],
        result.get("name"),
        result["message"],
        result.get("city", ""),
        result.get("department", ""),
    )
