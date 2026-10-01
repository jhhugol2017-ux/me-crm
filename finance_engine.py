"""
finance_engine.py
=================
Motores Matemáticos Cuantitativos y Financieros para
MULTIESENCIAS CORPORATE FINANCE & ERP SUITE V4.0.

Implementa:
1. Liquidación Aduanera Guatemalteca (SAT) paso a paso
2. Costeo de Formulación Interna con Merma Química y BOM
3. Capital de Trabajo y Ciclo de Conversión de Efectivo (CCC / NWC)
4. Lote Económico de Compra (EOQ) y Costo de Capital WACC
5. Rentabilidad Corporativa, ROIC y EVA
6. Flujo de Caja Libre Descontado (DCF), VAN, TIR y Payback
7. Simulación Estocástica de Monte Carlo (@RISK Logístico - 10,000 iteraciones)
"""

from __future__ import annotations
import math
from typing import Any, Dict, List, Optional
import numpy as np
import pandas as pd
from scipy.optimize import brentq


# ---------------------------------------------------------------------------
# HELPERS DEFENSIVOS UNIVERSALES (PREVENCIÓN DE TYPEERROR Y DIVISIÓN POR CERO)
# ---------------------------------------------------------------------------

def safe_num(val: Any, default: float = 0.0) -> float:
    """Convierte de forma segura cualquier valor a float, controlando None, NaN e Inf."""
    if val is None:
        return default
    try:
        f = float(val)
        return default if (math.isnan(f) or math.isinf(f)) else f
    except (ValueError, TypeError):
        return default


def safe_fmt(val: Any, fmt: str = "{:,.2f}", prefix: str = "", suffix: str = "") -> str:
    """Formatea valores numéricos con respaldo automático si es None o inválido."""
    v = safe_num(val, None)
    if v is None:
        return "N/A"
    return f"{prefix}{fmt.format(v)}{suffix}"


# ---------------------------------------------------------------------------
# 1. MOTOR DE LIQUIDACIÓN ADUANERA GUATEMALA (SAT)
# ---------------------------------------------------------------------------

def compute_landed_cost_sat(
    fob_unitario_usd: float,
    volumen: float,
    tarifa_flete_unitario_usd: float,
    tipo_cambio: float = 7.75,
    tasa_seguro_pct: float = 0.01,
    tasa_dai_pct: float = 0.05,
    gastos_aduanales_locales_usd: float = 0.0,
    flete_local_gtq: float = 0.0,
    costo_flete_fijo_usd: float = 0.0,
) -> Dict[str, float]:
    """
    Liquidación Aduanera Oficial SAT Guatemala:
    - FOB Total = FOB Unitario × Volumen
    - Flete Total = (Tarifa Unit × Volumen) + Flete Fijo
    - Seguro Total = (FOB + Flete) × Tasa Seguro %
    - CIF USD = FOB + Flete + Seguro
    - CIF GTQ = CIF USD × Tipo de Cambio
    - DAI GTQ = CIF GTQ × Tasa DAI %
    - Base Imponible IVA = CIF GTQ + DAI GTQ
    - IVA Importación (12% Crédito Fiscal) = Base Imponible × 0.12
    - Gastos Locales GTQ = (Gastos Aduanales USD × Tipo Cambio) + Flete Local GTQ
    - Landed Cost Total GTQ = CIF GTQ + DAI GTQ + Gastos Locales GTQ
    - Landed Cost Unitario = Landed Cost Total / Volumen
    """
    vol = max(safe_num(volumen), 1.0)
    tc = max(safe_num(tipo_cambio), 1.0)
    fob_u = safe_num(fob_unitario_usd)

    fob_total_usd = fob_u * vol
    flete_total_usd = (safe_num(tarifa_flete_unitario_usd) * vol) + safe_num(costo_flete_fijo_usd)
    seguro_total_usd = (fob_total_usd + flete_total_usd) * safe_num(tasa_seguro_pct)

    cif_usd = fob_total_usd + flete_total_usd + seguro_total_usd
    cif_gtq = cif_usd * tc
    dai_gtq = cif_gtq * safe_num(tasa_dai_pct)

    base_imponible_iva_gtq = cif_gtq + dai_gtq
    iva_importacion_gtq = base_imponible_iva_gtq * 0.12  # Crédito Fiscal compensable

    gastos_locales_gtq = (safe_num(gastos_aduanales_locales_usd) * tc) + safe_num(flete_local_gtq)
    landed_cost_total_gtq = cif_gtq + dai_gtq + gastos_locales_gtq
    landed_cost_unitario_gtq = landed_cost_total_gtq / vol

    return {
        "volumen": vol,
        "tipo_cambio": tc,
        "fob_unitario_usd": fob_u,
        "fob_total_usd": fob_total_usd,
        "flete_total_usd": flete_total_usd,
        "seguro_total_usd": seguro_total_usd,
        "cif_usd": cif_usd,
        "cif_gtq": cif_gtq,
        "dai_gtq": dai_gtq,
        "base_imponible_iva_gtq": base_imponible_iva_gtq,
        "iva_importacion_gtq": iva_importacion_gtq,
        "gastos_locales_gtq": gastos_locales_gtq,
        "landed_cost_total_gtq": landed_cost_total_gtq,
        "landed_cost_unitario_gtq": landed_cost_unitario_gtq,
    }


