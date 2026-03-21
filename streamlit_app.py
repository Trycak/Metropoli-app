import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
import os

# 1. Configuración de la página
st.set_page_config(page_title="Metropoli Cafe", page_icon="🏀", layout="wide")

# 2. Conexión a Base de Datos (AJUSTADA PARA RAILWAY)
def conectar_db():
    # Esta es la ruta del Volumen que configuramos (/app/data)
    ruta_volumen = '/app/data/metropoli.db'
    
    # Verificamos si la carpeta del volumen existe (estamos en Railway)
    if os.path.exists('/app/data'):
        ruta = ruta_volumen
    else:
        # Si no existe, estamos en Replit o local, usamos la ruta de siempre
        ruta = 'metropoli.db'
        
    conn = sqlite3.connect(ruta, check_same_thread=False)
    return conn

conn = conectar_db()
c = conn.cursor()

# Asegurar que las tablas existan
c.execute('CREATE TABLE IF NOT EXISTS productos (id INTEGER PRIMARY KEY, nombre TEXT, precio REAL, stock INTEGER)')
c.execute('CREATE TABLE IF NOT EXISTS ventas (id INTEGER PRIMARY KEY, fecha TEXT, total REAL, metodo TEXT, detalle TEXT, cliente TEXT, reporte_id INTEGER)')
c.execute('CREATE TABLE IF NOT EXISTS históricos_reportes (id INTEGER PRIMARY KEY AUTOINCREMENT, fecha_cierre TEXT, total_caja REAL)')
conn.commit()

# --- ESTILOS VISUALES ---
st.markdown("""
    <style>
    .stApp { background-color: #134971 !important; }
    .stApp::before {
        content: "";
        background-image: url("https://github.com/Trycak/Metropoli-app/blob/main/Logo%20Metropoli%20opacidad.png?raw=true");
        background-repeat: no-repeat; background-attachment: fixed; background-position: center; background-size: 600px;
        position: fixed; top: 0; left: 0; width: 100%; height: 100%; z-index: -1;
    }
    [data-testid="stSidebar"] { background-image: url("https://github.com/Trycak/Metropoli-app/blob/main/Back%20large.png?raw=true"); background-size: cover; }
    [data-testid="stSidebar"] .stRadio div[role="radiogroup"] label {
        background-color: rgba(255, 255, 255, 0.1) !important;
        border-radius: 10px !important; padding: 10px 15px !important; margin-bottom: 6px !important; width: 100% !important;
    }
    [data-testid="stSidebar"] .stRadio div[role="radiogroup"] label p { color: white !important; font-weight: bold !important; font-size: 18px !important; }
    div.stButton > button[key^="p_"] { background-color: #28a5a9 !important; color: white !important; border-radius: 12px !important; height: 115px !important; width: 100% !important; font-size: 18px !important; }
    h1, h2, h3, p, span, label { color: white !important; text-align: center; }
    </style>
    """, unsafe_allow_html=True)

# --- FUNCIONES DE APOYO ---
def obtener_conteo_productos(df):
    conteo = {}
    for detalle in df['detalle']:
        partes = detalle.split(", ")
        for p in partes:
            if "(" in p and ")" in p:
                try:
                    nombre = p.split("(")[0]
                    cantidad = int(p.split("(")[1].replace(")", ""))
                    conteo[nombre] = conteo.get(nombre, 0) + cantidad
                except: continue
    if not conteo: return pd.DataFrame()
    return pd.DataFrame(list(conteo.items()), columns=['Producto', 'Cantidad']).sort_values(by='Cantidad', ascending=False)

def to_csv(df):
    return df.to_csv(index=False).encode('utf-8')

# --- MENÚ LATERAL (NUEVO ORDEN SOLICITADO) ---
st.sidebar.image("https://github.com/Trycak/Metropoli-app/blob/main/Logo%20Metropoli.png?raw=true", use_container_width=True)
menu = ["🛒 Ventas", "📦 Inventario", "📊 Productos Vendidos", "📝 Cuentas por Cobrar", "📋 Reportes"]
choice = st.sidebar.radio("", menu)

# --- SECCIONES ---

