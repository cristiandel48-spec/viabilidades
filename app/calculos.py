"""
Lógica de cálculo de viabilidad financiera M&D.
Exactamente los mismos cálculos del Excel original.
"""

IVA = 0.19

CANALES = [
    {"nombre": "Aliados",          "descuento": 0.29},
    {"nombre": "Int + Vinculados", "descuento": 0.20},
    {"nombre": "Tiendas",          "descuento": 0.02},
    {"nombre": "E-Commerce",       "descuento": 0.01},
]

# Participación por canal (mix de distribución)
DIST_CANALES = [0.40, 0.25, 0.25, 0.10]


def precio_sin_iva(precio_con_iva: float) -> float:
    """Precio neto antes de IVA."""
    return precio_con_iva / (1 + IVA)


def precio_neto_canal(precio_con_iva: float, descuento: float) -> float:
    """Precio neto para un canal específico."""
    return precio_sin_iva(precio_con_iva) * (1 - descuento)


def precio_promedio_neto(precio_con_iva: float) -> float:
    """Precio promedio ponderado neto considerando todos los canales."""
    return sum(
        precio_neto_canal(precio_con_iva, c["descuento"]) * DIST_CANALES[i]
        for i, c in enumerate(CANALES)
    )


def margen_bruto(precio_neto: float, costo: float) -> float:
    """Margen bruto = (precio neto - costo) / precio neto."""
    if not precio_neto or precio_neto == 0:
        return 0.0
    return (precio_neto - costo) / precio_neto


def utilidad_bruta(precio_neto: float, costo: float) -> float:
    return precio_neto - costo


def variacion_costo(costo_real: float, costo_estimado: float) -> float:
    """Variación porcentual entre costo real y estimado."""
    if not costo_estimado or costo_estimado == 0:
        return 0.0
    return (costo_real - costo_estimado) / costo_estimado


def calcular_metricas(precio_cop_iva: float, costo: float, margen_objetivo: float = 40.0) -> dict:
    """
    Devuelve todas las métricas para mostrar en la UI.
    """
    sin_iva  = precio_sin_iva(precio_cop_iva)
    neto     = precio_promedio_neto(precio_cop_iva)
    mb       = margen_bruto(neto, costo)
    ub       = utilidad_bruta(neto, costo)
    viable   = mb >= (margen_objetivo / 100)

    canales_detalle = []
    for i, canal in enumerate(CANALES):
        pn = precio_neto_canal(precio_cop_iva, canal["descuento"])
        mb_canal = margen_bruto(pn, costo)
        canales_detalle.append({
            "nombre":        canal["nombre"],
            "descuento_pct": canal["descuento"] * 100,
            "precio_neto":   round(pn, 2),
            "margen_pct":    round(mb_canal * 100, 2),
            "participacion": DIST_CANALES[i] * 100,
        })

    return {
        "precio_sin_iva":     round(sin_iva, 2),
        "precio_prom_neto":   round(neto, 2),
        "margen_bruto_pct":   round(mb * 100, 2),
        "utilidad_bruta":     round(ub, 2),
        "viable":             viable,
        "canales":            canales_detalle,
    }


def fmt_cop(valor: float) -> str:
    """Formato moneda colombiana: $1.234.567"""
    if valor is None:
        return "—"
    return f"${round(valor):,}".replace(",", ".")