# ---------------------------------------------------------------------------
# 2. MOTOR DE FORMULACIÓN INTERNA (BOM & MERMA TÉCNICA)
# ---------------------------------------------------------------------------

def compute_formulation_cost(
    costo_mp_base_gtq: float,
    proporcion_peso: float = 1.0,
    merma_tecnica_pct: float = 0.03,
    aditivos_empaque_gtq: float = 0.0
) -> Dict[str, float]:
    """
    Calcula el costo real unitario de un producto formulado:
    Costo MP Real = (Costo MP Teórico × Proporción) / (1 - Merma %) + Aditivos y Empaque
    """
    prop = min(max(safe_num(proporcion_peso), 0.01), 1.0)
    merma = min(max(safe_num(merma_tecnica_pct), 0.0), 0.50)
    base = safe_num(costo_mp_base_gtq)
    adit = safe_num(aditivos_empaque_gtq)

    denominador = max(1.0 - merma, 0.01)
    costo_mp_neto = (base * prop) / denominador
    costo_unitario_final = costo_mp_neto + adit

    return {
        "costo_mp_base_gtq": base,
        "proporcion_peso": prop,
        "merma_tecnica_pct": merma,
        "aditivos_empaque_gtq": adit,
        "costo_mp_con_merma_gtq": costo_mp_neto,
        "costo_unitario_final_gtq": costo_unitario_final
    }


# ---------------------------------------------------------------------------
# 3. MOTOR DE CAPITAL DE TRABAJO Y CCC (BERK & DEMARZO)
# ---------------------------------------------------------------------------

def compute_ccc_and_nwc(
    inventario_promedio_gtq: float,
    cdbv_anual_gtq: float,
    cxc_promedio_gtq: float,
    ventas_anuales_gtq: float,
    cxp_promedio_gtq: float,
    efectivo_minimo_gtq: float = 0.0,
    dso_pactado_cliente: Optional[float] = None,
    dpo_pactado_proveedor: Optional[float] = None
) -> Dict[str, Any]:
    """
    Calcula DIO, DSO, DPO, Ciclo de Conversión de Efectivo (CCC) y Capital Neto de Trabajo (NWC).
    """
    cdbv = max(safe_num(cdbv_anual_gtq), 1e-6)
    ventas = max(safe_num(ventas_anuales_gtq), 1e-6)
    inv = safe_num(inventario_promedio_gtq)
    cxc = safe_num(cxc_promedio_gtq)
    cxp = safe_num(cxp_promedio_gtq)
    cash = safe_num(efectivo_minimo_gtq)

    cdbv_diario = cdbv / 365.0
    ventas_diarias = ventas / 365.0

    dio = inv / cdbv_diario
    dso = safe_num(dso_pactado_cliente) if dso_pactado_cliente is not None else (cxc / ventas_diarias)
    dpo = safe_num(dpo_pactado_proveedor) if dpo_pactado_proveedor is not None else (cxp / cdbv_diario)

    ccc = dio + dso - dpo
    financiamiento_req_gtq = ventas_diarias * max(ccc, 0.0)

    activo_circulante = cash + inv + cxc
    pasivo_circulante = cxp
    nwc = activo_circulante - pasivo_circulante

    if ccc <= 30:
        evaluacion = "Óptimo (Alta liquidez operativa)"
        color = "positive"
    elif ccc <= 60:
        evaluacion = "Aceptable para industria B2B"
        color = "positive"
    elif ccc <= 90:
        evaluacion = "Elevado (Riesgo moderado de caja)"
        color = "warning"
    else:
        evaluacion = "Crítico (Requiere financiamiento bancario)"
        color = "negative"

    return {
        "dio": round(dio, 1),
        "dso": round(dso, 1),
        "dpo": round(dpo, 1),
        "ccc": round(ccc, 1),
        "financiamiento_req_gtq": round(financiamiento_req_gtq, 2),
        "activo_circulante": round(activo_circulante, 2),
        "pasivo_circulante": round(pasivo_circulante, 2),
        "nwc": round(nwc, 2),
        "evaluacion": evaluacion,
        "color": color
    }


