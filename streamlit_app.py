import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
import io

# 1. CONFIGURACIÓN DE PÁGINA Y ESTILO "HAIL MARY"
st.set_page_config(page_title="Metropoli Basket Academy", page_icon="🏀", layout="wide")

ACCENT_COLOR = '#279aa0'

st.markdown(f"""
    <style>
    /* Fondo general */
    .stApp {{ background-color: #f8fafc; }}
    
    /* Sidebar Estilo MBA */
    [data-testid="stSidebar"] {{
        background-color: {ACCENT_COLOR};
    }}
    [data-testid="stSidebar"] * {{ color: white !important; }}
    
    /* Tarjetas de Producto */
    .product-card {{
        background-color: white;
        padding: 20px;
        border-radius: 15px;
        border-left: 5px solid {ACCENT_COLOR};
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        margin-bottom: 10px;
        transition: transform 0.2s;
    }}
    .product-card:hover {{ transform: translateY(-3px); }}
    
    .price-badge {{
        color: {ACCENT_COLOR};
        font-weight: bold;
        font-size: 1.2rem;
    }}

    /* Botones */
    .stButton>button {{
        width: 100%;
        border-radius: 10px;
        background-color: {ACCENT_COLOR};
        color: white;
        font-weight: bold;
        border: none;
        height: 3em;
    }}
    .stButton>button:hover {{
        background-color: #1a7478;
        color: white;
    }}
    
    /* Inputs y Selects */
    .stSelectbox, .stTextInput {{ border-radius: 10px; }}
    </style>
    """, unsafe_allow_html=True)

# 2. CONEXIÓN A BASE DE DATOS (Mantenida)
def conectar_db():
    conn = sqlite3.connect('metropoli.db', check_same_thread=False)
    return conn

conn = conectar_db()
c = conn.cursor()
c.execute('CREATE TABLE IF NOT EXISTS productos (id INTEGER PRIMARY KEY, nombre TEXT, precio REAL, stock INTEGER)')
try:
    c.execute('ALTER TABLE ventas ADD COLUMN reporte_id INTEGER')
except:
    pass
c.execute('CREATE TABLE IF NOT EXISTS ventas (id INTEGER PRIMARY KEY, fecha TEXT, total REAL, metodo TEXT, detalle TEXT, cliente TEXT, reporte_id INTEGER)')
c.execute('CREATE TABLE IF NOT EXISTS históricos_reportes (id INTEGER PRIMARY KEY AUTOINCREMENT, fecha_cierre TEXT, total_caja REAL)')
conn.commit()

# Lógica de conteo para reportes
def contar_articulos(dataframe):
    conteo = {}
    for d in dataframe['detalle']:
        partes = d.split(", ")
        for p in partes:
            if "(" in p and ")" in p:
                try:
                    nombre_item = p.split("(")[0]
                    cant_item = int(p.split("(")[1].replace(")", ""))
                    conteo[nombre_item] = conteo.get(nombre_item, 0) + cant_item
                except: continue
    return conteo

# 3. MENÚ LATERAL ESTILIZADO
with st.sidebar:
    st.markdown("## 🏀 MBA POS")
    st.write("---")
    menu = st.radio("Navegación", ["🛒 Ventas", "📦 Inventario", "📝 Cuentas por Cobrar", "📊 Reporte"])
    st.write("---")
    st.caption("Metropoli Basket Academy v1.1")

# --- SECCIÓN VENTAS ---
if menu == "🛒 Ventas":
    if 'carrito' not in st.session_state: st.session_state.carrito = {}
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown(f"<h2 style='color:{ACCENT_COLOR};'>Punto de Venta</h2>", unsafe_allow_html=True)
        busqueda = st.text_input("🔍 Buscar producto...", placeholder="Escribe para filtrar...")
        
        prods = pd.read_sql_query(f"SELECT * FROM productos WHERE stock > 0 AND nombre LIKE '%{busqueda}%' ORDER BY nombre ASC", conn)
        
        if prods.empty: 
            st.warning("No se encontraron productos.")
        else:
            columnas = st.columns(2)
            for i, row in prods.iterrows():
                with columnas[i % 2]:
                    st.markdown(f"""
                        <div class="product-card">
                            <div style="display: flex; justify-content: space-between; align-items: center;">
                                <div>
                                    <h4 style="margin:0;">{row['nombre']}</h4>
                                    <small style="color:gray;">Disponible: {row['stock']}</small>
                                </div>
                                <div class="price-badge">₡{int(row['precio']):,}</div>
                            </div>
                        </div>
                    """, unsafe_allow_html=True)
                    if st.button(f"Agregar {row['nombre']}", key=f"btn_{row['id']}"):
                        pid = str(row['id'])
                        if pid in st.session_state.carrito: st.session_state.carrito[pid]['cantidad'] += 1
                        else: st.session_state.carrito[pid] = {'nombre': row['nombre'], 'precio': row['precio'], 'cantidad': 1}
                        st.toast(f"✅ {row['nombre']} añadido")
                        st.rerun()

    with col2:
        st.markdown(f"<div style='background-color:white; padding:20px; border-radius:15px; border: 1px solid {ACCENT_COLOR};'>", unsafe_allow_html=True)
        st.subheader("🛒 Resumen de Venta")
        
        if st.session_state.carrito:
            total = 0
            for pid, item in list(st.session_state.carrito.items()):
                subtotal = item['precio'] * item['cantidad']
                total += subtotal
                c1, c2 = st.columns([3, 1])
                c1.write(f"**{item['nombre']}** (x{item['cantidad']})")
                c2.write(f"₡{int(subtotal):,}")
            
            st.divider()
            st.markdown(f"<h2 style='text-align:right;'>Total: ₡{int(total):,}</h2>", unsafe_allow_html=True)
            
            metodo = st.selectbox("Método de Pago", ["Efectivo", "SINPE Móvil", "Crédito"])
            cliente = ""
            if metodo == "Crédito":
                clientes_previos = pd.read_sql_query("SELECT DISTINCT cliente FROM ventas WHERE metodo = 'Crédito'", conn)['cliente'].tolist()
                cliente = st.selectbox("Cliente:", ["-- Nuevo --"] + clientes_previos)
                if cliente == "-- Nuevo --": cliente = st.text_input("Nombre del Cliente")
            
            if st.button("✅ FINALIZAR Y PAGAR", type="primary"):
                if metodo == "Crédito" and not cliente: st.error("Falta el nombre del cliente.")
                else:
                    fecha = datetime.now().strftime("%Y-%m-%d %H:%M")
                    detalle = ", ".join([f"{i['nombre']}({i['cantidad']})" for i in st.session_state.carrito.values()])
                    c.execute("INSERT INTO ventas (fecha, total, metodo, detalle, cliente, reporte_id) VALUES (?,?,?,?,?, NULL)", 
                              (fecha, total, metodo, detalle, cliente if cliente else ""))
                    for pid, item in st.session_state.carrito.items():
                        c.execute("UPDATE productos SET stock = stock - ? WHERE id = ?", (item['
