"""
Módulo de scraping de Facebook Marketplace.
Usa la librería facebook-scraper (no oficial) con fallback a requests+BeautifulSoup.
"""

import os
import logging
import re
from typing import Generator
from filters import extract_year, detect_vehicle_key

logger = logging.getLogger(__name__)

# Términos de búsqueda para cada tipo de vehículo
SEARCH_QUERIES = [
    "spark gt antioquia",
    "spark gt medellin",
    "hyundai i10 antioquia",
    "i10 medellin",
    "carro antioquia 2011",
    "carro medellin barato 2012",
    "vehiculo antioquia",
    "carro area metropolitana",
]

FB_COOKIE = os.environ.get("FB_COOKIE", "")
FB_EMAIL = os.environ.get("FB_EMAIL", "")
FB_PASSWORD = os.environ.get("FB_PASSWORD", "")


def _normalize_ad(raw: dict) -> dict:
    """Normaliza un anuncio crudo al formato estándar interno."""
    title = raw.get("title") or raw.get("name") or ""
    price_raw = str(raw.get("price") or raw.get("price_amount") or "")
    location = (
        raw.get("location")
        or raw.get("seller_location")
        or raw.get("city")
        or ""
    )
    description = raw.get("text") or raw.get("description") or ""
    images = raw.get("images") or []
    listing_url = raw.get("url") or raw.get("listing_url") or ""
    ad_id = str(raw.get("id") or raw.get("listing_id") or listing_url)

    year = raw.get("year")
    if year is None:
        year = extract_year(title + " " + description)

    return {
        "id": ad_id,
        "title": title,
        "price_raw": price_raw,
        "year": year,
        "location": location,
        "description": description,
        "images": images[:3],  # máx 3 fotos
        "url": listing_url,
        "vehicle_key": detect_vehicle_key(title),
    }


def scrape_marketplace(query: str, max_results: int = 20) -> Generator[dict, None, None]:
    """
    Scrape Facebook Marketplace para una query dada.
    Intenta con facebook-scraper; si falla, usa método alternativo.
    """
    try:
        from facebook_scraper import get_posts
        logger.info(f"Scrapeando con facebook-scraper: '{query}'")
        
        options = {
            "marketplace": True,
            "location": "Antioquia, Colombia",
            "radius": 100,
        }
        
        credentials = None
        if FB_EMAIL and FB_PASSWORD:
            credentials = (FB_EMAIL, FB_PASSWORD)
        
        count = 0
        for post in get_posts(
            group="marketplace",
            pages=3,
            options=options,
            credentials=credentials,
            extra_info=True,
        ):
            if count >= max_results:
                break
            # Filtrar por query en título
            title = (post.get("title") or post.get("text") or "").lower()
            if any(word in title for word in query.lower().split()):
                yield _normalize_ad(post)
                count += 1

    except ImportError:
        logger.warning("facebook-scraper no instalado, usando método alternativo")
        yield from _scrape_fallback(query, max_results)
    except Exception as e:
        logger.error(f"Error en scraping principal: {e}")
        yield from _scrape_fallback(query, max_results)


def _scrape_fallback(query: str, max_results: int = 20) -> Generator[dict, None, None]:
    """
    Método alternativo: construye URLs de Marketplace y parsea con requests.
    Nota: requiere cookies de sesión válidas en FB_COOKIE.
    """
    try:
        import requests
        from bs4 import BeautifulSoup

        if not FB_COOKIE:
            logger.error("FB_COOKIE no configurado para el método alternativo")
            return

        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Cookie": FB_COOKIE,
            "Accept-Language": "es-CO,es;q=0.9",
        }

        encoded_query = requests.utils.quote(query)
        url = (
            f"https://www.facebook.com/marketplace/search/"
            f"?query={encoded_query}&exact=false"
        )

        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "html.parser")

        # Extraer datos de los scripts JSON embebidos
        scripts = soup.find_all("script", type="application/json")
        count = 0
        for script in scripts:
            if count >= max_results:
                break
            try:
                import json
                data = json.loads(script.string or "{}")
                listings = _extract_listings_from_json(data)
                for listing in listings:
                    if count >= max_results:
                        break
                    yield _normalize_ad(listing)
                    count += 1
            except Exception:
                continue

    except Exception as e:
        logger.error(f"Error en scraping fallback: {e}")


def _extract_listings_from_json(data: dict | list, depth: int = 0) -> list:
    """Busca recursivamente listings en el JSON de Facebook."""
    results = []
    if depth > 8:
        return results

    if isinstance(data, dict):
        # Heurística: si tiene campos de listing, es un anuncio
        if ("listing_price" in data or "marketplace_listing_title" in data):
            normalized = {
                "id": data.get("id", ""),
                "title": data.get("marketplace_listing_title", ""),
                "price": (
                    data.get("listing_price", {}).get("amount", "")
                    if isinstance(data.get("listing_price"), dict)
                    else data.get("listing_price", "")
                ),
                "location": (
                    data.get("location", {}).get("reverse_geocode", {}).get("city", "")
                    if isinstance(data.get("location"), dict)
                    else data.get("location", "")
                ),
                "description": data.get("description", {}).get("text", "")
                if isinstance(data.get("description"), dict)
                else data.get("description", ""),
                "images": [
                    img.get("uri", "") for img in data.get("listing_photos", [])
                    if isinstance(img, dict)
                ],
                "url": f"https://www.facebook.com/marketplace/item/{data.get('id', '')}",
            }
            results.append(normalized)

        for value in data.values():
            results.extend(_extract_listings_from_json(value, depth + 1))

    elif isinstance(data, list):
        for item in data:
            results.extend(_extract_listings_from_json(item, depth + 1))

    return results


def run_all_searches(max_per_query: int = 15) -> list[dict]:
    """Ejecuta todas las búsquedas y retorna lista deduplicada de anuncios."""
    all_ads = {}
    for query in SEARCH_QUERIES:
        try:
            for ad in scrape_marketplace(query, max_results=max_per_query):
                if ad["id"] and ad["id"] not in all_ads:
                    all_ads[ad["id"]] = ad
        except Exception as e:
            logger.error(f"Error en query '{query}': {e}")

    return list(all_ads.values())