# ---------------------------------------------------------------------------
# 4. GESTIÓN DE INVENTARIO Y LOTE ECONÓMICO (EOQ)
# ---------------------------------------------------------------------------

def compute_eoq(
    demanda_anual_unidades: float,
    costo_ordenar_s_gtq: float,
    costo_unitario_c_gtq: float,
    tasa_costos_fisicos_pct: float = 0.08,
    wacc: float = 0.1072
) -> Dict[str, Any]:
    """
    EOQ = √[ (2 × D × S) / H ]
    donde H = C × (costos_físicos + WACC)
    """
    d = max(safe_num(demanda_anual_unidades), 1.0)
    s = max(safe_num(costo_ordenar_s_gtq), 1.0)
    c = max(safe_num(costo_unitario_c_gtq), 0.01)
    cf = max(safe_num(tasa_costos_fisicos_pct), 0.0)
    w = max(safe_num(wacc), 0.01)

    tasa_holding = cf + w
    h = c * tasa_holding

    eoq = math.sqrt((2.0 * d * s) / max(h, 1e-6))
    pedidos_por_ano = d / eoq
    dias_entre_pedidos = 365.0 / pedidos_por_ano if pedidos_por_ano > 0 else 0

    costo_ordenar_anual = pedidos_por_ano * s
    costo_mantener_anual = (eoq / 2.0) * h
    costo_total_inventario = costo_ordenar_anual + costo_mantener_anual

    return {
        "eoq": round(eoq, 1),
        "costo_mantener_h_gtq": round(h, 4),
        "tasa_holding_total": tasa_holding,
        "pedidos_por_ano": round(pedidos_por_ano, 1),
        "dias_entre_pedidos": round(dias_entre_pedidos, 1),
        "costo_ordenar_anual": round(costo_ordenar_anual, 2),
        "costo_mantener_anual": round(costo_mantener_anual, 2),
        "costo_total_inventario": round(costo_total_inventario, 2)
    }


# ---------------------------------------------------------------------------
# 5. RENTABILIDAD CORPORATIVA, ROIC Y EVA
# ---------------------------------------------------------------------------

def compute_profitability_and_eva(
    ventas_anuales_gtq: float,
    cdbv_anual_gtq: float,
    gastos_operativos_gtq: float,
    depreciacion_anual_gtq: float,
    nwc_gtq: float,
    activos_fijos_netos_gtq: float,
    tasa_isr: float = 0.25,
    wacc: float = 0.1072
) -> Dict[str, Any]:
    """
    Estado de Resultados Analítico:
    Utilidad Bruta, EBIT, ISR, NOPAT, ROIC y EVA.
    """
    v = safe_num(ventas_anuales_gtq)
    c = safe_num(cdbv_anual_gtq)
    opex = safe_num(gastos_operativos_gtq)
    depr = safe_num(depreciacion_anual_gtq)
    t_isr = safe_num(tasa_isr, 0.25)
    w = safe_num(wacc, 0.1072)

    utilidad_bruta = v - c
    margen_bruto = utilidad_bruta / v if v > 0 else 0.0

    ebit = utilidad_bruta - opex - depr
    margen_operativo = ebit / v if v > 0 else 0.0

    isr_gtq = max(ebit * t_isr, 0.0) if ebit > 0 else 0.0
    nopat = ebit - isr_gtq

    capital_empleado = max(safe_num(nwc_gtq) + safe_num(activos_fijos_netos_gtq), 1.0)
    roic = nopat / capital_empleado
    costo_capital = capital_empleado * w
    eva = nopat - costo_capital

    crea_valor = eva > 0

    return {
        "ventas_anuales": v,
        "cdbv_anual": c,
        "utilidad_bruta": utilidad_bruta,
        "margen_bruto": margen_bruto,
        "gastos_operativos": opex,
        "depreciacion_anual": depr,
        "ebit": ebit,
        "margen_operativo": margen_operativo,
        "isr_gtq": isr_gtq,
        "nopat": nopat,
        "capital_empleado": capital_empleado,
        "roic": roic,
        "costo_capital": costo_capital,
        "eva": eva,
        "spread_roic_wacc": roic - w,
        "crea_valor": crea_valor
    }


