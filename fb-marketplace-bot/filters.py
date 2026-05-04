"""
Lógica de filtros: precio, año, ubicación y vehículos de interés.
"""

import re

# ---------------------------------------------------------------------------
# Vehículos de interés y sus alias
# ---------------------------------------------------------------------------
VEHICLES_OF_INTEREST = {
    "spark_gt": {
        "aliases": [
            "spark gt", "sparkgt", "spark", "chevrolet spark", "chevy spark",
            "spark 2", "spark2", "chevrolet spark gt",
        ],
        "max_price_cop": 25_000_000,
    },
    "hyundai_i10": {
        "aliases": [
            "i10", "hyundai i10", "i 10", "hyundai i 10", "grand i10",
            "grand i 10", "i10 grand", "atos", "hyundai atos",
        ],
        "max_price_cop": 25_000_000,
    },
    "other": {
        "aliases": [],          # cualquier otro vehículo
        "max_price_cop": 20_000_000,
    },
}

MIN_YEAR = 2011

# ---------------------------------------------------------------------------
# Municipios de Antioquia (muestra amplia; puedes ampliar)
# ---------------------------------------------------------------------------
ANTIOQUIA_LOCATIONS = [
    "antioquia", "medellín", "medellin", "bello", "itagüi", "itagui",
    "envigado", "sabaneta", "la estrella", "caldas", "copacabana",
    "girardota", "barbosa", "rionegro", "guarne", "marinilla", "el retiro",
    "la ceja", "la unión", "sonsón", "sonson", "abejorral", "fredonia",
    "jericó", "jerico", "andes", "ciudad bolívar", "ciudad bolivar",
    "urrao", "dabeiba", "apartadó", "apartado", "turbo", "carepa",
    "chigorodó", "chigorodo", "necoclí", "necocli", "caucasia",
    "tarazá", "taraza", "yarumal", "santa rosa de osos", "don matías",
    "don matias", "san pedro de los milagros", "entrerríos", "entrerios",
    "amalfi", "yolombó", "yolombo", "cisneros", "puerto berrío",
    "puerto berrio", "maceo", "el bagre", "zaragoza", "segovia",
    "remedios", "vegachí", "vegachi", "yalí", "yali", "anorí", "anori",
    "angostura", "campamento", "valdivia", "briceño", "briceno",
    "liborina", "olaya", "sabanalarga", "sopetrán", "sopetran",
    "san jerónimo", "san jeronimo", "santa fe de antioquia",
    "buriticá", "buritica", "peque", "giraldo", "cañasgordas",
    "cajasgordas", "uramita", "mutatá", "mutata", "vigía del fuerte",
    "vigía", "murindó", "murindo", "armenia", "concordia",
    "betulia", "titiribí", "titiribi", "venecia", "hispania",
    "jardín", "jardin", "támesis", "tamesis", "valparaíso", "valparaiso",
    "pueblo rico", "betania", "montebello", "nariño", "narino",
    "cocorná", "cocorna", "san luis", "san francisco", "san carlos",
    "granada", "el santuario", "el peñol", "el penol", "guatapé", "guatape",
    "alejandría", "alejandria", "concepción", "concepcion", "san rafael",
    "san roque", "santo domingo", "carolina del príncipe", "gómez plata",
    "gomez plata", "guadalupe", "pueblorrico", "el jardín",
    "abriaquí", "abriaqui", "san josé de la montaña", "toledo",
    "ituango", "pedregal", "belmira", "san pedro",
    "la pintada", "venecia", "bolívar", "bolivar", "pueblorrico",
    "el Carmen de viboral", "el carmen", "carmen de viboral",
    "san vicente", "el carmen de atrato",
    "área metropolitana", "area metropolitana", "valle de aburra",
    "valle de aburrá", "aburra", "aburrá",
]


# ---------------------------------------------------------------------------
# Normalización de precio
# ---------------------------------------------------------------------------

