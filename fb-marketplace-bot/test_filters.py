"""
Tests para validar los filtros, especialmente el parseo de precios.
Corre con: python test_filters.py
"""

from filters import parse_price, apply_filters, detect_vehicle_key, is_in_antioquia

# ---------------------------------------------------------------------------
# Tests de parseo de precio
# ---------------------------------------------------------------------------

def test_parse_price():
    casos = [
        # (input, expected)
        ("20", 20_000_000),
        ("20,5", 20_500_000),
        ("20.5", 20_500_000),
        ("20,000", 20_000_000),
        ("20.000", 20_000_000),
        ("20,000,000", 20_000_000),
        ("20.000.000", 20_000_000),
        ("$20.000.000", 20_000_000),
        ("20 millones", 20_000_000),
        ("20M", 20_000_000),
        ("15", 15_000_000),
        ("25,000,000", 25_000_000),
        ("8500000", 8_500_000),
        ("8.500.000", 8_500_000),
        ("18,500,000", 18_500_000),
        ("25 millones cop", 25_000_000),
        ("12.5 millones", 12_500_000),
    ]
    
    passed = 0
    failed = 0
    for raw, expected in casos:
        result = parse_price(raw)
        ok = result == expected
        status = "✅" if ok else "❌"
        print(f"  {status} parse_price('{raw}') = {result:,} (esperado: {expected:,})")
        if ok:
            passed += 1
        else:
            failed += 1
    
    print(f"\n  Resultado: {passed}/{len(casos)} pasaron\n")
    return failed == 0


# ---------------------------------------------------------------------------
# Tests de detección de vehículo
# ---------------------------------------------------------------------------

def test_detect_vehicle():
    casos = [
        ("Spark GT 2015 excelente estado", "spark_gt"),
        ("Vendo chevrolet spark 2012", "spark_gt"),
        ("Hyundai i10 2019 único dueño", "hyundai_i10"),
        ("i10 grand 2020 full equipo", "hyundai_i10"),
        ("Toyota Corolla 2015", "other"),
        ("Renault Logan 2013 barato", "other"),
        ("SPARK GT MODELO 2017", "spark_gt"),
        ("Hyundai I10 2014 Negociable", "hyundai_i10"),
    ]
    
    passed = 0
    for title, expected in casos:
        result = detect_vehicle_key(title)
        ok = result == expected
        status = "✅" if ok else "❌"
        print(f"  {status} '{title}' → {result} (esperado: {expected})")
        if ok:
            passed += 1
    
    print(f"\n  Resultado: {passed}/{len(casos)} pasaron\n")
    return passed == len(casos)


# ---------------------------------------------------------------------------
# Tests de ubicación
# ---------------------------------------------------------------------------

def test_location():
    casos = [
        ("Medellín, Antioquia", True),
        ("Bello Antioquia", True),
        ("Rionegro", True),
        ("Bogotá", False),
        ("Cali, Valle del Cauca", False),
        ("Envigado", True),
        ("Sabaneta", True),
        ("Santa Marta", False),
        ("Itagüi Antioquia", True),
    ]
    
    passed = 0
    for loc, expected in casos:
        result = is_in_antioquia(loc)
        ok = result == expected
        status = "✅" if ok else "❌"
        print(f"  {status} '{loc}' → {result} (esperado: {expected})")
        if ok:
            passed += 1
    
    print(f"\n  Resultado: {passed}/{len(casos)} pasaron\n")
    return passed == len(casos)


# ---------------------------------------------------------------------------
# Tests de filtro completo
# ---------------------------------------------------------------------------

def test_apply_filters():
    casos = [
        # (ad_dict, should_pass, description)
        (
            {"title": "Spark GT 2015", "price_raw": "22.000.000", "year": 2015, "location": "Medellín"},
            True, "Spark GT 2015 a 22M en Medellín → DEBE PASAR"
        ),
        (
            {"title": "Spark GT 2015", "price_raw": "26.000.000", "year": 2015, "location": "Medellín"},
            False, "Spark GT a 26M → supera límite de 25M"
        ),
        (
            {"title": "Hyundai i10 2018", "price_raw": "24,500,000", "year": 2018, "location": "Bello Antioquia"},
            True, "i10 2018 a 24.5M en Bello → DEBE PASAR"
        ),
        (
            {"title": "Toyota Corolla 2019", "price_raw": "21.000.000", "year": 2019, "location": "Envigado"},
            False, "Corolla a 21M → supera 20M para 'other'"
        ),
        (
            {"title": "Renault Logan 2013", "price_raw": "18.000.000", "year": 2013, "location": "Rionegro"},
            True, "Logan 2013 a 18M en Rionegro → DEBE PASAR"
        ),
        (
            {"title": "Spark GT 2009", "price_raw": "10.000.000", "year": 2009, "location": "Medellín"},
            False, "Spark GT 2009 → año menor a 2011"
        ),
        (
            {"title": "Spark GT 2015", "price_raw": "22.000.000", "year": 2015, "location": "Bogotá"},
            False, "Spark GT en Bogotá → fuera de Antioquia"
        ),
        (
            {"title": "Hyundai i10 2020", "price_raw": "25", "year": 2020, "location": "Itagüi"},
            True, "i10 con precio '25' (se interpreta 25M) → DEBE PASAR"
        ),
    ]
    
    passed = 0
    for ad, should_pass, desc in casos:
        result, reason = apply_filters(ad)
        ok = result == should_pass
        status = "✅" if ok else "❌"
        print(f"  {status} {desc}")
        if not ok:
            print(f"       → Obtuvo: {result} ({reason})")
        if ok:
            passed += 1
    
    print(f"\n  Resultado: {passed}/{len(casos)} pasaron\n")
    return passed == len(casos)


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("=" * 60)
    print("  TESTS - FB Marketplace Bot Filtros")
    print("=" * 60)
    
    results = []
    
    print("\n📦 Test 1: Parseo de precios")
    results.append(test_parse_price())
    
    print("🚗 Test 2: Detección de vehículo")
    results.append(test_detect_vehicle())
    
    print("📍 Test 3: Ubicación Antioquia")
    results.append(test_location())
    
    print("🔍 Test 4: Filtro completo")
    results.append(test_apply_filters())
    
    total = len(results)
    passed = sum(results)
    print("=" * 60)
    print(f"  TOTAL: {passed}/{total} grupos de tests pasaron")
    print("=" * 60)