# ---------------------------------------------------------------------------
# 6. VALUACIÓN DCF, TESORERÍA 24M Y MATRIZ DE SENSIBILIDAD
# ---------------------------------------------------------------------------

def compute_valuation_dcf(
    inversion_inicial_gtq: float,
    fcff_12_meses: List[float],
    wacc: float = 0.1072,
    crecimiento_terminal: float = 0.02,
    kd_after_tax: float = 0.06375
) -> Dict[str, Any]:
    """
    Valuación por Flujo de Caja Descontado a 5 años + Valor Terminal.
    Protección defensiva total: si inversión inicial <= 0, PI reporta 1.00x sin división entre cero.
    """
    inv = safe_num(inversion_inicial_gtq)
    w = max(safe_num(wacc), 0.01)
    g = min(safe_num(crecimiento_terminal), w - 0.005)

    y1_fcff = sum(safe_num(x) for x in fcff_12_meses)
    annual_fcff = [y1_fcff * ((1.0 + g) ** k) for k in range(5)]

    # Valor Terminal Gordon-Shapiro
    terminal_value = annual_fcff[-1] * (1.0 + g) / (w - g)

    # Valor Presente
    pv_flows = sum(cf / ((1.0 + w) ** (i + 1)) for i, cf in enumerate(annual_fcff))
    pv_tv = terminal_value / ((1.0 + w) ** 5)
    npv = pv_flows + pv_tv - inv

    # TIR
    cf_series = [-inv] + annual_fcff + [terminal_value]
    irr = None
    try:
        sign_changes = sum(1 for i in range(len(cf_series) - 1) if cf_series[i] * cf_series[i + 1] < 0)
        if sign_changes >= 1:
            irr = brentq(
                lambda r: sum(c / ((1.0 + r) ** t) for t, c in enumerate(cf_series)),
                -0.95, 5.0, maxiter=500
            )
    except Exception:
        irr = None

    # Índice de Rentabilidad (PI) - Totalmente defensivo
    if inv > 1.0:
        pi = (npv + inv) / inv
    else:
        pi = 1.00

    # Payback descontado
    payback_meses = None
    cum_cash = -inv
    for month_idx, m_cf in enumerate(fcff_12_meses):
        prev = cum_cash
        cum_cash += m_cf
        if prev < 0 and cum_cash >= 0:
            payback_meses = (month_idx + 1)
            break

    return {
        "npv": npv,
        "irr": irr,
        "pi": pi,
        "payback_meses": payback_meses,
        "terminal_value": terminal_value,
        "annual_fcff": annual_fcff,
        "y1_fcff": y1_fcff
    }


def compute_treasury_24m(
    inversion_inicial_gtq: float,
    fcff_12_meses: List[float],
    ccc_dias: float = 45.0
) -> Dict[str, Any]:
    """
    Proyecta la trayectoria de caja a 24 meses integrando el desfase operativo del CCC.
    """
    inv = safe_num(inversion_inicial_gtq)
    clean_cfs = [safe_num(x) for x in fcff_12_meses]
    if not clean_cfs or all(x == 0 for x in clean_cfs):
        clean_cfs = [15000.0] * 12

    # Proyección M13 a M24 con ligero crecimiento
    m12 = clean_cfs[-1]
    ext_cfs = [m12 * (1.015 ** i) for i in range(1, 13)]
    cfs_24 = clean_cfs + ext_cfs

    # Aplicación del lag por CCC (desfase de capital)
    lag_months = int(round(safe_num(ccc_dias) / 30.0))
    lag_months = max(min(lag_months, 3), 0)

    # Flujo acumulado
    cum_cash = [-inv]
    saldo = -inv
    for idx, cf in enumerate(cfs_24):
        # Durante los meses de lag hay mayor presión sobre el efectivo
        ajuste = 0.85 if idx < lag_months else 1.0
        saldo += (cf * ajuste)
        cum_cash.append(saldo)

    min_cash = min(cum_cash)
    peak_deficit_gtq = abs(min_cash) if min_cash < 0 else 0.0

    mes_recuperacion = None
    for m_i, s_val in enumerate(cum_cash):
        if m_i > 0 and s_val >= 0:
            mes_recuperacion = m_i
            break

    return {
        "cum_cash_series": cum_cash[1:],  # 24 meses
        "peak_deficit_gtq": peak_deficit_gtq,
        "mes_recuperacion": mes_recuperacion,
        "saldo_final_24m": cum_cash[-1]
    }


# ---------------------------------------------------------------------------
# 7. SIMULACIÓN ESTOCÁSTICA DE MONTE CARLO (@RISK LOGÍSTICO - 10,000 ITERS)
# ---------------------------------------------------------------------------

