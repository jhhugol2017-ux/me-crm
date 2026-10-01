"""
database.py
===========
Arquitectura de Persistencia y Modelos Relacionales para
MULTIESENCIAS CORPORATE FINANCE & ERP SUITE V4.0.

Compatible con PostgreSQL en la nube (Supabase) y fallback transparente a SQLite.
Soporte para SQLAlchemy ORM, Bcrypt para contraseñas y transacciones ACID.
"""

from __future__ import annotations
import os
import datetime
from typing import Any, Optional, List, Dict
import bcrypt
from dotenv import load_dotenv

from sqlalchemy import (
    create_engine, Column, Integer, String, Float, Boolean, DateTime,
    ForeignKey, Text, select, update, delete, desc
)
from sqlalchemy.orm import declarative_base, sessionmaker, relationship, Session

# Cargar variables de entorno desde .env si existe
load_dotenv()

# Cadena de conexión con fallback transparente a SQLite
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///multiesencias.db")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

is_sqlite = DATABASE_URL.startswith("sqlite")
connect_args = {"check_same_thread": False} if is_sqlite else {}

engine = create_engine(
    DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
    connect_args=connect_args
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# ---------------------------------------------------------------------------
# UTILIDADES DE SEGURIDAD Y HASHING
# ---------------------------------------------------------------------------
def hash_password(plain_password: str) -> str:
    """Genera hash seguro de contraseña usando bcrypt."""
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(plain_password.encode("utf-8"), salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifica una contraseña contra su hash bcrypt."""
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except Exception:
        return False


# ---------------------------------------------------------------------------
# MODELOS RELACIONALES (SQLALCHEMY)
# ---------------------------------------------------------------------------

class Usuario(Base):
    """Tabla de usuarios del sistema con roles y autenticación."""
    __tablename__ = "usuarios"

    id_usuario = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    nombre_completo = Column(String(100), nullable=False)
    rol = Column(String(20), nullable=False, default="EJECUTIVO")  # 'ADMIN' | 'EJECUTIVO'
    activo = Column(Boolean, default=True, nullable=False)
    fecha_creacion = Column(DateTime, default=datetime.datetime.utcnow)

    ordenes_venta = relationship("OrdenVenta", back_populates="usuario")


class Proveedor(Base):
    """Catálogo de proveedores internacionales y locales."""
    __tablename__ = "proveedores"

    id_proveedor = Column(Integer, primary_key=True, autoincrement=True)
    codigo_proveedor = Column(String(50), unique=True, nullable=False, index=True)
    nombre_empresa = Column(String(150), nullable=False)
    pais_origen = Column(String(100), nullable=False)
    termino_pago_dias = Column(Integer, default=30, nullable=False)  # DPO por defecto
    moneda_origen = Column(String(10), default="USD", nullable=False)  # 'USD', 'EUR', 'BRL', 'CNY'

    rutas = relationship("RutaFlete", back_populates="proveedor", cascade="all, delete-orphan")
    productos = relationship("CatalogoProducto", back_populates="proveedor_default")
    ordenes_compra = relationship("OrdenCompra", back_populates="proveedor")


class RutaFlete(Base):
    """Rutas logísticas y tarifas de flete según modalidad."""
    __tablename__ = "rutas_fletes"

    id_ruta = Column(Integer, primary_key=True, autoincrement=True)
    id_proveedor = Column(Integer, ForeignKey("proveedores.id_proveedor", ondelete="SET NULL"), nullable=True)
    modalidad = Column(String(20), nullable=False)  # 'MARÍTIMO' | 'AÉREO'
    puerto_origen = Column(String(100), nullable=False)
    puerto_destino = Column(String(100), nullable=False)
    costo_flete_unitario_usd = Column(Float, default=0.0, nullable=False)
    tasa_seguro_pct = Column(Float, default=0.01, nullable=False)
    gastos_aduanales_locales_usd = Column(Float, default=0.0, nullable=False)
    tiempo_transito_dias = Column(Integer, default=15, nullable=False)

    proveedor = relationship("Proveedor", back_populates="rutas")


class CatalogoProducto(Base):
    """Catálogo de productos: reventa directa o formulación interna."""
    __tablename__ = "catalogo_productos"

    sku_codigo = Column(String(50), primary_key=True, index=True)
    nombre_producto = Column(String(150), nullable=False)
    tipo_producto = Column(String(30), nullable=False)  # 'DISTRIBUCION_DIRECTA' | 'FORMULACION_INTERNA'
    id_proveedor_default = Column(Integer, ForeignKey("proveedores.id_proveedor", ondelete="SET NULL"), nullable=True)
    costo_fob_moneda_origen = Column(Float, default=0.0, nullable=False)
    moneda_fob = Column(String(10), default="USD", nullable=False)
    tasa_dai_sat_pct = Column(Float, default=0.05, nullable=False)  # 0.00, 0.05, 0.10, 0.15
    unidad_medida = Column(String(20), default="KG", nullable=False)  # 'KG', 'L', 'UNIDAD'
    stock_actual = Column(Float, default=0.0, nullable=False)
    total_vendido_historico = Column(Float, default=0.0, nullable=False)

    proveedor_default = relationship("Proveedor", back_populates="productos")
    ordenes_compra = relationship("OrdenCompra", back_populates="producto")
    ordenes_venta = relationship("OrdenVenta", back_populates="producto")


class RecetaFormulacion(Base):
    """Lista de materiales (BOM) para formulaciones internas."""
    __tablename__ = "recetas_formulacion"

    id_receta = Column(Integer, primary_key=True, autoincrement=True)
    sku_producto_terminado = Column(String(50), ForeignKey("catalogo_productos.sku_codigo", ondelete="CASCADE"), nullable=False)
    sku_materia_prima = Column(String(50), ForeignKey("catalogo_productos.sku_codigo", ondelete="CASCADE"), nullable=False)
    proporcion_peso_pct = Column(Float, default=1.0, nullable=False)
    merma_tecnica_pct = Column(Float, default=0.03, nullable=False)
    costo_aditivos_empaque_gtq = Column(Float, default=0.0, nullable=False)


class Cliente(Base):
    """Catálogo comercial de clientes y condiciones de crédito."""
    __tablename__ = "clientes"

    id_cliente = Column(Integer, primary_key=True, autoincrement=True)
    codigo_cliente = Column(String(50), unique=True, nullable=False, index=True)
    razon_social = Column(String(150), nullable=False)
    nit = Column(String(50), nullable=True)
    dias_credito_pactados = Column(Integer, default=30, nullable=False)  # DSO por defecto
    limite_credito_gtq = Column(Float, default=100000.0, nullable=False)
    categoria_riesgo = Column(String(5), default="B", nullable=False)  # 'A', 'B', 'C'

    ordenes_venta = relationship("OrdenVenta", back_populates="cliente")


class OrdenCompra(Base):
    """Órdenes de compra internacionales o locales (Ingresos a bodega)."""
    __tablename__ = "ordenes_compra"

    id_orden_compra = Column(Integer, primary_key=True, autoincrement=True)
    numero_orden = Column(String(50), unique=True, nullable=False, index=True)
    id_proveedor = Column(Integer, ForeignKey("proveedores.id_proveedor"), nullable=False)
    sku_codigo = Column(String(50), ForeignKey("catalogo_productos.sku_codigo"), nullable=False)
    modalidad_flete = Column(String(20), default="MARÍTIMO", nullable=False)
    cantidad_comprada = Column(Float, nullable=False)
    costo_fob_total_usd = Column(Float, default=0.0, nullable=False)
    landed_cost_unitario_gtq = Column(Float, default=0.0, nullable=False)
    fecha_creacion = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    estado = Column(String(30), default="CONFIRMADA", nullable=False)  # 'CONFIRMADA' | 'EN_TRANSITO' | 'RECIBIDA_EN_BODEGA'

    proveedor = relationship("Proveedor", back_populates="ordenes_compra")
    producto = relationship("CatalogoProducto", back_populates="ordenes_compra")


class OrdenVenta(Base):
    """Órdenes de venta comerciales (Salidas de bodega)."""
    __tablename__ = "ordenes_venta"

    id_orden_venta = Column(Integer, primary_key=True, autoincrement=True)
    numero_orden = Column(String(50), unique=True, nullable=False, index=True)
    id_cliente = Column(Integer, ForeignKey("clientes.id_cliente"), nullable=False)
    sku_codigo = Column(String(50), ForeignKey("catalogo_productos.sku_codigo"), nullable=False)
    cantidad_vendida = Column(Float, nullable=False)
    precio_venta_unitario_gtq = Column(Float, nullable=False)
    monto_total_gtq = Column(Float, nullable=False)
    fecha_venta = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    creado_por_usuario = Column(Integer, ForeignKey("usuarios.id_usuario"), nullable=True)

    cliente = relationship("Cliente", back_populates="ordenes_venta")
    producto = relationship("CatalogoProducto", back_populates="ordenes_venta")
    usuario = relationship("Usuario", back_populates="ordenes_venta")


class ConfiguracionMaestra(Base):
    """Parámetros institucionales, macroeconómicos y normativa fiscal SAT."""
    __tablename__ = "configuracion_maestra"

    id = Column(Integer, primary_key=True)
    tipo_cambio_gtq_usd = Column(Float, default=7.75, nullable=False)
    tasa_dai_defecto = Column(Float, default=0.05, nullable=False)
    tasa_iva_sat = Column(Float, default=0.12, nullable=False)
    tasa_isr_sat = Column(Float, default=0.25, nullable=False)
    wacc_institucional = Column(Float, default=0.1072, nullable=False)
    tasa_libre_riesgo = Column(Float, default=0.0425, nullable=False)
    prima_riesgo_mercado = Column(Float, default=0.055, nullable=False)
    riesgo_pais_crp = Column(Float, default=0.0225, nullable=False)
    costo_deuda_kd = Column(Float, default=0.085, nullable=False)
    deuda_ratio_dv = Column(Float, default=0.35, nullable=False)
    equity_ratio_ev = Column(Float, default=0.65, nullable=False)
    beta_desapalancada = Column(Float, default=0.85, nullable=False)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)


# ---------------------------------------------------------------------------
# INICIALIZACIÓN Y DATA SEEDING
# ---------------------------------------------------------------------------

def init_db() -> None:
    """Crea todas las tablas e inicializa datos semilla si la base está vacía."""
    Base.metadata.create_all(bind=engine)
    seed_database()


def seed_database() -> None:
    """Inserta registros institucionales por defecto si no existen usuarios."""
    db: Session = SessionLocal()
    try:
        user_count = db.query(Usuario).count()
        if user_count == 0:
            # 1. Usuarios Oficiales
            admin_user = Usuario(
                username="admin",
                password_hash=hash_password("Multiesencias2026!"),
                nombre_completo="Dirección General & Finanzas",
                rol="ADMIN",
                activo=True
            )
            ventas_user = Usuario(
                username="ventas",
                password_hash=hash_password("Ventas2026!"),
                nombre_completo="Ejecutivo Comercial Senior",
                rol="EJECUTIVO",
                activo=True
            )
            db.add_all([admin_user, ventas_user])

            # 2. Configuración Maestra
            config = ConfiguracionMaestra(
                id=1,
                tipo_cambio_gtq_usd=7.75,
                tasa_dai_defecto=0.05,
                tasa_iva_sat=0.12,
                tasa_isr_sat=0.25,
                wacc_institucional=0.1072,
                tasa_libre_riesgo=0.0425,
                prima_riesgo_mercado=0.055,
                riesgo_pais_crp=0.0225,
                costo_deuda_kd=0.085,
                deuda_ratio_dv=0.35,
                equity_ratio_ev=0.65,
                beta_desapalancada=0.85
            )
            db.add(config)
            db.flush()

            db.commit()
            print("[database] Seed institucional V4 completado exitosamente (solo usuarios y config).")
    except Exception as e:
        db.rollback()
        print(f"[database] Error en seeding: {e}")
    finally:
        db.close()


def reset_database() -> None:
    """Borra todas las tablas y vuelve a ejecutar el seed limpio."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    seed_database()


# ---------------------------------------------------------------------------
# FUNCIONES CRUD OPERATIVAS
# ---------------------------------------------------------------------------

# === USUARIOS & AUTENTICACIÓN ===
def authenticate_user(username: str, password_plain: str) -> Optional[Dict[str, Any]]:
    """Valida credenciales contra la BD. Retorna dict con datos o None."""
    db: Session = SessionLocal()
    try:
        user = db.query(Usuario).filter(Usuario.username == username, Usuario.activo == True).first()
        if user and verify_password(password_plain, user.password_hash):
            return {
                "id_usuario": user.id_usuario,
                "username": user.username,
                "nombre_completo": user.nombre_completo,
                "rol": user.rol,
                "activo": user.activo
            }
        return None
    finally:
        db.close()


def create_user(username: str, password_plain: str, nombre_completo: str, rol: str = "EJECUTIVO") -> bool:
    db: Session = SessionLocal()
    try:
        exist = db.query(Usuario).filter(Usuario.username == username).first()
        if exist:
            return False
        nuevo = Usuario(
            username=username.strip().lower(),
            password_hash=hash_password(password_plain),
            nombre_completo=nombre_completo.strip(),
            rol=rol.upper(),
            activo=True
        )
        db.add(nuevo)
        db.commit()
        return True
    except Exception:
        db.rollback()
        return False
    finally:
        db.close()


def get_all_users() -> List[Dict[str, Any]]:
    db: Session = SessionLocal()
    try:
        users = db.query(Usuario).order_by(Usuario.id_usuario).all()
        return [
            {
                "id_usuario": u.id_usuario,
                "username": u.username,
                "nombre_completo": u.nombre_completo,
                "rol": u.rol,
                "activo": u.activo,
                "fecha_creacion": u.fecha_creacion.strftime("%Y-%m-%d %H:%M") if u.fecha_creacion else ""
            }
            for u in users
        ]
    finally:
        db.close()


def toggle_user_active(id_usuario: int) -> bool:
    db: Session = SessionLocal()
    try:
        u = db.query(Usuario).filter(Usuario.id_usuario == id_usuario).first()
        if u:
            u.activo = not u.activo
            db.commit()
            return True
        return False
    except Exception:
        db.rollback()
        return False
    finally:
        db.close()


# === PROVEEDORES ===
def get_all_proveedores() -> List[Dict[str, Any]]:
    db: Session = SessionLocal()
    try:
        items = db.query(Proveedor).order_by(Proveedor.nombre_empresa).all()
        return [
            {
                "id_proveedor": p.id_proveedor,
                "codigo_proveedor": p.codigo_proveedor,
                "nombre_empresa": p.nombre_empresa,
                "pais_origen": p.pais_origen,
                "termino_pago_dias": p.termino_pago_dias,
                "moneda_origen": p.moneda_origen
            }
            for p in items
        ]
    finally:
        db.close()


def create_proveedor(codigo: str, nombre: str, pais: str, dias_pago: int, moneda: str = "USD") -> bool:
    db: Session = SessionLocal()
    try:
        nuevo = Proveedor(
            codigo_proveedor=codigo.strip().upper(),
            nombre_empresa=nombre.strip(),
            pais_origen=pais.strip(),
            termino_pago_dias=int(dias_pago),
            moneda_origen=moneda.strip().upper()
        )
        db.add(nuevo)
        db.commit()
        return True
    except Exception:
        db.rollback()
        return False
    finally:
        db.close()


# === RUTAS DE FLETE ===
def get_all_rutas() -> List[Dict[str, Any]]:
    db: Session = SessionLocal()
    try:
        items = db.query(RutaFlete).order_by(RutaFlete.puerto_origen).all()
        result = []
        for r in items:
            prov_nombre = r.proveedor.nombre_empresa if r.proveedor else "Sin Proveedor"
            result.append({
                "id_ruta": r.id_ruta,
                "id_proveedor": r.id_proveedor,
                "proveedor_nombre": prov_nombre,
                "modalidad": r.modalidad,
                "puerto_origen": r.puerto_origen,
                "puerto_destino": r.puerto_destino,
                "costo_flete_unitario_usd": r.costo_flete_unitario_usd,
                "tasa_seguro_pct": r.tasa_seguro_pct,
                "gastos_aduanales_locales_usd": r.gastos_aduanales_locales_usd,
                "tiempo_transito_dias": r.tiempo_transito_dias
            })
        return result
    finally:
        db.close()


def create_ruta(id_proveedor: int, modalidad: str, origen: str, destino: str,
                flete_usd: float, seguro_pct: float, aduana_usd: float, transito_dias: int) -> bool:
    db: Session = SessionLocal()
    try:
        nueva = RutaFlete(
            id_proveedor=id_proveedor if id_proveedor > 0 else None,
            modalidad=modalidad.upper(),
            puerto_origen=origen.strip(),
            puerto_destino=destino.strip(),
            costo_flete_unitario_usd=float(flete_usd),
            tasa_seguro_pct=float(seguro_pct),
            gastos_aduanales_locales_usd=float(aduana_usd),
            tiempo_transito_dias=int(transito_dias)
        )
        db.add(nueva)
        db.commit()
        return True
    except Exception:
        db.rollback()
        return False
    finally:
        db.close()


# === CATÁLOGO DE PRODUCTOS ===
def get_all_productos() -> List[Dict[str, Any]]:
    db: Session = SessionLocal()
    try:
        items = db.query(CatalogoProducto).order_by(CatalogoProducto.sku_codigo).all()
        result = []
        for p in items:
            prov_nombre = p.proveedor_default.nombre_empresa if p.proveedor_default else "N/A"
            result.append({
                "sku_codigo": p.sku_codigo,
                "nombre_producto": p.nombre_producto,
                "tipo_producto": p.tipo_producto,
                "id_proveedor_default": p.id_proveedor_default,
                "proveedor_nombre": prov_nombre,
                "costo_fob_moneda_origen": p.costo_fob_moneda_origen,
                "moneda_fob": p.moneda_fob,
                "tasa_dai_sat_pct": p.tasa_dai_sat_pct,
                "unidad_medida": p.unidad_medida,
                "stock_actual": p.stock_actual,
                "total_vendido_historico": p.total_vendido_historico
            })
        return result
    finally:
        db.close()


def get_producto_by_sku(sku: str) -> Optional[Dict[str, Any]]:
    db: Session = SessionLocal()
    try:
        p = db.query(CatalogoProducto).filter(CatalogoProducto.sku_codigo == sku).first()
        if not p:
            return None
        prov_nombre = p.proveedor_default.nombre_empresa if p.proveedor_default else "N/A"
        return {
            "sku_codigo": p.sku_codigo,
            "nombre_producto": p.nombre_producto,
            "tipo_producto": p.tipo_producto,
            "id_proveedor_default": p.id_proveedor_default,
            "proveedor_nombre": prov_nombre,
            "costo_fob_moneda_origen": p.costo_fob_moneda_origen,
            "moneda_fob": p.moneda_fob,
            "tasa_dai_sat_pct": p.tasa_dai_sat_pct,
            "unidad_medida": p.unidad_medida,
            "stock_actual": p.stock_actual,
            "total_vendido_historico": p.total_vendido_historico
        }
    finally:
        db.close()


def create_producto(sku: str, nombre: str, tipo: str, id_proveedor: int,
                    costo_fob: float, dai_pct: float, unidad: str = "KG", stock_ini: float = 0.0) -> bool:
    db: Session = SessionLocal()
    try:
        nuevo = CatalogoProducto(
            sku_codigo=sku.strip().upper(),
            nombre_producto=nombre.strip(),
            tipo_producto=tipo.strip().upper(),
            id_proveedor_default=id_proveedor if id_proveedor > 0 else None,
            costo_fob_moneda_origen=float(costo_fob),
            moneda_fob="USD",
            tasa_dai_sat_pct=float(dai_pct),
            unidad_medida=unidad.strip().upper(),
            stock_actual=float(stock_ini),
            total_vendido_historico=0.0
        )
        db.add(nuevo)
        db.commit()
        return True
    except Exception:
        db.rollback()
        return False
    finally:
        db.close()


# === RECETAS DE FORMULACIÓN ===
def get_recetas_by_producto(sku_terminado: str) -> List[Dict[str, Any]]:
    db: Session = SessionLocal()
    try:
        items = db.query(RecetaFormulacion).filter(
            RecetaFormulacion.sku_producto_terminado == sku_terminado
        ).all()
        return [
            {
                "id_receta": r.id_receta,
                "sku_producto_terminado": r.sku_producto_terminado,
                "sku_materia_prima": r.sku_materia_prima,
                "proporcion_peso_pct": r.proporcion_peso_pct,
                "merma_tecnica_pct": r.merma_tecnica_pct,
                "costo_aditivos_empaque_gtq": r.costo_aditivos_empaque_gtq
            }
            for r in items
        ]
    finally:
        db.close()


def create_receta(sku_terminado: str, sku_mp: str, proporcion: float, merma: float, aditivos: float) -> bool:
    db: Session = SessionLocal()
    try:
        nueva = RecetaFormulacion(
            sku_producto_terminado=sku_terminado.strip().upper(),
            sku_materia_prima=sku_mp.strip().upper(),
            proporcion_peso_pct=float(proporcion),
            merma_tecnica_pct=float(merma),
            costo_aditivos_empaque_gtq=float(aditivos)
        )
        db.add(nueva)
        db.commit()
        return True
    except Exception:
        db.rollback()
        return False
    finally:
        db.close()


# === CLIENTES ===
def get_all_clientes() -> List[Dict[str, Any]]:
    db: Session = SessionLocal()
    try:
        items = db.query(Cliente).order_by(Cliente.razon_social).all()
        return [
            {
                "id_cliente": c.id_cliente,
                "codigo_cliente": c.codigo_cliente,
                "razon_social": c.razon_social,
                "nit": c.nit,
                "dias_credito_pactados": c.dias_credito_pactados,
                "limite_credito_gtq": c.limite_credito_gtq,
                "categoria_riesgo": c.categoria_riesgo
            }
            for c in items
        ]
    finally:
        db.close()


def create_cliente(codigo: str, razon: str, nit: str, dias_credito: int, limite_gtq: float, riesgo: str = "B") -> bool:
    db: Session = SessionLocal()
    try:
        nuevo = Cliente(
            codigo_cliente=codigo.strip().upper(),
            razon_social=razon.strip(),
            nit=nit.strip(),
            dias_credito_pactados=int(dias_credito),
            limite_credito_gtq=float(limite_gtq),
            categoria_riesgo=riesgo.strip().upper()
        )
        db.add(nuevo)
        db.commit()
        return True
    except Exception:
        db.rollback()
        return False
    finally:
        db.close()


# === ÓRDENES DE COMPRA (ABASTECIMIENTO) ===
def create_orden_compra(numero_orden: str, id_proveedor: int, sku: str, modalidad: str,
                        cantidad: float, costo_fob_total: float, landed_unitario: float,
                        auto_recibir: bool = False) -> bool:
    """Crea una orden de compra. Si auto_recibir es True, incrementa el stock inmediatamente."""
    db: Session = SessionLocal()
    try:
        estado = "RECIBIDA_EN_BODEGA" if auto_recibir else "CONFIRMADA"
        orden = OrdenCompra(
            numero_orden=numero_orden.strip().upper(),
            id_proveedor=id_proveedor,
            sku_codigo=sku.strip().upper(),
            modalidad_flete=modalidad.strip().upper(),
            cantidad_comprada=float(cantidad),
            costo_fob_total_usd=float(costo_fob_total),
            landed_cost_unitario_gtq=float(landed_unitario),
            estado=estado
        )
        db.add(orden)

        if auto_recibir:
            prod = db.query(CatalogoProducto).filter(CatalogoProducto.sku_codigo == sku).first()
            if prod:
                prod.stock_actual += float(cantidad)

        db.commit()
        return True
    except Exception:
        db.rollback()
        return False
    finally:
        db.close()


def recibir_orden_compra(id_orden: int) -> bool:
    """Marca la orden como recibida e incrementa automáticamente el stock del SKU."""
    db: Session = SessionLocal()
    try:
        orden = db.query(OrdenCompra).filter(OrdenCompra.id_orden_compra == id_orden).first()
        if orden and orden.estado != "RECIBIDA_EN_BODEGA":
            orden.estado = "RECIBIDA_EN_BODEGA"
            prod = db.query(CatalogoProducto).filter(CatalogoProducto.sku_codigo == orden.sku_codigo).first()
            if prod:
                prod.stock_actual += float(orden.cantidad_comprada)
            db.commit()
            return True
        return False
    except Exception:
        db.rollback()
        return False
    finally:
        db.close()


def get_all_ordenes_compra() -> List[Dict[str, Any]]:
    db: Session = SessionLocal()
    try:
        items = db.query(OrdenCompra).order_by(desc(OrdenCompra.fecha_creacion)).all()
        return [
            {
                "id_orden_compra": o.id_orden_compra,
                "numero_orden": o.numero_orden,
                "proveedor": o.proveedor.nombre_empresa if o.proveedor else "N/A",
                "sku_codigo": o.sku_codigo,
                "producto": o.producto.nombre_producto if o.producto else "N/A",
                "modalidad": o.modalidad_flete,
                "cantidad": o.cantidad_comprada,
                "fob_total_usd": o.costo_fob_total_usd,
                "landed_unitario_gtq": o.landed_cost_unitario_gtq,
                "fecha": o.fecha_creacion.strftime("%Y-%m-%d %H:%M") if o.fecha_creacion else "",
                "estado": o.estado
            }
            for o in items
        ]
    finally:
        db.close()


# === ÓRDENES DE VENTA (SALIDAS COMERCIALES) ===
def create_orden_venta(numero_orden: str, id_cliente: int, sku: str,
                       cantidad: float, precio_unitario: float, id_usuario: Optional[int] = None) -> Dict[str, Any]:
    """
    Registra orden de venta comercial.
    Comportamiento:
    - Deduce de stock_actual
    - Incrementa total_vendido_historico
    - Retorna dict con status y mensaje (incluyendo si falta stock)
    """
    db: Session = SessionLocal()
    try:
        prod = db.query(CatalogoProducto).filter(CatalogoProducto.sku_codigo == sku).first()
        if not prod:
            return {"success": False, "msg": f"El SKU {sku} no existe."}

        cantidad_f = float(cantidad)
        if prod.stock_actual < cantidad_f:
            return {
                "success": False,
                "msg": f"Stock insuficiente para {sku}. Disponible: {prod.stock_actual:,.1f} {prod.unidad_medida}, Solicitado: {cantidad_f:,.1f}."
            }

        monto_total = cantidad_f * float(precio_unitario)
        orden = OrdenVenta(
            numero_orden=numero_orden.strip().upper(),
            id_cliente=id_cliente,
            sku_codigo=sku.strip().upper(),
            cantidad_vendida=cantidad_f,
            precio_venta_unitario_gtq=float(precio_unitario),
            monto_total_gtq=monto_total,
            creado_por_usuario=id_usuario
        )
        db.add(orden)

        # Actualización automática de inventario y acumuladores
        prod.stock_actual -= cantidad_f
        prod.total_vendido_historico += cantidad_f

        db.commit()
        return {
            "success": True,
            "msg": f"Venta registrada. Stock restante: {prod.stock_actual:,.1f} {prod.unidad_medida}.",
            "nuevo_stock": prod.stock_actual,
            "total_vendido": prod.total_vendido_historico
        }
    except Exception as e:
        db.rollback()
        return {"success": False, "msg": f"Error al procesar venta: {str(e)}"}
    finally:
        db.close()


def get_all_ordenes_venta() -> List[Dict[str, Any]]:
    db: Session = SessionLocal()
    try:
        items = db.query(OrdenVenta).order_by(desc(OrdenVenta.fecha_venta)).all()
        return [
            {
                "id_orden_venta": o.id_orden_venta,
                "numero_orden": o.numero_orden,
                "cliente": o.cliente.razon_social if o.cliente else "N/A",
                "sku_codigo": o.sku_codigo,
                "producto": o.producto.nombre_producto if o.producto else "N/A",
                "cantidad": o.cantidad_vendida,
                "precio_unitario_gtq": o.precio_venta_unitario_gtq,
                "monto_total_gtq": o.monto_total_gtq,
                "fecha": o.fecha_venta.strftime("%Y-%m-%d %H:%M") if o.fecha_venta else "",
                "usuario": o.usuario.nombre_completo if o.usuario else "Sistema"
            }
            for o in items
        ]
    finally:
        db.close()


# === CONFIGURACIÓN MAESTRA ===
def get_master_config() -> Dict[str, Any]:
    db: Session = SessionLocal()
    try:
        cfg = db.query(ConfiguracionMaestra).filter(ConfiguracionMaestra.id == 1).first()
        if not cfg:
            init_db()
            cfg = db.query(ConfiguracionMaestra).filter(ConfiguracionMaestra.id == 1).first()
        return {
            "tipo_cambio_gtq_usd": cfg.tipo_cambio_gtq_usd,
            "tasa_dai_defecto": cfg.tasa_dai_defecto,
            "tasa_iva_sat": cfg.tasa_iva_sat,
            "tasa_isr_sat": cfg.tasa_isr_sat,
            "wacc_institucional": cfg.wacc_institucional,
            "tasa_libre_riesgo": cfg.tasa_libre_riesgo,
            "prima_riesgo_mercado": cfg.prima_riesgo_mercado,
            "riesgo_pais_crp": cfg.riesgo_pais_crp,
            "costo_deuda_kd": cfg.costo_deuda_kd,
            "deuda_ratio_dv": cfg.deuda_ratio_dv,
            "equity_ratio_ev": cfg.equity_ratio_ev,
            "beta_desapalancada": cfg.beta_desapalancada,
        }
    finally:
        db.close()


def update_master_config(data: Dict[str, float]) -> bool:
    db: Session = SessionLocal()
    try:
        cfg = db.query(ConfiguracionMaestra).filter(ConfiguracionMaestra.id == 1).first()
        if not cfg:
            cfg = ConfiguracionMaestra(id=1)
            db.add(cfg)
        for k, v in data.items():
            if hasattr(cfg, k):
                setattr(cfg, k, float(v))
        db.commit()
        return True
    except Exception:
        db.rollback()
        return False
    finally:
        db.close()


# Inicializar automáticamente al importar
init_db()
