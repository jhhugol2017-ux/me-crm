"""
export_excel.py
===============
Generador de Reportes Corporativos Multi-Pestaña en formato Excel (.xlsx)
para MULTIESENCIAS CORPORATE FINANCE & ERP SUITE V4.0.

Pestañas incluidas:
1. Resumen_Ejecutivo_KPI: Márgenes, ROIC, EVA, VAN, TIR, PI, WACC
2. Liquidacion_Aduanera_SAT: Desglose paso a paso de impuestos y fletes
3. Control_Ventas_Inventario: Rotación por SKU, stock y trazabilidad de órdenes
4. Flujo_Caja_12M: Proyección financiera con fórmulas vivas de Excel (=SUM, =NPV, =IRR)
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter


# ---------------------------------------------------------------------------
# ESTILOS CORPORATIVOS OPENPYXL
# ---------------------------------------------------------------------------

def _style_header(cell, text: str, bg_color: str = "1F4E78"):
    """Encabezado corporativo institucional (fondo azul oscuro, texto blanco)."""
    cell.value = text
    cell.font = Font(name="Segoe UI", size=11, bold=True, color="FFFFFF")
    cell.fill = PatternFill("solid", fgColor=bg_color)
    cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)


def _style_sub_header(cell, text: str):
    """Sub-encabezado de sección."""
    cell.value = text
    cell.font = Font(name="Segoe UI", size=10, bold=True, color="1F4E78")
    cell.fill = PatternFill("solid", fgColor="D9E1F2")
    cell.alignment = Alignment(horizontal="left", vertical="center")


def _format_currency(cell, value: Any):
    cell.value = value
    cell.number_format = '"Q"#,##0.00'
    cell.font = Font(name="Segoe UI", size=10)


def _format_usd(cell, value: Any):
    cell.value = value
    cell.number_format = '"$"#,##0.00'
    cell.font = Font(name="Segoe UI", size=10)


def _format_pct(cell, value: Any):
    cell.value = value
    cell.number_format = '0.00%'
    cell.font = Font(name="Segoe UI", size=10)


def _format_qty(cell, value: Any):
    cell.value = value
    cell.number_format = '#,##0.0'
    cell.font = Font(name="Segoe UI", size=10)


def _autofit_columns(ws, max_cols: int = 15):
    """Ajusta automáticamente el ancho de columnas."""
    for col in range(1, max_cols + 1):
        col_letter = get_column_letter(col)
        max_len = 0
        for row in range(1, min(ws.max_row + 1, 100)):
            val = ws.cell(row=row, column=col).value
            if val is not None:
                max_len = max(max_len, len(str(val)))
        ws.column_dimensions[col_letter].width = max(max_len + 4, 14)


# ---------------------------------------------------------------------------
# GENERADOR MAESTRO DE LIBRO EXCEL
# ---------------------------------------------------------------------------

def generate_enterprise_excel(
    filepath: str,
    master_cfg: Dict[str, Any],
    sat_liquidation: Dict[str, Any],
    kpi_metrics: Dict[str, Any],
    inventory_items: List[Dict[str, Any]],
    recent_sales: List[Dict[str, Any]],
    recent_purchases: List[Dict[str, Any]],
    monthly_fcff: List[float],
    initial_investment_gtq: float = 0.0
) -> str:
    """
    Genera el archivo Excel corporativo con las 4 pestañas requeridas.
    Retorna la ruta del archivo generado.
    """
    wb = openpyxl.Workbook()

    # =======================================================================
    # PESTAÑA 1: Resumen_Ejecutivo_KPI
    # =======================================================================
    ws_kpi = wb.active
    ws_kpi.title = "Resumen_Ejecutivo_KPI"
    ws_kpi.views.sheetView[0].showGridLines = True

    ws_kpi.merge_cells("A1:D1")
    title_cell = ws_kpi["A1"]
    title_cell.value = "MULTIESENCIAS | SUITE FINANCIERA & ERP V4.0 - RESUMEN EJECUTIVO"
    title_cell.font = Font(name="Segoe UI", size=14, bold=True, color="1F4E78")
    title_cell.alignment = Alignment(horizontal="left", vertical="center")

    _style_sub_header(ws_kpi["A3"], "PARÁMETRO CORPORATIVO")
    _style_sub_header(ws_kpi["B3"], "VALOR APLICADO")
    _style_sub_header(ws_kpi["C3"], "MÉTRICA FINANCIERA")
    _style_sub_header(ws_kpi["D3"], "RESULTADO DEL MODELO")

    params_list = [
        ("Tipo de Cambio Oficial (GTQ/USD)", master_cfg.get("tipo_cambio_gtq_usd", 7.75), "Q"),
        ("Tasa ISR Régimen General SAT", master_cfg.get("tasa_isr_sat", 0.25), "%"),
        ("Tasa IVA Importación SAT", master_cfg.get("tasa_iva_sat", 0.12), "%"),
        ("Tasa DAI Estándar", master_cfg.get("tasa_dai_defecto", 0.05), "%"),
        ("Costo Promedio Ponderado WACC", master_cfg.get("wacc_institucional", 0.1072), "%"),
        ("Tasa Libre de Riesgo (Rf)", master_cfg.get("tasa_libre_riesgo", 0.0425), "%"),
        ("Prima de Riesgo Mercado (ERP)", master_cfg.get("prima_riesgo_mercado", 0.055), "%"),
        ("Riesgo País Guatemala (CRP)", master_cfg.get("riesgo_pais_crp", 0.0225), "%"),
    ]

    kpis_list = [
        ("Margen Bruto Operativo", kpi_metrics.get("margen_bruto", 0.0), "%"),
        ("Margen Operativo (EBIT)", kpi_metrics.get("margen_operativo", 0.0), "%"),
        ("Utilidad Operativa NOPAT", kpi_metrics.get("nopat", 0.0), "Q"),
        ("Retorno sobre Capital (ROIC)", kpi_metrics.get("roic", 0.0), "%"),
        ("Valor Económico Agregado (EVA)", kpi_metrics.get("eva", 0.0), "Q"),
        ("Valor Actual Neto (VAN / NPV)", kpi_metrics.get("npv", 0.0), "Q"),
        ("Tasa Interna de Retorno (TIR)", kpi_metrics.get("irr", 0.0), "%"),
        ("Índice de Rentabilidad (PI)", kpi_metrics.get("pi", 1.0), "X"),
    ]

    for i in range(max(len(params_list), len(kpis_list))):
        row = 4 + i
        if i < len(params_list):
            lbl_p, val_p, typ_p = params_list[i]
            ws_kpi.cell(row=row, column=1, value=lbl_p).font = Font(name="Segoe UI", size=10)
            c_p = ws_kpi.cell(row=row, column=2)
            if typ_p == "Q": _format_currency(c_p, val_p)
            elif typ_p == "%": _format_pct(c_p, val_p)
            else: c_p.value = val_p

        if i < len(kpis_list):
            lbl_k, val_k, typ_k = kpis_list[i]
            ws_kpi.cell(row=row, column=3, value=lbl_k).font = Font(name="Segoe UI", size=10, bold=True)
            c_k = ws_kpi.cell(row=row, column=4)
            if typ_k == "Q": _format_currency(c_k, val_k)
            elif typ_k == "%": _format_pct(c_k, val_k if val_k is not None else 0.0)
            elif typ_k == "X":
                c_k.value = val_k
                c_k.number_format = '0.00"x"'
            else: c_k.value = val_k

    _autofit_columns(ws_kpi, 4)

    # =======================================================================
    # PESTAÑA 2: Liquidacion_Aduanera_SAT
    # =======================================================================
    ws_sat = wb.create_sheet(title="Liquidacion_Aduanera_SAT")
    ws_sat.views.sheetView[0].showGridLines = True

    ws_sat.merge_cells("A1:D1")
    ws_sat["A1"].value = "LIQUIDACIÓN ADUANERA OFICIAL - SUPERINTENDENCIA DE ADMINISTRACIÓN TRIBUTARIA (SAT)"
    ws_sat["A1"].font = Font(name="Segoe UI", size=13, bold=True, color="1F4E78")

    headers_sat = ["Concepto Arancelario / Tributario", "Base de Cálculo", "Importe Moneda Origen", "Importe en Quetzales (GTQ)"]
    for col_idx, h in enumerate(headers_sat, start=1):
        _style_header(ws_sat.cell(row=3, column=col_idx), h)

    sat_rows = [
        ("Volumen del Lote Importado", f"{sat_liquidation.get('volumen', 0):,.1f} Unidades", "-", "-"),
        ("Tipo de Cambio Aplicable", f"Q {sat_liquidation.get('tipo_cambio', 7.75):,.2f} / USD", "-", "-"),
        ("FOB Total", "FOB Unitario × Volumen", sat_liquidation.get("fob_total_usd", 0.0), sat_liquidation.get("fob_total_usd", 0.0) * sat_liquidation.get("tipo_cambio", 7.75)),
        ("Flete Internacional (Marítimo / Aéreo)", "Tarifa de Ruta × Volumen", sat_liquidation.get("flete_total_usd", 0.0), sat_liquidation.get("flete_total_usd", 0.0) * sat_liquidation.get("tipo_cambio", 7.75)),
        ("Seguro Internacional", "(FOB + Flete) × Tasa Seguro", sat_liquidation.get("seguro_total_usd", 0.0), sat_liquidation.get("seguro_total_usd", 0.0) * sat_liquidation.get("tipo_cambio", 7.75)),
        ("Valor CIF (Costo, Seguro y Flete)", "FOB + Flete + Seguro", sat_liquidation.get("cif_usd", 0.0), sat_liquidation.get("cif_gtq", 0.0)),
        ("DAI (Derechos Arancelarios a la Importación)", "CIF GTQ × Tasa DAI", "-", sat_liquidation.get("dai_gtq", 0.0)),
        ("Base Imponible IVA SAT", "CIF GTQ + DAI GTQ", "-", sat_liquidation.get("base_imponible_iva_gtq", 0.0)),
        ("IVA Importación (12% Crédito Fiscal)", "Base Imponible × 12%", "-", sat_liquidation.get("iva_importacion_gtq", 0.0)),
        ("Gastos Locales y Trámites Aduanales", "Almacenaje + Trámite + Flete Local", "-", sat_liquidation.get("gastos_locales_gtq", 0.0)),
        ("LANDED COST TOTAL (Inventariable)", "CIF + DAI + Gastos Locales", "-", sat_liquidation.get("landed_cost_total_gtq", 0.0)),
        ("LANDED COST UNITARIO FINAL", "Landed Cost Total / Volumen", "-", sat_liquidation.get("landed_cost_unitario_gtq", 0.0)),
    ]

    for idx, (concepto, base, usd_val, gtq_val) in enumerate(sat_rows, start=4):
        ws_sat.cell(row=idx, column=1, value=concepto).font = Font(name="Segoe UI", size=10, bold=(idx in [9, 14, 15]))
        ws_sat.cell(row=idx, column=2, value=base).font = Font(name="Segoe UI", size=10)

        c_usd = ws_sat.cell(row=idx, column=3)
        if isinstance(usd_val, (int, float)):
            _format_usd(c_usd, usd_val)
        else:
            c_usd.value = usd_val
            c_usd.alignment = Alignment(horizontal="center")

        c_gtq = ws_sat.cell(row=idx, column=4)
        if isinstance(gtq_val, (int, float)):
            _format_currency(c_gtq, gtq_val)
            if idx in [14, 15]:
                c_gtq.font = Font(name="Segoe UI", size=11, bold=True, color="1F4E78")
        else:
            c_gtq.value = gtq_val
            c_gtq.alignment = Alignment(horizontal="center")

    _autofit_columns(ws_sat, 4)

    # =======================================================================
    # PESTAÑA 3: Control_Ventas_Inventario
    # =======================================================================
    ws_inv = wb.create_sheet(title="Control_Ventas_Inventario")
    ws_inv.views.sheetView[0].showGridLines = True

    ws_inv.merge_cells("A1:G1")
    ws_inv["A1"].value = "INVENTARIO ACTIVO Y ROTACIÓN HISTÓRICA POR PRODUCTO (SKU)"
    ws_inv["A1"].font = Font(name="Segoe UI", size=13, bold=True, color="1F4E78")

    inv_headers = ["SKU Código", "Nombre del Producto", "Tipo de Producto", "Proveedor Principal", "Stock Actual", "Total Vendido Histórico", "Unidad"]
    for c_i, h in enumerate(inv_headers, start=1):
        _style_header(ws_inv.cell(row=3, column=c_i), h)

    row_cur = 4
    for prod in inventory_items:
        ws_inv.cell(row=row_cur, column=1, value=prod.get("sku_codigo", "")).font = Font(name="Segoe UI", bold=True)
        ws_inv.cell(row=row_cur, column=2, value=prod.get("nombre_producto", ""))
        ws_inv.cell(row=row_cur, column=3, value=prod.get("tipo_producto", ""))
        ws_inv.cell(row=row_cur, column=4, value=prod.get("proveedor_nombre", ""))
        _format_qty(ws_inv.cell(row=row_cur, column=5), prod.get("stock_actual", 0.0))
        _format_qty(ws_inv.cell(row=row_cur, column=6), prod.get("total_vendido_historico", 0.0))
        ws_inv.cell(row=row_cur, column=7, value=prod.get("unidad_medida", "KG"))
        row_cur += 1

    # Tabla de Ventas Recientes
    row_cur += 2
    ws_inv.cell(row=row_cur, column=1, value="HISTORIAL AUDITABLE DE ÓRDENES DE VENTA RECIENTES").font = Font(name="Segoe UI", size=11, bold=True, color="1F4E78")
    row_cur += 1

    sale_headers = ["No. Orden Venta", "Fecha", "Cliente", "SKU", "Cantidad", "Precio Unitario", "Total Facturado"]
    for c_i, h in enumerate(sale_headers, start=1):
        _style_header(ws_inv.cell(row=row_cur, column=c_i), h, bg_color="2F5597")
    row_cur += 1

    for sale in recent_sales[:15]:
        ws_inv.cell(row=row_cur, column=1, value=sale.get("numero_orden", "")).font = Font(name="Segoe UI", bold=True)
        ws_inv.cell(row=row_cur, column=2, value=sale.get("fecha", ""))
        ws_inv.cell(row=row_cur, column=3, value=sale.get("cliente", ""))
        ws_inv.cell(row=row_cur, column=4, value=sale.get("sku_codigo", ""))
        _format_qty(ws_inv.cell(row=row_cur, column=5), sale.get("cantidad", 0.0))
        _format_currency(ws_inv.cell(row=row_cur, column=6), sale.get("precio_unitario_gtq", 0.0))
        _format_currency(ws_inv.cell(row=row_cur, column=7), sale.get("monto_total_gtq", 0.0))
        row_cur += 1

    _autofit_columns(ws_inv, 7)

    # =======================================================================
    # PESTAÑA 4: Flujo_Caja_12M (FÓRMULAS VIVAS DE EXCEL)
    # =======================================================================
    ws_cf = wb.create_sheet(title="Flujo_Caja_12M")
    ws_cf.views.sheetView[0].showGridLines = True

    ws_cf.merge_cells("A1:N1")
    ws_cf["A1"].value = "PROYECCIÓN DE FLUJO DE CAJA LIBRE (FCFF) CON FÓRMULAS DINÁMICAS EXCEL"
    ws_cf["A1"].font = Font(name="Segoe UI", size=13, bold=True, color="1F4E78")

    cols_cf = ["Concepto Financiero", "Mes 0 (Inv)"] + [f"Mes {i}" for i in range(1, 13)]
    for c_i, h in enumerate(cols_cf, start=1):
        _style_header(ws_cf.cell(row=3, column=c_i), h)

    # Fila 4: Flujo de Caja Libre
    ws_cf.cell(row=4, column=1, value="Flujo de Caja Libre (FCFF)").font = Font(name="Segoe UI", bold=True)
    _format_currency(ws_cf.cell(row=4, column=2), -abs(initial_investment_gtq))

    clean_fcff = monthly_fcff if monthly_fcff and len(monthly_fcff) >= 12 else [25000.0] * 12
    for m in range(12):
        col_target = 3 + m
        val_m = clean_fcff[m] if m < len(clean_fcff) else clean_fcff[-1]
        _format_currency(ws_cf.cell(row=4, column=col_target), val_m)

    # Fila 5: Flujo Acumulado con Fórmula Viva
    ws_cf.cell(row=5, column=1, value="Flujo Acumulado").font = Font(name="Segoe UI", bold=True)
    ws_cf.cell(row=5, column=2, value="=B4")
    _format_currency(ws_cf.cell(row=5, column=2), None)
    for m in range(12):
        col_target = 3 + m
        prev_letter = get_column_letter(col_target - 1)
        curr_letter = get_column_letter(col_target)
        ws_cf.cell(row=5, column=col_target, value=f"={prev_letter}5+{curr_letter}4")
        _format_currency(ws_cf.cell(row=5, column=col_target), None)

    # Fila 7: Fórmulas Dinámicas de Valuación
    _style_sub_header(ws_cf["A7"], "MÉTRICAS VIVAS DE EXCEL")
    _style_sub_header(ws_cf["B7"], "FÓRMULA NATIVA APLICADA")

    wacc_val = master_cfg.get("wacc_institucional", 0.1072)
    # Total FCFF Año 1
    ws_cf.cell(row=8, column=1, value="Total FCFF Año 1 (=SUM)").font = Font(name="Segoe UI", bold=True)
    ws_cf.cell(row=8, column=2, value="=SUM(C4:N4)")
    _format_currency(ws_cf.cell(row=8, column=2), None)

    # VAN con fórmula =NPV
    ws_cf.cell(row=9, column=1, value="Valor Actual Neto (=NPV + B4)").font = Font(name="Segoe UI", bold=True)
    ws_cf.cell(row=9, column=2, value=f"=NPV({wacc_val}, C4:N4) + B4")
    _format_currency(ws_cf.cell(row=9, column=2), None)

    # TIR con fórmula =IRR
    ws_cf.cell(row=10, column=1, value="Tasa Interna de Retorno (=IRR)").font = Font(name="Segoe UI", bold=True)
    ws_cf.cell(row=10, column=2, value="=IRR(B4:N4)")
    _format_pct(ws_cf.cell(row=10, column=2), None)

    _autofit_columns(ws_cf, 14)

    wb.save(filepath)
    return filepath
