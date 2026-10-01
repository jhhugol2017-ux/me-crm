"""
app.py
======
MULTIESENCIAS CORPORATE FINANCE & ERP SUITE V4.0
Plataforma Empresarial Cloud, Multi-Usuario, Control de Órdenes y Suite Financiera.
"""

from __future__ import annotations
import os
import datetime
import tempfile
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from database import (
    authenticate_user, create_user, get_all_users, toggle_user_active,
    get_all_proveedores, create_proveedor,
    get_all_rutas, create_ruta,
    get_all_productos, get_producto_by_sku, create_producto,
    get_all_clientes, create_cliente,
    get_recetas_by_producto, create_receta,
    create_orden_compra, recibir_orden_compra, get_all_ordenes_compra,
    create_orden_venta, get_all_ordenes_venta,
    get_master_config, update_master_config, reset_database
)

from finance_engine import (
    safe_num, safe_fmt,
    compute_landed_cost_sat,
    compute_formulation_cost,
    compute_ccc_and_nwc,
    compute_eoq,
    compute_profitability_and_eva,
    compute_valuation_dcf,
    compute_treasury_24m,
    run_monte_carlo_logistics
)

from export_excel import generate_enterprise_excel

# ---------------------------------------------------------------------------
# CONFIGURACIÓN DE PÁGINA STREAMLIT
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="MULTIESENCIAS | Corporate Finance & ERP Suite V4.0",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="expanded"
)


# ---------------------------------------------------------------------------
# INYECCIÓN DE ESTILOS CSS DEFENSIVOS (DARK FINTECH THEME)
# ---------------------------------------------------------------------------
def inject_custom_styles():
    css = """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500;700&display=swap');
    
    html, body, [data-testid="stAppViewContainer"] {
        font-family: 'Inter', system-ui, sans-serif;
        background-color: #0B0F17 !important;
        color: #E2E8F0 !important;
    }
    
    [data-testid="stHeader"] {
        background-color: #0B0F17 !important;
    }
    
    [data-testid="stSidebar"] {
        background-color: #111722 !important;
        border-right: 1px solid #1E2A3D !important;
    }
    
    .block-container {
        padding-top: 1.5rem !important;
        padding-bottom: 2.5rem !important;
        max-width: 96% !important;
    }
    
    /* Botones primarios y secundarios */
    div[data-testid="stButton"] > button[kind="primary"] {
        background: linear-gradient(135deg, #3B82F6 0%, #1D4ED8 100%) !important;
        color: #FFFFFF !important;
        border: 1px solid #3B82F6 !important;
        border-radius: 6px !important;
        font-weight: 600 !important;
        box-shadow: 0 2px 8px rgba(59, 130, 246, 0.35) !important;
    }
    
    div[data-testid="stButton"] > button[kind="secondary"] {
        background-color: #1A2332 !important;
        color: #E2E8F0 !important;
        border: 1px solid #2D3E57 !important;
        border-radius: 6px !important;
    }
    
    /* Inputs */
    [data-testid="stNumberInput"] input, [data-testid="stTextInput"] input, [data-testid="stSelectbox"] > div {
        background-color: #151D2A !important;
        color: #E2E8F0 !important;
        border: 1px solid #2D3E57 !important;
        border-radius: 6px !important;
    }
    
    /* Dataframes */
    [data-testid="stDataFrame"] {
        border: 1px solid #2D3E57 !important;
        border-radius: 8px !important;
    }
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)

inject_custom_styles()


# ---------------------------------------------------------------------------
# COMPONENTES VISUALES INSTITUCIONALES (HTML ROBUSTO)
# ---------------------------------------------------------------------------

def hero_banner(title: str, badge: str, subtitle: str, formula: str = "") -> str:
    f_html = f'<div style="font-family:monospace; font-size:0.8rem; color:#60A5FA; background:rgba(59,130,246,0.12); padding:4px 10px; border-radius:4px; margin-top:8px; display:inline-block; border:1px solid rgba(59,130,246,0.3);">📐 {formula}</div>' if formula else ""
    return f"""<div style="background:#151D2A; border:1px solid #2D3E57; border-left:4px solid #3B82F6; border-radius:8px; padding:16px 20px; margin-bottom:18px;">
<div style="display:flex; align-items:center; gap:10px;">
<span style="font-size:1.15rem; font-weight:700; color:#E2E8F0;">{title}</span>
<span style="font-size:0.7rem; font-weight:700; text-transform:uppercase; letter-spacing:0.08em; background:rgba(59,130,246,0.2); color:#60A5FA; padding:3px 8px; border-radius:999px; border:1px solid rgba(59,130,246,0.4);">{badge}</span>
</div>
<div style="font-size:0.85rem; color:#94A3B8; margin-top:4px;">{subtitle}</div>
{f_html}
</div>"""


def kpi_card(label: str, value: str, badge_text: str = "", badge_type: str = "neutral", subtext: str = "") -> str:
    color_map = {
        "positive": ("rgba(16,185,129,0.15)", "#10B981", "#10B981"),
        "negative": ("rgba(239,68,68,0.15)", "#EF4444", "#EF4444"),
        "warning":  ("rgba(245,158,11,0.15)", "#F59E0B", "#F59E0B"),
        "accent":   ("rgba(59,130,246,0.15)", "#3B82F6", "#3B82F6"),
        "neutral":  ("rgba(148,163,184,0.15)", "#94A3B8", "#2D3E57"),
    }
    bg, fg, bdr = color_map.get(badge_type, color_map["neutral"])
    badge_html = f'<span style="font-size:0.65rem; font-weight:700; padding:2px 7px; border-radius:999px; background:{bg}; color:{fg}; border:1px solid {bdr}; display:inline-block;">{badge_text}</span>' if badge_text else ""
    sub_html = f'<div style="font-size:0.72rem; color:#94A3B8; margin-top:4px; font-family:monospace;">{subtext}</div>' if subtext else ""

    return f"""<div style="background:#151D2A; border:1px solid {bdr}; border-radius:8px; padding:14px 16px; min-width:200px; flex:1; box-shadow:0 2px 6px rgba(0,0,0,0.35);">