def run_monte_carlo_logistics(
    fob_unitario_usd: float,
    volumen_mensual: float,
    precio_venta_gtq: float,
    tarifa_flete_unitario_usd: float,
    tipo_cambio_base: float = 7.75,
    wacc: float = 0.1072,
    vol_flete_maritimo_pct: float = 0.15,
    vol_flete_aereo_pct: float = 0.20,
    vol_tipo_cambio_pct: float = 0.05,
    vol_demanda_pct: float = 0.10,
    modalidad: str = "MARÍTIMO",
    n_iterations: int = 10000,
    seed: int = 42
) -> Dict[str, Any]:
    """
    Ejecuta 10,000 iteraciones vectorizadas con NumPy evaluando:
    - Volatilidad de Flete Internacional
    - Volatilidad del Tipo de Cambio USD/GTQ
    - Volatilidad de la Demanda Mensual
    Genera distribución de Landed Cost, distribución de VAN y calcula VaR al 5%.
    """
    rng = np.random.default_rng(seed)

    vol = max(safe_num(volumen_mensual), 1.0)
    p_gtq = max(safe_num(precio_venta_gtq), 1.0)
    fob = max(safe_num(fob_unitario_usd), 0.1)
    flete_base = max(safe_num(tarifa_flete_unitario_usd), 0.01)
    tc = max(safe_num(tipo_cambio_base), 1.0)
    w = max(safe_num(wacc), 0.01)

    # 1. Variables estocásticas vectorizadas
    vol_flete = vol_flete_aereo_pct if modalidad.upper() == "AÉREO" else vol_flete_maritimo_pct
    flete_sim = rng.lognormal(mean=np.log(flete_base), sigma=safe_num(vol_flete), size=n_iterations)
    tc_sim = rng.normal(loc=tc, scale=tc * safe_num(vol_tipo_cambio_pct), size=n_iterations)
    tc_sim = np.clip(tc_sim, tc * 0.8, tc * 1.3)

    demanda_mult = rng.normal(loc=1.0, scale=safe_num(vol_demanda_pct), size=n_iterations)
    demanda_mult = np.clip(demanda_mult, 0.4, 2.0)
    vol_sim = vol * demanda_mult

    # 2. Vectorización de Landed Cost
    seguro_sim = (fob + flete_sim) * 0.01
    cif_usd_sim = fob + flete_sim + seguro_sim
    cif_gtq_sim = cif_usd_sim * tc_sim
    dai_gtq_sim = cif_gtq_sim * 0.05
    landed_unitario_sim = cif_gtq_sim + dai_gtq_sim

    # 3. Flujos anualizados y VAN estocástico
    ventas_anuales_sim = vol_sim * 12.0 * p_gtq
    costos_anuales_sim = vol_sim * 12.0 * landed_unitario_sim
    ebit_sim = (ventas_anuales_sim - costos_anuales_sim) * 0.85  # Menos gastos operativos
    nopat_sim = np.where(ebit_sim > 0, ebit_sim * 0.75, ebit_sim)

    # VAN a 5 años simplificado
    inv_inicial = vol * landed_unitario_sim.mean() * 1.5
    annuity_factor = (1.0 - (1.0 + w) ** -5) / w
    npv_sim = (nopat_sim * annuity_factor) - inv_inicial

    # 4. Métricas de Riesgo
    var_5pct = float(np.percentile(npv_sim, 5))
    p10_npv = float(np.percentile(npv_sim, 10))
    p50_npv = float(np.percentile(npv_sim, 50))
    p90_npv = float(np.percentile(npv_sim, 90))
    mean_npv = float(np.mean(npv_sim))

    prob_npv_negativo = float(np.mean(npv_sim < 0))
    prob_margen_negativo = float(np.mean((p_gtq - landed_unitario_sim) < 0))
    std_return = float(np.std(npv_sim) / max(abs(mean_npv), 1.0))

    return {
        "landed_cost_dist": landed_unitario_sim.tolist()[:1000],  # Muestra para gráficos
        "npv_dist": npv_sim.tolist()[:1000],
        "landed_cost_mean": float(np.mean(landed_unitario_sim)),
        "landed_cost_p95": float(np.percentile(landed_unitario_sim, 95)),
        "mean_npv": mean_npv,
        "p10_npv": p10_npv,
        "p50_npv": p50_npv,
        "p90_npv": p90_npv,
        "var_5pct": var_5pct,
        "prob_npv_negativo": prob_npv_negativo,
        "prob_margen_negativo": prob_margen_negativo,
        "std_return": std_return,
    }