def parse_price(raw: str) -> int | None:
    """
    Intenta convertir un string de precio a entero en pesos colombianos.

    Ejemplos que maneja:
      "20"            → 20_000_000   (si < 1000, asume millones)
      "20,5"          → 20_500_000
      "20.5"          → 20_500_000
      "20,000"        → 20_000_000   (miles con coma)
      "20.000"        → 20_000_000   (miles con punto europeo)
      "20,000,000"    → 20_000_000
      "20.000.000"    → 20_000_000
      "$20.000.000"   → 20_000_000
      "20 millones"   → 20_000_000
      "20M"           → 20_000_000
      "20k"           → 20_000       (raramente usado pero por si acaso)
    """
    if not raw:
        return None

    s = raw.lower().strip()

    # Quitar símbolo de moneda y espacios
    s = re.sub(r"[\$\s]", "", s)

    # "millones" o "M"
    million_match = re.search(r"([\d]+(?:[.,]\d+)?)\s*(?:millones?|millon|m\b)", s)
    if million_match:
        num = million_match.group(1).replace(",", ".")
        try:
            return int(float(num) * 1_000_000)
        except ValueError:
            pass

    # "k" (miles)
    k_match = re.search(r"([\d]+(?:[.,]\d+)?)\s*k", s)
    if k_match:
        num = k_match.group(1).replace(",", ".")
        try:
            return int(float(num) * 1_000)
        except ValueError:
            pass

    # Extraer solo dígitos, comas y puntos
    s = re.sub(r"[^\d.,]", "", s)
    if not s:
        return None

    # Detectar separador decimal vs. miles
    # Caso: "20,500,000" o "20.500.000" → separadores de miles
    # Caso: "20,5" o "20.5" → decimal
    # Caso: "20,000" o "20.000" → miles (terminan en exactamente 3 dígitos después del sep)
    dot_count = s.count(".")
    comma_count = s.count(",")

    if dot_count > 1:
        # e.g. "20.000.000" → quitar puntos
        s = s.replace(".", "")
    elif comma_count > 1:
        # e.g. "20,000,000" → quitar comas
        s = s.replace(",", "")
    elif comma_count == 1 and dot_count == 1:
        # e.g. "20,000.00" o "20.000,00"
        # El último separador es el decimal
        last_comma = s.rfind(",")
        last_dot = s.rfind(".")
        if last_dot > last_comma:
            s = s.replace(",", "")         # punto decimal
        else:
            s = s.replace(".", "").replace(",", ".")  # coma decimal
    elif comma_count == 1:
        # e.g. "20,5" (decimal) o "20,000" (miles → pero en COP contexto vehículos = millones)
        after_comma = s.split(",")[1]
        if len(after_comma) == 3 and after_comma.isdigit():
            # "20,000" → eliminar coma → 20000 → luego heurística lo sube a 20M
            s = s.replace(",", "")
        else:
            s = s.replace(",", ".")        # decimal
    elif dot_count == 1:
        after_dot = s.split(".")[1]
        if len(after_dot) == 3 and after_dot.isdigit():
            # "20.000" → eliminar punto → 20000 → luego heurística lo sube a 20M
            s = s.replace(".", "")
        # else: ya es decimal, dejar como está

    try:
        value = float(s)
    except ValueError:
        return None

    # Heurística contexto vehículos colombianos:
    # < 1000        → millones (ej: "20" → 20M)
    # 1000-999999   → miles que representan millones (ej: "20000" → 20M)
    if value < 1_000:
        value *= 1_000_000
    elif value < 1_000_000:
        value *= 1_000

    return int(value)


# ---------------------------------------------------------------------------
# Detección de vehículo de interés
# ---------------------------------------------------------------------------

def detect_vehicle_key(title: str) -> str:
    """
    Retorna la clave del vehículo detectado en el título del anuncio.
    Retorna "other" si no coincide con ninguno específico.
    """
    title_lower = title.lower()
    for key, info in VEHICLES_OF_INTEREST.items():
        if key == "other":
            continue
        for alias in info["aliases"]:
            if alias in title_lower:
                return key
    return "other"


def get_max_price_for_vehicle(vehicle_key: str) -> int:
    return VEHICLES_OF_INTEREST[vehicle_key]["max_price_cop"]


# ---------------------------------------------------------------------------
# Extracción de año
# ---------------------------------------------------------------------------

def extract_year(text: str) -> int | None:
    """Extrae el primer año de 4 dígitos entre 1980 y 2030 encontrado en el texto."""
    matches = re.findall(r"\b((?:19|20)\d{2})\b", text)
    for m in matches:
        year = int(m)
        if 1980 <= year <= 2030:
            return year
    return None


# ---------------------------------------------------------------------------
# Detección de ubicación en Antioquia
# ---------------------------------------------------------------------------

def is_in_antioquia(location_text: str) -> bool:
    """Verifica si la ubicación está en Antioquia o sus municipios."""
    if not location_text:
        return False
    loc = location_text.lower()
    return any(place in loc for place in ANTIOQUIA_LOCATIONS)


# ---------------------------------------------------------------------------
# Filtro principal
# ---------------------------------------------------------------------------

def apply_filters(ad: dict) -> tuple[bool, str]:
    """
    Aplica todos los filtros al anuncio.
    Retorna (pasa_filtro: bool, motivo_rechazo: str)
    
    `ad` debe tener keys: title, price_raw, year (int|None), location
    """
    title = ad.get("title", "")
    price_raw = ad.get("price_raw", "")
    year = ad.get("year")
    location = ad.get("location", "")

    # 1. Ubicación
    if not is_in_antioquia(location):
        return False, f"Ubicación fuera de Antioquia: '{location}'"

    # 2. Año
    if year is None:
        year = extract_year(title + " " + ad.get("description", ""))
    if year is not None and year < MIN_YEAR:
        return False, f"Modelo {year} es anterior a {MIN_YEAR}"

    # 3. Precio
    price = parse_price(price_raw)
    if price is None:
        return False, f"No se pudo interpretar el precio: '{price_raw}'"

    vehicle_key = detect_vehicle_key(title)
    max_price = get_max_price_for_vehicle(vehicle_key)

    if price > max_price:
        return False, (
            f"Precio ${price:,.0f} supera el máximo "
            f"${max_price:,.0f} para '{vehicle_key}'"
        )

    return True, "OK"