<div style="font-size:0.7rem; font-weight:600; text-transform:uppercase; letter-spacing:0.08em; color:#94A3B8; margin-bottom:4px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">{label}</div>
<div style="font-size:1.35rem; font-weight:700; color:#E2E8F0; font-family:monospace; margin-bottom:4px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">{value}</div>
{badge_html}
{sub_html}
</div>"""


def kpi_row(*cards: str) -> str:
    inner = "".join(c.strip() for c in cards if c)
    return f'<div style="display:flex; gap:12px; margin-bottom:18px; flex-wrap:wrap;">{inner}</div>'


def section_header(title: str, subtitle: str = "", icon: str = "") -> str:
    icon_h = f'<span style="font-size:1.15rem; margin-right:8px;">{icon}</span>' if icon else ""
    sub_h = f'<span style="font-size:0.75rem; color:#94A3B8; margin-left:8px;">{subtitle}</span>' if subtitle else ""
    return f'<div style="font-size:0.95rem; font-weight:700; color:#E2E8F0; padding-bottom:8px; margin:16px 0 12px 0; border-bottom:1px solid #2D3E57; display:flex; align-items:center;">{icon_h}{title}{sub_h}</div>'


# ---------------------------------------------------------------------------
# GESTIÓN DE SESIÓN Y AUTENTICACIÓN
# ---------------------------------------------------------------------------

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "user_data" not in st.session_state:
    st.session_state.user_data = None


def render_login():
    """Pantalla institucional de inicio de sesión."""
    st.markdown("<br><br>", unsafe_allow_html=True)
    c_left, c_mid, c_right = st.columns([1, 1.8, 1])
    with c_mid:
        st.markdown("""
        <div style="background:#151D2A; border:1px solid #2D3E57; border-radius:12px; padding:28px 32px; box-shadow:0 8px 24px rgba(0,0,0,0.5);">
            <div style="font-size:1.6rem; font-weight:800; color:#3B82F6; letter-spacing:-0.03em;">MULTIESENCIAS</div>
            <div style="font-size:0.8rem; font-weight:600; color:#94A3B8; text-transform:uppercase; letter-spacing:0.1em; margin-bottom:20px;">Corporate Finance & ERP Suite V4.0</div>
            <p style="font-size:0.85rem; color:#64748B;">Ingrese sus credenciales corporativas para acceder al sistema:</p>
        </div>
        """, unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)

        with st.form("login_form"):
            usr = st.text_input("Usuario", placeholder="ej. admin o ventas")
            pwd = st.text_input("Contraseña", type="password")
            submit = st.form_submit_button("Iniciar Sesión", type="primary", use_container_width=True)

            if submit:
                user = authenticate_user(usr.strip(), pwd.strip())
                if user:
                    st.session_state.authenticated = True
                    st.session_state.user_data = user
                    st.success(f"Bienvenido(a), {user['nombre_completo']}")
                    st.rerun()
                else:
                    st.error("Credenciales incorrectas o usuario inactivo.")

        st.caption("ℹ️ Usuarios predeterminados: **admin** (Pass: `Multiesencias2026!`) / **ventas** (Pass: `Ventas2026!`)")


# Si no está autenticado, bloquear interfaz
if not st.session_state.authenticated:
    render_login()
    st.stop()


# ---------------------------------------------------------------------------
# CARGA DE ESTADO Y CONFIGURACIÓN MAESTRA
# ---------------------------------------------------------------------------
current_user = st.session_state.user_data
is_admin = current_user.get("rol") == "ADMIN"
master_cfg = get_master_config()


# ---------------------------------------------------------------------------
# SIDEBAR INSTITUCIONAL
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown(f"""
    <div style="background:#151D2A; border:1px solid #2D3E57; border-radius:8px; padding:12px; margin-bottom:14px;">
        <div style="font-size:1.1rem; font-weight:800; color:#3B82F6;">MULTIESENCIAS</div>
        <div style="font-size:0.7rem; font-weight:600; color:#94A3B8; text-transform:uppercase; letter-spacing:0.08em;">Suite Enterprise v4.0</div>
        <div style="font-size:0.75rem; color:#10B981; margin-top:4px;">● {current_user.get('nombre_completo')}</div>
        <div style="font-size:0.68rem; color:#60A5FA; font-weight:600;">Rol: {current_user.get('rol')}</div>
    </div>
    """, unsafe_allow_html=True)

    menu_options = [
        "📦 Gestión de Órdenes & Inventario Activo",
        "🧮 Cotizador B2B & Liquidación SAT",
        "📊 Valuación DCF & Sensibilidad",
        "💧 Tesorería & Liquidez (24M)",
        "🎲 Simulación @RISK (Monte Carlo)",
        "💼 Capital de Trabajo & CCC",
        "📦 Gestión de Inventario & EOQ",
        "📈 Rentabilidad, ROIC & EVA",
        "📋 Gestor Maestro en la Nube (CRUD)",
        "📥 Exportación Oficial a Excel"
    ]

    if is_admin:
        menu_options.extend([
            "⚙️ Configuración Maestra SAT",
            "👥 Gestión de Usuarios del Sistema"
        ])

    nav_selected = st.radio("Módulos del Sistema", menu_options, label_visibility="collapsed")

    st.markdown("---")
    c_out1, c_out2 = st.columns(2)
    with c_out1:
        if st.button("🚪 Cerrar Sesión", use_container_width=True):
            st.session_state.authenticated = False
            st.session_state.user_data = None
            st.rerun()
    with c_out2:
        if is_admin:
            if st.button("🧹 Limpiar Campos", use_container_width=True, help="Limpia todos los datos de los formularios"):
                for key in list(st.session_state.keys()):
                    if key not in ['authenticated', 'user_data']:
                        del st.session_state[key]
                st.success("Campos limpios.")
                st.rerun()


# ===========================================================================
# 1. GESTIÓN DE ÓRDENES & INVENTARIO ACTIVO
# ===========================================================================
if nav_selected == "📦 Gestión de Órdenes & Inventario Activo":
    st.markdown(hero_banner(
        "Control Operativo de Órdenes e Inventario en Tiempo Real",
        "ERP Cloud Engine",
        "Registro de salidas comerciales, abastecimiento internacional y rotación histórica de productos.",
        "Stock Final = Stock Inicial + Compras Recibidas - Ventas"
    ), unsafe_allow_html=True)

    tab_venta, tab_compra, tab_rotacion = st.tabs([
        "🛒 Registro de Venta (Salida)",
        "🚢 Orden de Compra (Abastecimiento)",
        "📊 Métricas de Rotación por SKU"
    ])

    # --- PESTAÑA 1: REGISTRO DE VENTA ---
    with tab_venta:
        st.markdown(section_header("Registro de Salida Comercial", icon="📤"), unsafe_allow_html=True)
        clientes = get_all_clientes()
        productos = get_all_productos()

        if not clientes or not productos:
            st.warning("Debe registrar al menos un cliente y un producto para generar ventas.")
        else:
            c1, c2 = st.columns(2)
            with c1:
                cli_map = {c["id_cliente"]: f"{c['codigo_cliente']} — {c['razon_social']}" for c in clientes}
                sel_cli_id = st.selectbox("Seleccione Cliente", options=list(cli_map.keys()), format_func=lambda k: cli_map[k])

            with c2:
                prod_map = {p["sku_codigo"]: f"{p['sku_codigo']} — {p['nombre_producto']} (Disp: {p['stock_actual']:,.1f} {p['unidad_medida']})" for p in productos}
                sel_sku = st.selectbox("Seleccione Producto (SKU)", options=list(prod_map.keys()), format_func=lambda k: prod_map[k])

            curr_prod = get_producto_by_sku(sel_sku)
            stock_disponible = curr_prod["stock_actual"] if curr_prod else 0.0
            precio_sug_gtq = curr_prod["costo_fob_moneda_origen"] * master_cfg.get("tipo_cambio_gtq_usd", 7.75) * 1.40 if curr_prod else 0.0

            # Tarjetas de estado en vivo
            st.markdown(kpi_row(
                kpi_card("Stock en Bodega", f"{stock_disponible:,.1f} {curr_prod.get('unidad_medida', 'U')}", "DISPONIBLE", "positive" if stock_disponible > 50 else "negative"),
                kpi_card("Precio Sugerido", safe_fmt(precio_sug_gtq, prefix="Q "), "MARGEN +40%", "accent"),
                kpi_card("Total Vendido Histórico", f"{curr_prod.get('total_vendido_historico', 0):,.1f}", "ROTACIÓN", "neutral")
            ), unsafe_allow_html=True)

            with st.form("form_registro_venta"):
                cv1, cv2, cv3 = st.columns(3)
                num_ov = cv1.text_input("No. Orden de Venta", value=f"OV-2026-{len(get_all_ordenes_venta()) + 1:03d}")
                cant_venta = cv2.number_input(f"Cantidad a Vender ({curr_prod.get('unidad_medida', 'U')})", min_value=1.0, max_value=max(stock_disponible, 1.0), value=min(100.0, max(stock_disponible, 1.0)), step=10.0)
                precio_unit_venta = cv3.number_input("Precio de Venta Unitario (Q)", min_value=0.01, value=round(precio_sug_gtq, 2), step=1.0, format="%.2f")

                total_factura = cant_venta * precio_unit_venta
                st.info(f"💰 Monto Total a Facturar: **Q {total_factura:,.2f}**")

                submit_venta = st.form_submit_button("🚀 Confirmar Venta y Descargar Inventario", type="primary")

                if submit_venta:
                    res_v = create_orden_venta(
                        numero_orden=num_ov,
                        id_cliente=sel_cli_id,
                        sku=sel_sku,
                        cantidad=cant_venta,
                        precio_unitario=precio_unit_venta,
                        id_usuario=current_user.get("id_usuario")
                    )
                    if res_v["success"]:
                        st.success(f"✓ {res_v['msg']}")
                        st.rerun()
                    else:
                        st.error(f"⚠ {res_v['msg']}")

    # --- PESTAÑA 2: REGISTRO DE ORDEN DE COMPRA ---
    with tab_compra:
        st.markdown(section_header("Abastecimiento Internacional & Landed Cost de Entrada", icon="📥"), unsafe_allow_html=True)
        proveedores = get_all_proveedores()
        rutas = get_all_rutas()

        if not proveedores or not productos:
            st.warning("Registre proveedores y productos para ingresar órdenes de compra.")
        else:
            cp1, cp2, cp3 = st.columns(3)
            with cp1:
                prv_map = {pr["id_proveedor"]: f"{pr['codigo_proveedor']} — {pr['nombre_empresa']}" for pr in proveedores}
                sel_prv_id = st.selectbox("Proveedor", options=list(prv_map.keys()), format_func=lambda k: prv_map[k])
            with cp2:
                sel_sku_compra = st.selectbox("SKU a Comprar", options=list(prod_map.keys()), format_func=lambda k: prod_map[k], key="sku_compra_key")
            with cp3:
                mod_compra = st.selectbox("Modalidad de Flete", ["MARÍTIMO", "AÉREO"])

            prod_c_info = get_producto_by_sku(sel_sku_compra)
            fob_base_usd = prod_c_info["costo_fob_moneda_origen"] if prod_c_info else 15.0

            with st.form("form_registro_compra"):
                cc1, cc2, cc3 = st.columns(3)
                num_oc = cc1.text_input("No. Orden de Compra", value=f"OC-2026-{len(get_all_ordenes_compra()) + 1:03d}")
                cant_compra = cc2.number_input("Cantidad a Comprar", min_value=1.0, value=1000.0, step=100.0)
                fob_unit_compra = cc3.number_input("FOB Unitario Negociado (USD)", value=float(fob_base_usd), step=0.5, format="%.2f")

                # Cálculo de liquidación automática en vivo
                tarifa_flete_estimada = 0.35 if mod_compra == "MARÍTIMO" else 1.85
                sat_res_compra = compute_landed_cost_sat(
                    fob_unitario_usd=fob_unit_compra,
                    volumen=cant_compra,
                    tarifa_flete_unitario_usd=tarifa_flete_estimada,
                    tipo_cambio=master_cfg.get("tipo_cambio_gtq_usd", 7.75),
                    tasa_dai_pct=prod_c_info.get("tasa_dai_sat_pct", 0.05) if prod_c_info else 0.05
                )

                st.markdown(f"""
                <div style="background:#1B2433; border:1px solid #2D3E57; border-radius:6px; padding:10px 14px; margin:10px 0; font-size:0.85rem;">
                    CIF Estimado: <strong>Q {sat_res_compra['cif_gtq']:,.2f}</strong> | 
                    DAI (SAT): <strong>Q {sat_res_compra['dai_gtq']:,.2f}</strong> | 
                    Landed Cost Total: <strong style="color:#10B981;">Q {sat_res_compra['landed_cost_total_gtq']:,.2f}</strong> | 
                    Costo Unitario de Ingreso: <strong style="color:#3B82F6;">Q {sat_res_compra['landed_cost_unitario_gtq']:,.2f} / unidad</strong>
                </div>
                """, unsafe_allow_html=True)

                auto_recibir = st.checkbox("📥 Recibir en bodega inmediatamente (Incrementa stock actual)", value=True)
                submit_compra = st.form_submit_button("🛒 Registrar Orden de Compra", type="primary")

                if submit_compra:
                    ok_c = create_orden_compra(
                        numero_orden=num_oc,
                        id_proveedor=sel_prv_id,
                        sku=sel_sku_compra,
                        modalidad=mod_compra,
                        cantidad=cant_compra,
                        costo_fob_total=sat_res_compra["fob_total_usd"],
                        landed_unitario=sat_res_compra["landed_cost_unitario_gtq"],
                        auto_recibir=auto_recibir
                    )
                    if ok_c:
                        st.success("✓ Orden de compra registrada correctamente.")
                        st.rerun()
                    else:
                        st.error("Error al registrar la orden de compra.")

        # Tabla de órdenes de compra para recepción
        st.markdown(section_header("Órdenes de Compra Registradas", icon="📋"), unsafe_allow_html=True)
        ocs = get_all_ordenes_compra()
        if ocs:
            df_ocs = pd.DataFrame(ocs)
            st.dataframe(df_ocs, use_container_width=True)

            # Botón rápido para recibir en bodega órdenes pendientes
            pendientes = [o for o in ocs if o["estado"] != "RECIBIDA_EN_BODEGA"]
            if pendientes:
                st.markdown("##### Recepción de Mercancía Pendiente")
                col_p1, col_p2 = st.columns([3, 1])
                with col_p1:
                    pend_opts = {p["id_orden_compra"]: f"{p['numero_orden']} — {p['producto']} ({p['cantidad']:,.1f} uds)" for p in pendientes}
                    sel_p_id = st.selectbox("Seleccione orden recibida", options=list(pend_opts.keys()), format_func=lambda k: pend_opts[k])
                with col_p2:
                    st.write("")
                    st.write("")
                    if st.button("📦 Marcar como Recibida", type="primary"):
                        if recibir_orden_compra(sel_p_id):
                            st.success("Stock incrementado exitosamente.")
                            st.rerun()

    # --- PESTAÑA 3: MÉTRICAS DE ROTACIÓN POR SKU ---
    with tab_rotacion:
        st.markdown(section_header("Métricas de Inventario y Rotación por SKU", icon="📈"), unsafe_allow_html=True)
        todos_prods = get_all_productos()
        if todos_prods:
            df_p = pd.DataFrame(todos_prods)

            # Cálculo de valorización
            tc_act = master_cfg.get("tipo_cambio_gtq_usd", 7.75)
            df_p["valor_inventario_gtq"] = df_p["stock_actual"] * df_p["costo_fob_moneda_origen"] * tc_act
            df_p["estatus_stock"] = np.where(df_p["stock_actual"] <= 200, "🔴 Crítico", np.where(df_p["stock_actual"] <= 800, "🟡 Normal", "🟢 Óptimo"))

            tot_stock = df_p["stock_actual"].sum()
            tot_ventas_hist = df_p["total_vendido_historico"].sum()
            tot_valor_inv = df_p["valor_inventario_gtq"].sum()

            st.markdown(kpi_row(
                kpi_card("Total Unidades en Bodega", f"{tot_stock:,.1f}", "INVENTARIO FÍSICO", "positive"),
                kpi_card("Total Unidades Vendidas", f"{tot_ventas_hist:,.1f}", "SALIDAS HISTÓRICAS", "accent"),
                kpi_card("Valorización Bodega (FOB)", f"Q {tot_valor_inv:,.2f}", "ACTIVO REAL", "neutral")
            ), unsafe_allow_html=True)

            st.dataframe(
                df_p[["sku_codigo", "nombre_producto", "tipo_producto", "proveedor_nombre", "stock_actual", "total_vendido_historico", "unidad_medida", "valor_inventario_gtq", "estatus_stock"]],
                column_config={
                    "sku_codigo": "SKU",
                    "nombre_producto": "Producto",
                    "tipo_producto": "Tipo",
                    "stock_actual": st.column_config.NumberColumn("Stock Actual", format="%.1f"),
                    "total_vendido_historico": st.column_config.NumberColumn("Ventas Históricas", format="%.1f"),
                    "valor_inventario_gtq": st.column_config.NumberColumn("Valoración (Q)", format="Q %.2f"),
                    "estatus_stock": "Estado"
                },
                use_container_width=True
            )

        st.markdown(section_header("Historial Completo de Ventas Realizadas", icon="📜"), unsafe_allow_html=True)
        ovs = get_all_ordenes_venta()
        if ovs:
            st.dataframe(pd.DataFrame(ovs), use_container_width=True)
        else:
            st.info("No se han registrado salidas comerciales aún.")


# ===========================================================================
# 2. COTIZADOR B2B & LIQUIDACIÓN SAT (SINGLE SOURCE OF TRUTH)
# ===========================================================================
elif nav_selected == "🧮 Cotizador B2B & Liquidación SAT":
    st.markdown(hero_banner(
        "Cotizador Operativo & Cascada Financiera Automática",
        "Single Source of Truth",
        "Seleccione Cliente, SKU y Ruta. El sistema calcula en cascada el costo aduanero, precio y márgenes.",
        "Landed Cost = CIF + DAI + Gastos Locales"
    ), unsafe_allow_html=True)

    clientes = get_all_clientes()
    productos = get_all_productos()
    rutas = get_all_rutas()

    if not clientes or not productos:
        st.warning("Debe registrar clientes y productos para cotizar.")
    else:
        c1, c2, c3 = st.columns(3)
        with c1:
            cli_map = {c["id_cliente"]: f"{c['codigo_cliente']} — {c['razon_social']}" for c in clientes}
            s_cli_id = st.selectbox("Cliente", options=list(cli_map.keys()), format_func=lambda k: cli_map[k], key="cot_cli")
        with c2:
            prod_map = {p["sku_codigo"]: f"{p['sku_codigo']} — {p['nombre_producto']}" for p in productos}
            s_sku = st.selectbox("Producto (SKU)", options=list(prod_map.keys()), format_func=lambda k: prod_map[k], key="cot_sku")
        with c3:
            modalidad_cot = st.selectbox("Modalidad de Flete", ["MARÍTIMO", "AÉREO"], key="cot_mod")

        prod_obj = get_producto_by_sku(s_sku)
        fob_u_base = prod_obj["costo_fob_moneda_origen"] if prod_obj else 18.0

        c_v1, c_v2, c_v3 = st.columns(3)
        vol_mensual_cot = c_v1.number_input("Volumen Mensual Proyectado (uds)", min_value=1.0, value=1500.0, step=100.0, key="cot_vol")
        p_venta_cot = c_v2.number_input("Precio de Venta Sugerido (Q/unidad)", min_value=0.01, value=round(fob_u_base * 7.75 * 1.5, 2), step=1.0, key="cot_p_venta")
        tc_cot = c_v3.number_input("Tipo de Cambio (GTQ/USD)", value=master_cfg.get("tipo_cambio_gtq_usd", 7.75), step=0.05, key="cot_tc")

        tarifa_fl = 0.35 if modalidad_cot == "MARÍTIMO" else 1.85

        # Ejecución del motor SAT
        sat_liquidation = compute_landed_cost_sat(
            fob_unitario_usd=fob_u_base,
            volumen=vol_mensual_cot,
            tarifa_flete_unitario_usd=tarifa_fl,
            tipo_cambio=tc_cot,
            tasa_dai_pct=prod_obj.get("tasa_dai_sat_pct", 0.05) if prod_obj else 0.05,
            gastos_aduanales_locales_usd=1200.0 if modalidad_cot == "MARÍTIMO" else 450.0
        )

        # Si es producto formulado internamente, calcular costo con merma
        if prod_obj and prod_obj.get("tipo_producto") == "FORMULACION_INTERNA":
            form_res = compute_formulation_cost(
                costo_mp_base_gtq=sat_liquidation["landed_cost_unitario_gtq"],
                proporcion_peso=0.85,
                merma_tecnica_pct=0.04,
                aditivos_empaque_gtq=8.50
            )
            costo_unitario_final_gtq = form_res["costo_unitario_final_gtq"]
            st.info(f"🧪 Producto de Formulación Interna: Costo MP con Merma: Q {form_res['costo_mp_con_merma_gtq']:,.2f} + Aditivos: Q {form_res['aditivos_empaque_gtq']:,.2f}")
        else:
            costo_unitario_final_gtq = sat_liquidation["landed_cost_unitario_gtq"]

        # KPIs Principales de la Cotización
        utilidad_unitaria = p_venta_cot - costo_unitario_final_gtq
        margen_bruto_pct = utilidad_unitaria / p_venta_cot if p_venta_cot > 0 else 0.0
        ingresos_mensuales = vol_mensual_cot * p_venta_cot

        st.markdown(kpi_row(
            kpi_card("Landed Cost Unitario", safe_fmt(costo_unitario_final_gtq, prefix="Q "), "COSTO REAL SAT", "accent"),
            kpi_card("Precio de Venta", safe_fmt(p_venta_cot, prefix="Q "), "PRECIO SUGERIDO", "neutral"),
            kpi_card("Margen Bruto", safe_fmt(margen_bruto_pct * 100, suffix="%"), "MARGEN COMERCIAL", "positive" if margen_bruto_pct > 0.25 else "warning"),
            kpi_card("Ingresos Mensuales", safe_fmt(ingresos_mensuales, prefix="Q "), "VENTAS PROYECTADAS", "positive")
        ), unsafe_allow_html=True)

        # Detalle de Liquidación Aduanera SAT
        st.markdown(section_header("Desglose Paso a Paso - Liquidación Aduanera SAT", icon="🏛️"), unsafe_allow_html=True)
        col_s1, col_s2, col_s3, col_s4 = st.columns(4)
        col_s1.metric("FOB Total (USD)", f"${sat_liquidation['fob_total_usd']:,.2f}")
        col_s2.metric("CIF Total (GTQ)", f"Q {sat_liquidation['cif_gtq']:,.2f}")
        col_s3.metric("DAI Arancel SAT (GTQ)", f"Q {sat_liquidation['dai_gtq']:,.2f}")
        col_s4.metric("IVA Crédito Fiscal (GTQ)", f"Q {sat_liquidation['iva_importacion_gtq']:,.2f}")


# ===========================================================================
# 3. VALUACIÓN DCF & SENSIBILIDAD
# ===========================================================================
elif nav_selected == "📊 Valuación DCF & Sensibilidad":
    st.markdown(hero_banner(
        "Valuación por Flujo de Caja Libre Descontado (DCF)",
        "Finanzas Corporativas",
        "Proyección de FCFF a 5 años, Valor Terminal Gordon-Shapiro, VAN, TIR y Payback.",
        "VAN = ∑ [FCFF_t / (1 + WACC)^t] + Valor Terminal - Inversión Inicial"
    ), unsafe_allow_html=True)

    # Defaults vinculados al proyecto
    vol_def = st.session_state.get("cot_vol", 1500.0)
    p_def = st.session_state.get("cot_p_venta", 210.0)
    flujo_def = float(vol_def * p_def * 0.15)
    
    st.info("💡 Valores predeterminados vinculados al proyecto seleccionado en el Cotizador.")
    is_one_time = st.checkbox("🛑 Proyecto de Compra Única (Sin flujos recurrentes)", value=False)

    c1, c2, c3 = st.columns(3)
    inv_inicial = c1.number_input("Inversión Inicial en CapEx / Inventario (Q)", value=float(vol_def * 100.0), step=10000.0)
    fcff_base_mensual = c2.number_input("Flujo de Caja Libre (Q)", value=flujo_def, step=1000.0)
    wacc_dcf = c3.number_input("WACC Aplicable (%)", value=master_cfg.get("wacc_institucional", 0.1072) * 100, step=0.25) / 100.0

    if is_one_time:
        monthly_flows = [fcff_base_mensual] + [0.0] * 11
    else:
        monthly_flows = [fcff_base_mensual * (1.01 ** i) for i in range(12)]
        
    dcf_res = compute_valuation_dcf(
        inversion_inicial_gtq=inv_inicial,
        fcff_12_meses=monthly_flows,
        wacc=wacc_dcf
    )

    k_npv = kpi_card("VAN / NPV", safe_fmt(dcf_res["npv"], prefix="Q "), "CREA VALOR" if dcf_res["npv"] > 0 else "DESTRUYE", "positive" if dcf_res["npv"] > 0 else "negative")
    k_tir = kpi_card("TIR / IRR", safe_fmt(dcf_res["irr"] * 100 if dcf_res["irr"] else None, suffix="%"), "RETORNO PROYECTADO", "positive" if dcf_res["irr"] and dcf_res["irr"] > wacc_dcf else "warning")
    k_pi = kpi_card("Índice Rentabilidad (PI)", safe_fmt(dcf_res["pi"], suffix="x"), "RENTABILIDAD", "positive" if dcf_res["pi"] >= 1.0 else "negative")
    k_pb = kpi_card("Payback Descontado", f"{dcf_res['payback_meses']} meses" if dcf_res["payback_meses"] else "No recupera en 12m", "RECUPERACIÓN", "positive" if dcf_res["payback_meses"] else "warning")

    st.markdown(kpi_row(k_npv, k_tir, k_pi, k_pb), unsafe_allow_html=True)

    # Gráfico Waterfall de Flujos de Caja
    st.markdown(section_header("Trayectoria de Flujo de Caja Libre", icon="💹"), unsafe_allow_html=True)
    x_wf = ["Inv. Inicial"] + [f"M{i+1}" for i in range(12)] + ["Valor Terminal"]
    y_wf = [-inv_inicial] + monthly_flows + [dcf_res["terminal_value"]]
    m_wf = ["absolute"] + ["relative"] * 12 + ["total"]

    fig_wf = go.Figure(go.Waterfall(
        x=x_wf, y=y_wf, measure=m_wf,
        decreasing={"marker": {"color": "#EF4444"}},
        increasing={"marker": {"color": "#10B981"}},
        totals={"marker": {"color": "#3B82F6"}},
        connector={"line": {"color": "#2D3E57", "width": 1, "dash": "dot"}},
        hovertemplate="<b>%{x}</b><br>Q %{y:,.0f}<extra></extra>"
    ))
    fig_wf.update_layout(
        paper_bgcolor="#151D2A", plot_bgcolor="#151D2A",
        font=dict(color="#94A3B8"), height=350, margin=dict(l=40, r=20, t=30, b=40)
    )
    st.plotly_chart(fig_wf, use_container_width=True)


# ===========================================================================
# 4. TESORERÍA & LIQUIDEZ (24 MESES)
# ===========================================================================
elif nav_selected == "💧 Tesorería & Liquidez (24M)":
    st.markdown(hero_banner(
        "Proyección de Tesorería & Curva de Liquidez (24 Meses)",
        "Control de Caja",
        "Modelado de desfase de liquidez derivado del Ciclo de Conversión de Efectivo (CCC).",
        "Saldo Acumulado_t = Saldo_{t-1} + Flujo Neto_t"
    ), unsafe_allow_html=True)

    vol_def = st.session_state.get("cot_vol", 1500.0)
    p_def = st.session_state.get("cot_p_venta", 210.0)
    flujo_def = float(vol_def * p_def * 0.15)
    
    st.info("💡 Valores predeterminados vinculados al proyecto seleccionado.")
    is_one_time_t = st.checkbox("🛑 Proyecto de Compra Única (Impacto en caja de un solo golpe)", value=False)

    c1, c2 = st.columns(2)
    inv_t = c1.number_input("Inversión de Arranque / Capital Inicial (Q)", value=float(vol_def * 100.0), step=10000.0)
    ccc_dias_t = c2.number_input("Ciclo de Conversión de Efectivo CCC (días)", value=48.0, step=5.0)

    if is_one_time_t:
        sample_flows = [flujo_def] + [0.0] * 11
    else:
        sample_flows = [flujo_def * (1.015 ** i) for i in range(12)]
    t_res = compute_treasury_24m(
        inversion_inicial_gtq=inv_t,
        fcff_12_meses=sample_flows,
        ccc_dias=ccc_dias_t
    )

    k_def = kpi_card("Pico Máximo de Déficit", safe_fmt(t_res["peak_deficit_gtq"], prefix="Q "), "MÁXIMO RIESGO", "negative" if t_res["peak_deficit_gtq"] > 0 else "positive")
    k_rec = kpi_card("Mes de Equilibrio", f"Mes {t_res['mes_recuperacion']}" if t_res["mes_recuperacion"] else "No recupera", "RECUPERACIÓN CAJA", "positive" if t_res["mes_recuperacion"] else "warning")
    k_fin = kpi_card("Saldo Final M24", safe_fmt(t_res["saldo_final_24m"], prefix="Q "), "SALUD FINANCIERA", "positive" if t_res["saldo_final_24m"] > 0 else "negative")

    st.markdown(kpi_row(k_def, k_rec, k_fin), unsafe_allow_html=True)

    # Gráfico de Línea de Caja
    meses_x = [f"M{i+1}" for i in range(len(t_res["cum_cash_series"]))]
    vals_y = t_res["cum_cash_series"]

    fig_t = go.Figure()
    fig_t.add_trace(go.Scatter(
        x=meses_x, y=vals_y, mode="lines+markers",
        line=dict(color="#3B82F6", width=2.5),
        name="Saldo Acumulado"
    ))
    fig_t.add_hline(y=0, line_dash="dash", line_color="#EF4444", annotation_text="Punto de Equilibrio (Q 0)")
    fig_t.update_layout(
        paper_bgcolor="#151D2A", plot_bgcolor="#151D2A",
        font=dict(color="#94A3B8"), height=350, margin=dict(l=40, r=20, t=30, b=40)
    )
    st.plotly_chart(fig_t, use_container_width=True)


# ===========================================================================
# 5. SIMULACIÓN @RISK (MONTE CARLO LOGÍSTICO)
# ===========================================================================
elif nav_selected == "🎲 Simulación @RISK (Monte Carlo)":
    st.markdown(hero_banner(
        "Simulador Estocástico @RISK — 10,000 Iteraciones Vectorizadas",
        "Gestión de Riesgo Logístico",
        "Simulación de volatilidad de fletes marítimos/aéreos y tipo de cambio sobre el Landed Cost y VAN.",
        "Value at Risk (VaR 5%) = Percentil 5% de la Distribución del VAN"
    ), unsafe_allow_html=True)

    sku_cot = st.session_state.get("cot_sku")
    fob_def = 18.50
    if sku_cot:
        prod_obj = get_producto_by_sku(sku_cot)
        if prod_obj:
            fob_def = prod_obj["costo_fob_moneda_origen"]

    vol_def = st.session_state.get("cot_vol", 1500.0)
    p_def = st.session_state.get("cot_p_venta", 210.0)

    st.info("💡 Valores predeterminados vinculados al proyecto seleccionado.")
    cm1, cm2, cm3 = st.columns(3)
    fob_mc = cm1.number_input("FOB Unitario Base (USD)", value=float(fob_def), step=0.5)
    vol_mc = cm2.number_input("Volumen (unidades)", value=float(vol_def), step=100.0)
    precio_mc = cm3.number_input("Precio de Venta Unitario (Q)", value=float(p_def), step=5.0)

    if st.button("🎲 Ejecutar 10,000 Iteraciones Monte Carlo", type="primary"):
        with st.spinner("Ejecutando simulaciones estocásticas vectorizadas con NumPy..."):
            mc_res = run_monte_carlo_logistics(
                fob_unitario_usd=fob_mc,
                volumen_mensual=vol_mc,
                precio_venta_gtq=precio_mc,
                tarifa_flete_unitario_usd=0.35,
                tipo_cambio_base=master_cfg.get("tipo_cambio_gtq_usd", 7.75)
            )

        st.session_state["mc_last_res"] = mc_res
        st.success("✓ Simulación completada exitosamente.")

    if "mc_last_res" in st.session_state:
        res_m = st.session_state["mc_last_res"]
        st.markdown(kpi_row(
            kpi_card("VaR al 5% (Peor Escenario)", safe_fmt(res_m["var_5pct"], prefix="Q "), "MÁXIMA PÉRDIDA 95% CONF.", "negative" if res_m["var_5pct"] < 0 else "positive"),
            kpi_card("P50 (Mediana Esperada)", safe_fmt(res_m["p50_npv"], prefix="Q "), "MEDIANA", "positive" if res_m["p50_npv"] > 0 else "negative"),
            kpi_card("P(Pérdida en VAN)", safe_fmt(res_m["prob_npv_negativo"] * 100, suffix="%"), "PROBABILIDAD VAN < 0", "warning" if res_m["prob_npv_negativo"] > 0.15 else "positive"),
            kpi_card("Landed Cost P95", safe_fmt(res_m["landed_cost_p95"], prefix="Q "), "COSTO MÁX. ESPERADO", "accent")
        ), unsafe_allow_html=True)

        # Histograma Plotly
        dist_npv = res_m["npv_dist"]
        fig_hist = go.Figure()
        fig_hist.add_trace(go.Histogram(
            x=dist_npv, nbinsx=50,
            marker_color="#3B82F6", opacity=0.85
        ))
        fig_hist.add_vline(x=res_m["var_5pct"], line_color="#EF4444", line_width=2, line_dash="dash", annotation_text=f"VaR 5%: Q {res_m['var_5pct']:,.0f}")
        fig_hist.add_vline(x=res_m["p50_npv"], line_color="#10B981", line_width=2, annotation_text=f"Mediana: Q {res_m['p50_npv']:,.0f}")
        fig_hist.update_layout(
            paper_bgcolor="#151D2A", plot_bgcolor="#151D2A",
            font=dict(color="#94A3B8"), height=350, margin=dict(l=40, r=20, t=30, b=40),
            xaxis_title="VAN Proyectado (Q)", yaxis_title="Frecuencia"
        )
        st.plotly_chart(fig_hist, use_container_width=True)


# ===========================================================================
# 6. CAPITAL DE TRABAJO & CCC
# ===========================================================================
elif nav_selected == "💼 Capital de Trabajo & CCC":
    st.markdown(hero_banner(
        "Ciclo de Conversión de Efectivo (CCC) & Capital Neto de Trabajo (NWC)",
        "Doctrina Berk & DeMarzo",
        "Control de días de inventario (DIO), cobro (DSO) y pago (DPO) con impacto directo en caja.",
        "CCC = DIO + DSO - DPO   |   NWC = (Efectivo + Inventario + CxC) - CxP"
    ), unsafe_allow_html=True)

    cw1, cw2, cw3 = st.columns(3)
    inv_ccc = cw1.number_input("Inventario en Bodega (Q)", value=180000.0, step=10000.0)
    cdbv_ccc = cw2.number_input("CDBV Anual (Q)", value=1200000.0, step=50000.0)
    cxc_ccc = cw3.number_input("Cuentas por Cobrar Clientes (Q)", value=220000.0, step=10000.0)

    cw4, cw5, cw6 = st.columns(3)
    ventas_ccc = cw4.number_input("Ventas Anuales (Q)", value=1850000.0, step=50000.0)
    cxp_ccc = cw5.number_input("Cuentas por Pagar Proveedores (Q)", value=140000.0, step=10000.0)
    cash_ccc = cw6.number_input("Efectivo Operativo Mínimo (Q)", value=50000.0, step=5000.0)

    ccc_res = compute_ccc_and_nwc(
        inventario_promedio_gtq=inv_ccc,
        cdbv_anual_gtq=cdbv_ccc,
        cxc_promedio_gtq=cxc_ccc,
        ventas_anuales_gtq=ventas_ccc,
        cxp_promedio_gtq=cxp_ccc,
        efectivo_minimo_gtq=cash_ccc
    )

    st.markdown(kpi_row(
        kpi_card("Días Inventario (DIO)", f"{ccc_res['dio']} días", "ROTACIÓN", "neutral"),
        kpi_card("Días Cobro (DSO)", f"{ccc_res['dso']} días", "CRÉDITO CLIENTES", "warning" if ccc_res["dso"] > 45 else "positive"),
        kpi_card("Días Pago (DPO)", f"{ccc_res['dpo']} días", "PLAZO PROVEEDORES", "positive"),
        kpi_card("Ciclo Efectivo (CCC)", f"{ccc_res['ccc']} días", ccc_res["evaluacion"], ccc_res["color"])
    ), unsafe_allow_html=True)

    st.markdown(kpi_row(
        kpi_card("Capital Neto Trabajo (NWC)", safe_fmt(ccc_res["nwc"], prefix="Q "), "NWC OPERATIVO", "positive" if ccc_res["nwc"] > 0 else "negative"),
        kpi_card("Financiamiento Requerido", safe_fmt(ccc_res["financiamiento_req_gtq"], prefix="Q "), "REQUERIMIENTO DIARIO", "accent")
    ), unsafe_allow_html=True)


# ===========================================================================
# 7. GESTIÓN DE INVENTARIO & EOQ
# ===========================================================================
elif nav_selected == "📦 Gestión de Inventario & EOQ":
    st.markdown(hero_banner(
        "Lote Económico de Pedido (EOQ) & Costo de Capital WACC",
        "Optimización Logística",
        "Cálculo del tamaño de orden óptimo que minimiza el costo total anual integrando el WACC institucional.",
        "EOQ = √[ (2 × D × S) / (C × (c_físicos + WACC)) ]"
    ), unsafe_allow_html=True)

    ce1, ce2, ce3 = st.columns(3)
    d_eoq = ce1.number_input("Demanda Anual (unidades)", value=18000.0, step=1000.0)
    s_eoq = ce2.number_input("Costo Fijo por Pedido / Orden S (Q)", value=2500.0, step=100.0)
    c_eoq = ce3.number_input("Costo Unitario de Adquisición C (Q)", value=145.0, step=5.0)

    eoq_res = compute_eoq(
        demanda_anual_unidades=d_eoq,
        costo_ordenar_s_gtq=s_eoq,
        costo_unitario_c_gtq=c_eoq,
        wacc=master_cfg.get("wacc_institucional", 0.1072)
    )

    st.markdown(kpi_row(
        kpi_card("Lote Óptimo (EOQ)", f"{eoq_res['eoq']:,.0f} uds", "TAMAÑO DE PEDIDO", "positive"),
        kpi_card("Frecuencia de Compra", f"Cada {eoq_res['dias_entre_pedidos']:.0f} días", f"{eoq_res['pedidos_por_ano']:.1f} pedidos/año", "accent"),
        kpi_card("Costo Anual Ordenar", safe_fmt(eoq_res["costo_ordenar_anual"], prefix="Q "), "PEDIDOS", "neutral"),
        kpi_card("Costo Anual Mantener", safe_fmt(eoq_res["costo_mantener_anual"], prefix="Q "), "HOLDING + WACC", "warning")
    ), unsafe_allow_html=True)


# ===========================================================================
# 8. RENTABILIDAD, ROIC & EVA
# ===========================================================================
elif nav_selected == "📈 Rentabilidad, ROIC & EVA":
    st.markdown(hero_banner(
        "Rentabilidad del Capital Invertido (ROIC) & Creación de Valor (EVA)",
        "Creación de Valor Económico",
        "Evaluación del retorno sobre el capital empleado contra el costo promedio de capital WACC.",
        "ROIC = NOPAT / Capital Empleado   |   EVA = NOPAT - (Capital Empleado × WACC)"
    ), unsafe_allow_html=True)

    cr1, cr2, cr3 = st.columns(3)
    v_an = cr1.number_input("Ventas Totales Anuales (Q)", value=2500000.0, step=50000.0)
    c_an = cr2.number_input("Costo de Ventas CDBV (Q)", value=1650000.0, step=50000.0)
    op_an = cr3.number_input("Gastos Operativos OPEX (Q)", value=320000.0, step=10000.0)

    cr4, cr5, cr6 = st.columns(3)
    dep_an = cr4.number_input("Depreciación Anual (Q)", value=45000.0, step=5000.0)
    nwc_an = cr5.number_input("Capital Neto de Trabajo NWC (Q)", value=280000.0, step=10000.0)
    afn_an = cr6.number_input("Activos Fijos Netos PP&E (Q)", value=350000.0, step=10000.0)

    prof_res = compute_profitability_and_eva(
        ventas_anuales_gtq=v_an,
        cdbv_anual_gtq=c_an,
        gastos_operativos_gtq=op_an,
        depreciacion_anual_gtq=dep_an,
        nwc_gtq=nwc_an,
        activos_fijos_netos_gtq=afn_an,
        tasa_isr=master_cfg.get("tasa_isr_sat", 0.25),
        wacc=master_cfg.get("wacc_institucional", 0.1072)
    )

    st.markdown(kpi_row(
        kpi_card("Margen Bruto", safe_fmt(prof_res["margen_bruto"] * 100, suffix="%"), "MARGEN", "positive" if prof_res["margen_bruto"] > 0.25 else "warning"),
        kpi_card("EBIT Operativo", safe_fmt(prof_res["ebit"], prefix="Q "), "RESULTADO OPERATIVO", "positive" if prof_res["ebit"] > 0 else "negative"),
        kpi_card("NOPAT (Post ISR)", safe_fmt(prof_res["nopat"], prefix="Q "), "DESPUÉS DE IMPUESTOS", "accent"),
        kpi_card("ROIC Institucional", safe_fmt(prof_res["roic"] * 100, suffix="%"), "RETORNO DE CAPITAL", "positive" if prof_res["roic"] > master_cfg.get("wacc_institucional", 0.1072) else "negative"),
        kpi_card("EVA Económico", safe_fmt(prof_res["eva"], prefix="Q "), "CREA VALOR" if prof_res["crea_valor"] else "DESTRUYE VALOR", "positive" if prof_res["crea_valor"] else "negative")
    ), unsafe_allow_html=True)


# ===========================================================================
# 9. GESTOR MAESTRO EN LA NUBE (CRUD COMPARTIDO)
# ===========================================================================
elif nav_selected == "📋 Gestor Maestro en la Nube (CRUD)":
    st.markdown(hero_banner(
        "Gestión Maestra de Entidades en Tiempo Real",
        "Cloud Database",
        "Altas y modificaciones compartidas de Proveedores, Rutas de Flete, Productos y Clientes.",
        "Sincronización Inmediata para Todos los Usuarios"
    ), unsafe_allow_html=True)

    t_prv, t_rut, t_prod, t_cli = st.tabs(["🏭 Proveedores", "🚢 Rutas de Flete", "📦 Productos", "👤 Clientes"])

    with t_prv:
        st.markdown(section_header("Catálogo de Proveedores", icon="🏭"), unsafe_allow_html=True)
        with st.expander("➕ Dar de Alta Nuevo Proveedor"):
            with st.form("form_add_prov"):
                p_c1, p_c2 = st.columns(2)
                p_cod = p_c1.text_input("Código (ej. PRV-COL-04)")
                p_nom = p_c2.text_input("Razón Social")
                p_c3, p_c4, p_c5 = st.columns(3)
                p_pais = p_c3.text_input("País de Origen", value="Colombia")
                p_dias = p_c4.number_input("Días de Crédito (DPO)", value=30, step=5)
                p_mon = p_c5.selectbox("Moneda", ["USD", "EUR", "BRL", "CNY"])
                if st.form_submit_button("Crear Proveedor", type="primary"):
                    if create_proveedor(p_cod, p_nom, p_pais, p_dias, p_mon):
                        st.success("Proveedor guardado exitosamente.")
                        st.rerun()
                    else:
                        st.error("Error: Verifique que el código no esté duplicado.")
        st.dataframe(pd.DataFrame(get_all_proveedores()), use_container_width=True)

    with t_rut:
        st.markdown(section_header("Rutas de Flete Internacional", icon="🚢"), unsafe_allow_html=True)
        provs = get_all_proveedores()
        with st.expander("➕ Dar de Alta Nueva Ruta de Flete"):
            with st.form("form_add_ruta"):
                r_c1, r_c2 = st.columns(2)
                pr_dict = {p["id_proveedor"]: p["nombre_empresa"] for p in provs}
                r_prv = r_c1.selectbox("Proveedor Asociado", options=list(pr_dict.keys()), format_func=lambda k: pr_dict[k]) if pr_dict else 0
                r_mod = r_c2.selectbox("Modalidad", ["MARÍTIMO", "AÉREO"])
                r_c3, r_c4 = st.columns(2)
                r_orig = r_c3.text_input("Puerto / Aeropuerto Origen", value="Puerto de Buenaventura")
                r_dest = r_c4.text_input("Puerto / Aeropuerto Destino", value="Puerto Quetzal")
                r_c5, r_c6, r_c7, r_c8 = st.columns(4)
                r_flete = r_c5.number_input("Tarifa Flete Unit (USD)", value=0.30, step=0.05)
                r_seg = r_c6.number_input("Tasa Seguro (%)", value=1.0, step=0.1) / 100.0
                r_aduana = r_c7.number_input("Gastos Aduana Locales (USD)", value=900.0, step=50.0)
                r_dias = r_c8.number_input("Tiempo Tránsito (días)", value=14, step=1)
                if st.form_submit_button("Crear Ruta", type="primary"):
                    if create_ruta(r_prv, r_mod, r_orig, r_dest, r_flete, r_seg, r_aduana, r_dias):
                        st.success("Ruta creada.")
                        st.rerun()
                    else:
                        st.error("Error al crear la ruta.")
        st.dataframe(pd.DataFrame(get_all_rutas()), use_container_width=True)

    with t_prod:
        st.markdown(section_header("Catálogo Maestro de Productos", icon="📦"), unsafe_allow_html=True)
        with st.expander("➕ Dar de Alta Nuevo Producto"):
            with st.form("form_add_prod"):
                pd_c1, pd_c2 = st.columns(2)
                pd_sku = pd_c1.text_input("SKU Código (ej. 285 o ME-FORM-20)")
                pd_nom = pd_c2.text_input("Nombre del Producto")
                pd_c3, pd_c4, pd_c5 = st.columns(3)
                pd_tipo = pd_c3.selectbox("Tipo de Producto", ["DISTRIBUCION_DIRECTA", "FORMULACION_INTERNA"])
                pd_prv = pd_c4.selectbox("Proveedor Defecto", options=list(pr_dict.keys()), format_func=lambda k: pr_dict[k]) if pr_dict else 0
                pd_um = pd_c5.selectbox("Unidad de Medida", ["KG", "L", "UNIDAD"])
                pd_c6, pd_c7, pd_c8 = st.columns(3)
                pd_fob = pd_c6.number_input("Costo FOB (USD)", value=15.0, step=0.5)
                pd_dai = pd_c7.selectbox("Tasa DAI SAT", [0.00, 0.05, 0.10, 0.15], index=1)
                pd_stock = pd_c8.number_input("Stock Inicial en Bodega", value=0.0, step=10.0)
                if st.form_submit_button("Guardar Producto", type="primary"):
                    if create_producto(pd_sku, pd_nom, pd_tipo, pd_prv, pd_fob, pd_dai, pd_um, pd_stock):
                        st.success("Producto creado exitosamente.")
                        st.rerun()
                    else:
                        st.error("Error: Verifique que el SKU no esté duplicado.")
        st.dataframe(pd.DataFrame(get_all_productos()), use_container_width=True)

    with t_cli:
        st.markdown(section_header("Catálogo de Clientes Corporativos", icon="👤"), unsafe_allow_html=True)
        with st.expander("➕ Dar de Alta Nuevo Cliente"):
            with st.form("form_add_cli"):
                cl_c1, cl_c2 = st.columns(2)
                cl_cod = cl_c1.text_input("Código Cliente (ej. CLI-004)")
                cl_raz = cl_c2.text_input("Razón Social")
                cl_c3, cl_c4, cl_c5 = st.columns(3)
                cl_nit = cl_c3.text_input("NIT", value="CF")
                cl_dso = cl_c4.number_input("Días de Crédito (DSO)", value=30, step=5)
                cl_lim = cl_c5.number_input("Límite de Crédito (Q)", value=100000.0, step=10000.0)
                cl_riesgo = st.selectbox("Categoría de Riesgo", ["A", "B", "C"])
                if st.form_submit_button("Crear Cliente", type="primary"):
                    if create_cliente(cl_cod, cl_raz, cl_nit, cl_dso, cl_lim, cl_riesgo):
                        st.success("Cliente guardado.")
                        st.rerun()
                    else:
                        st.error("Error: Verifique que el código no esté duplicado.")
        st.dataframe(pd.DataFrame(get_all_clientes()), use_container_width=True)


# ===========================================================================
# 10. EXPORTACIÓN OFICIAL A EXCEL
# ===========================================================================
elif nav_selected == "📥 Exportación Oficial a Excel":
    st.markdown(hero_banner(
        "Generador de Reportes Corporativos Excel (.xlsx)",
        "Reporting Institucional",
        "Descargue el libro de trabajo con fórmulas dinámicas vivas, liquidación aduanera y control de inventario.",
        "4 Hojas: Resumen KPI | Liquidación SAT | Ventas e Inventario | Flujo 12M con =NPV() y =IRR()"
    ), unsafe_allow_html=True)

    if st.button("📥 Generar y Descargar Reporte Ejecutivo Oficial (.xlsx)", type="primary"):
        with st.spinner("Construyendo libro de Excel multi-pestaña con fórmulas nativas..."):
            tmp_excel = tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx")

            # Preparación de datos reales
            sat_sample = compute_landed_cost_sat(
                fob_unitario_usd=18.50,
                volumen=1500.0,
                tarifa_flete_unitario_usd=0.35,
                tipo_cambio=master_cfg.get("tipo_cambio_gtq_usd", 7.75)
            )

            dcf_sample = compute_valuation_dcf(
                inversion_inicial_gtq=150000.0,
                fcff_12_meses=[22000.0 * (1.01 ** i) for i in range(12)],
                wacc=master_cfg.get("wacc_institucional", 0.1072)
            )

            kpi_dict = {
                "margen_bruto": 0.32,
                "margen_operativo": 0.18,
                "nopat": 185000.0,
                "roic": 0.22,
                "eva": 74500.0,
                "npv": dcf_sample["npv"],
                "irr": dcf_sample["irr"],
                "pi": dcf_sample["pi"]
            }

            path_gen = generate_enterprise_excel(
                filepath=tmp_excel.name,
                master_cfg=master_cfg,
                sat_liquidation=sat_sample,
                kpi_metrics=kpi_dict,
                inventory_items=get_all_productos(),
                recent_sales=get_all_ordenes_venta(),
                recent_purchases=get_all_ordenes_compra(),
                monthly_fcff=[22000.0 * (1.01 ** i) for i in range(12)],
                initial_investment_gtq=150000.0
            )

            with open(path_gen, "rb") as fh:
                st.download_button(
                    label="⬇ Descargar Reporte_Multiesencias_V4_Oficial.xlsx",
                    data=fh,
                    file_name="Reporte_Multiesencias_V4_Oficial.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )

        st.success("✓ Archivo Excel generado y listo para descarga.")


# ===========================================================================
# 11. CONFIGURACIÓN MAESTRA SAT & MACRO (SOLO ADMIN)
# ===========================================================================
elif nav_selected == "⚙️ Configuración Maestra SAT" and is_admin:
    st.markdown(hero_banner(
        "Configuración Institucional & Normativa SAT Guatemala",
        "Parámetros Globales (Admin)",
        "Edición de tasas tributarias SAT, tipo de cambio de referencia y costo de capital WACC.",
        "WACC = (E/V × Ke) + (D/V × Kd × (1 - ISR))"
    ), unsafe_allow_html=True)

    with st.form("form_master_cfg"):
        c1, c2, c3 = st.columns(3)
        tc_new = c1.number_input("Tipo de Cambio Oficial (GTQ/USD)", value=master_cfg["tipo_cambio_gtq_usd"], step=0.05)
        dai_new = c2.number_input("Tasa DAI por Defecto (%)", value=master_cfg["tasa_dai_defecto"] * 100, step=0.5) / 100.0
        iva_new = c3.number_input("Tasa IVA SAT (%)", value=master_cfg["tasa_iva_sat"] * 100, step=0.5) / 100.0

        c4, c5, c6 = st.columns(3)
        isr_new = c4.number_input("Tasa ISR SAT (%)", value=master_cfg["tasa_isr_sat"] * 100, step=0.5) / 100.0
        wacc_new = c5.number_input("WACC Institucional (%)", value=master_cfg["wacc_institucional"] * 100, step=0.25) / 100.0
        rf_new = c6.number_input("Tasa Libre de Riesgo Rf (%)", value=master_cfg["tasa_libre_riesgo"] * 100, step=0.25) / 100.0

        if st.form_submit_button("💾 Guardar Parámetros Globales", type="primary"):
            ok_up = update_master_config({
                "tipo_cambio_gtq_usd": tc_new,
                "tasa_dai_defecto": dai_new,
                "tasa_iva_sat": iva_new,
                "tasa_isr_sat": isr_new,
                "wacc_institucional": wacc_new,
                "tasa_libre_riesgo": rf_new
            })
            if ok_up:
                st.success("✓ Configuración actualizada en la nube.")
                st.rerun()


# ===========================================================================
# 12. GESTIÓN DE USUARIOS DEL SISTEMA (SOLO ADMIN)
# ===========================================================================
elif nav_selected == "👥 Gestión de Usuarios del Sistema" and is_admin:
    st.markdown(hero_banner(
        "Administración de Cuentas y Accesos Multi-Usuario",
        "Seguridad Enterprise",
        "Alta de nuevos usuarios con cifrado Bcrypt y asignación de roles (ADMIN / EJECUTIVO).",
        "Control de Acceso Basado en Roles (RBAC)"
    ), unsafe_allow_html=True)

    with st.expander("➕ Registrar Nuevo Usuario"):
        with st.form("form_add_user"):
            u1, u2 = st.columns(2)
            u_name = u1.text_input("Username (sin espacios)").strip().lower()
            u_full = u2.text_input("Nombre Completo y Cargo")
            u3, u4 = st.columns(2)
            u_pwd = u3.text_input("Contraseña Temporal", type="password")
            u_rol = u4.selectbox("Rol Asignado", ["EJECUTIVO", "ADMIN"])

            if st.form_submit_button("Crear Usuario", type="primary"):
                if u_name and u_pwd and u_full:
                    if create_user(u_name, u_pwd, u_full, u_rol):
                        st.success(f"✓ Usuario '{u_name}' creado con éxito.")
                        st.rerun()
                    else:
                        st.error("El nombre de usuario ya existe o hubo un error.")
                else:
                    st.warning("Complete todos los campos.")

    st.markdown(section_header("Usuarios Registrados en el Sistema", icon="👥"), unsafe_allow_html=True)
    all_u = get_all_users()
    if all_u:
        df_u = pd.DataFrame(all_u)
        st.dataframe(df_u, use_container_width=True)