if choice == "🛒 Ventas":
    if 'carrito' not in st.session_state: st.session_state.carrito = {}
    col_prods, col_cart = st.columns([2, 1])
    with col_prods:
        st.subheader("🛒 Productos Disponibles")
        prods = pd.read_sql_query("SELECT * FROM productos ORDER BY nombre ASC", conn)
        grid = st.columns(3)
        for i, row in prods.iterrows():
            with grid[i % 3]:
                texto_btn = f"{row['nombre']} ({int(row['stock'])})\n₡{int(row['precio'])}"
                if st.button(texto_btn, key=f"p_{row['id']}", disabled=row['stock']<=0):
                    pid = str(row['id'])
                    if pid in st.session_state.carrito: st.session_state.carrito[pid]['cantidad'] += 1
                    else: st.session_state.carrito[pid] = {'nombre': row['nombre'], 'precio': row['precio'], 'cantidad': 1}
                    st.rerun()
    
    with col_cart:
        st.subheader("🛒 Carrito")
        if st.session_state.carrito:
            total_v = 0
            for pid, item in list(st.session_state.carrito.items()):
                sub = item['precio'] * item['cantidad']; total_v += sub
                c1, c2 = st.columns([5, 1])
                c1.write(f"**{item['nombre']} x{item['cantidad']}** (₡{int(sub)})")
                if c2.button("X", key=f"del_{pid}"): del st.session_state.carrito[pid]; st.rerun()
            st.divider()
            metodo = st.selectbox("Forma de Pago", ["Efectivo", "SINPE Móvil", "Crédito"])
            if st.button("✅ FINALIZAR VENTA", use_container_width=True):
                det = ", ".join([f"{v['nombre']}({v['cantidad']})" for v in st.session_state.carrito.values()])
                c.execute("INSERT INTO ventas (fecha, total, metodo, detalle) VALUES (?,?,?,?)", (datetime.now().strftime("%Y-%m-%d %H:%M"), total_v, metodo, det))
                for pid, item in st.session_state.carrito.items():
                    c.execute("UPDATE productos SET stock = stock - ? WHERE id = ?", (item['cantidad'], int(pid)))
                conn.commit(); st.session_state.carrito = {}; st.success("¡Venta Lista!"); st.rerun()
        else: st.info("Carrito vacío")

elif choice == "📦 Inventario":
    st.header("📦 Gestión de Inventario")
    df_inv = pd.read_sql_query("SELECT id, nombre, precio, stock FROM productos ORDER BY nombre ASC", conn)
    df_ed = st.data_editor(df_inv, column_config={"id": None}, hide_index=True, use_container_width=True)
    if st.button("💾 Guardar Cambios"):
        for _, row in df_ed.iterrows():
            c.execute("UPDATE productos SET nombre=?, precio=?, stock=? WHERE id=?", (row['nombre'], row['precio'], row['stock'], int(row['id'])))
        conn.commit(); st.success("Inventario actualizado"); st.rerun()
    
    with st.expander("➕ Agregar Nuevo Producto"):
        with st.form("nuevo"):
            n = st.text_input("Nombre")
            p = st.number_input("Precio", min_value=0)
            s = st.number_input("Stock Inicial", min_value=0)
            if st.form_submit_button("Añadir"):
                c.execute("INSERT INTO productos (nombre, precio, stock) VALUES (?,?,?)", (n, p, s))
                conn.commit(); st.rerun()

elif choice == "📊 Productos Vendidos":
    st.header("📊 Productos Vendidos")
    df_v = pd.read_sql_query("SELECT detalle FROM ventas WHERE reporte_id IS NULL", conn)
    if not df_v.empty:
        df_res = obtener_conteo_productos(df_v)
        st.dataframe(df_res, hide_index=True, use_container_width=True)
    else: st.info("No hay ventas en este periodo.")

elif choice == "📝 Cuentas por Cobrar":
    st.header("📝 Cuentas por Cobrar")
    st.info("Función en desarrollo para créditos de clientes.")

elif choice == "📋 Reportes":
    st.header("📋 Reportes de Ventas")
    df_p = pd.read_sql_query("SELECT id, fecha, total, metodo, detalle FROM ventas WHERE reporte_id IS NULL", conn)
    if not df_p.empty:
        st.dataframe(df_p, hide_index=True, use_container_width=True)
        if st.button("🔴 CERRAR CAJA"):
            total_caja = df_p['total'].sum()
            c.execute("INSERT INTO históricos_reportes (fecha_cierre, total_caja) VALUES (?,?)", (datetime.now().strftime("%Y-%m-%d %H:%M"), total_caja))
            c.execute("UPDATE ventas SET reporte_id = (SELECT max(id) FROM históricos_reportes) WHERE reporte_id IS NULL")
            conn.commit(); st.success(f"Caja cerrada con ₡{int(total_caja)}"); st.rerun()
    else: st.info("No hay ventas pendientes de cierre.")
