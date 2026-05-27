import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
import io
import os

# 1. Configuración de la página
st.set_page_config(page_title="Metropoli Cafe", page_icon="🏀", layout="wide")

# 2. Conexión a Base de Datos
def conectar_db():
    ruta_volumen = '/app/data/metropoli.db'
    if os.path.exists('/app/data'):
        ruta = ruta_volumen
    else:
        ruta = 'metropoli.db'
    conn = sqlite3.connect(ruta, check_same_thread=False)
    return conn

conn = conectar_db()
c = conn.cursor()

# Asegurar tablas
c.execute('CREATE TABLE IF NOT EXISTS productos (id INTEGER PRIMARY KEY, nombre TEXT, precio REAL, stock INTEGER)')
c.execute('CREATE TABLE IF NOT EXISTS ventas (id INTEGER PRIMARY KEY, fecha TEXT, total REAL, metodo TEXT, detalle TEXT, cliente TEXT, reporte_id INTEGER)')
c.execute('CREATE TABLE IF NOT EXISTS históricos_reportes (id INTEGER PRIMARY KEY AUTOINCREMENT, fecha_cierre TEXT, total_caja REAL)')
conn.commit()

# --- ESTILOS VISUALES ORIGINALES ---
st.markdown("""
    <style>
    .stApp { background-color: #134971 !important; }
    [data-testid="stSidebar"] { background-image: url("https://github.com/Trycak/Metropoli-app/blob/main/Back%20large.png?raw=true"); background-size: cover; }
    h1, h2, h3, p, span, label, .stMarkdown { color: white !important; text-align: center; }
    
    div.stButton > button {
        -webkit-appearance: none !important;
        appearance: none !important;
        background-color: #ff6b1d !important; 
        color: #000000 !important;           
        border: 2px solid #d15615 !important; 
        border-radius: 12px !important;
        font-weight: bold !important;
        font-size: 18px !important;
        height: 115px !important; 
        width: 100% !important; 
        margin-bottom: 10px !important;
        display: block !important;
        white-space: pre-line !important;
    }

    div.stButton > button:disabled {
        background-color: #000000 !important;
        color: #444444 !important;
        border: 2px solid #333333 !important;
        opacity: 1 !important;
    }
    
    .total-carrito {
        background-color: rgba(255, 107, 29, 0.15);
        padding: 20px;
        border-radius: 15px;
        border: 2px solid #ff6b1d;
        margin: 15px 0px;
        text-align: center;
    }
    .info-caja {
        background-color: rgba(255, 255, 255, 0.1);
        padding: 15px;
        border-radius: 10px;
        border: 1px solid #ff6b1d;
        margin-bottom: 20px;
    }
    </style>
    """, unsafe_allow_html=True)

def obtener_conteo_productos(df):
    conteo = {}
    for detalle in df['detalle']:
        partes = str(detalle).split(", ")
        for p in partes:
            if "(" in p and ")" in p:
                try:
                    nombre = p.split("(")[0].strip()
                    cantidad = int(p.split("(")[1].replace(")", ""))
                    conteo[nombre] = conteo.get(nombre, 0) + cantidad
                except: continue
    if not conteo: return pd.DataFrame()
    return pd.DataFrame(list(conteo.items()), columns=['Producto', 'Cant.']).sort_values(by='Cant.', ascending=False)

def unificar_detalles_texto(lista_detalles):
    """Consolida múltiples strings de detalle en uno solo limpio y acumulado"""
    conteo = {}
    for detalle in lista_detalles:
        partes = str(detalle).split(", ")
        for p in partes:
            if "(" in p and ")" in p:
                try:
                    nombre = p.split("(")[0].strip()
                    cantidad = int(p.split("(")[1].replace(")", ""))
                    conteo[nombre] = conteo.get(nombre, 0) + cantidad
                except: continue
    return ", ".join([f"{prod}({cant})" for prod, cant in conteo.items()])

# --- MENÚ LATERAL ---
st.sidebar.image("https://github.com/Trycak/Metropoli-app/blob/main/Logo%20Metropoli.png?raw=true", use_container_width=True)
menu = ["🛒 Ventas", "📦 Inventario", "📊 Productos Vendidos", "📝 Cuentas por Cobrar", "📋 Reportes"]
choice = st.sidebar.radio("Nav", menu, label_visibility="collapsed")

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
                label_stock = f"({int(row['stock'])})" if row['stock'] > 0 else "(AGOTADO)"
                
                # ÚNICO CAMBIO REAL: El texto ahora se divide en 3 líneas exactas con (\n)
                texto_final = f"{row['nombre']}\n{label_stock}\n₡{int(row['precio'])}"
                
                if st.button(texto_final, key=f"p_{row['id']}", disabled=row['stock'] <= 0):
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
            st.markdown(f"""<div class="total-carrito"><p style="margin:0; font-size:16px; color:#ff6b1d;">MONTO A PAGAR</p><h1 style="margin:0; font-size:45px; color:white;">₡{int(total_v)}</h1></div>""", unsafe_allow_html=True)
            st.divider()
            metodo = st.selectbox("Forma de Pago", ["Efectivo", "SINPE Móvil", "Crédito"])
            cliente_n = ""
            if metodo == "Crédito":
                clientes_db = pd.read_sql_query("SELECT DISTINCT cliente FROM ventas WHERE metodo = 'Crédito' AND reporte_id = -1 AND cliente != ''", conn)['cliente'].tolist()
                opc = st.selectbox("Seleccionar Cliente", ["-- Nuevo --"] + clientes_db)
                cliente_n = st.text_input("Nombre del Cliente") if opc == "-- Nuevo --" else opc
            if st.button("✅ FINALIZAR VENTA", use_container_width=True):
                if metodo == "Crédito" and not cliente_n: st.error("Falta nombre")
                else:
                    det = ", ".join([f"{v['nombre']}({v['cantidad']})" for v in st.session_state.carrito.values()])
                    rep_id_inicial = -1 if metodo == "Crédito" else None
                    c.execute("INSERT INTO ventas (fecha, total, metodo, detalle, cliente, reporte_id) VALUES (?,?,?,?,?,?)", (datetime.now().strftime("%Y-%m-%d %H:%M"), total_v, metodo, det, cliente_n, rep_id_inicial))
                    for pid, item in st.session_state.carrito.items():
                        c.execute("UPDATE productos SET stock = stock - ? WHERE id = ?", (item['cantidad'], int(pid)))
                    conn.commit(); st.session_state.carrito = {}; st.success("¡Venta Lista!"); st.rerun()
        else: st.info("El carrito está vacío")

elif choice == "📦 Inventario":
    st.header("📦 Gestión de Inventario")
    df_inv = pd.read_sql_query("SELECT id, nombre, precio, stock FROM productos ORDER BY nombre ASC", conn)
    df_inv['Eliminar'] = False
    _, mid, _ = st.columns([1, 6, 1])
    with mid:
        df_ed = st.data_editor(df_inv, column_config={"id": None, "Eliminar": st.column_config.CheckboxColumn("¿Borrar?", default=False)}, hide_index=True, use_container_width=True)
        c_inv1, c_inv2 = st.columns(2)
        if c_inv1.button("💾 Guardar Cambios", use_container_width=True):
            for _, r in df_ed.iterrows(): c.execute("UPDATE productos SET nombre=?, precio=?, stock=? WHERE id=?", (r['nombre'], r['precio'], r['stock'], int(r['id'])))
            conn.commit(); st.success("Inventario Actualizado"); st.rerun()
        if c_inv2.button("🗑️ Eliminar Seleccionados", use_container_width=True):
            for _, r in df_ed[df_ed['Eliminar']].iterrows(): c.execute("DELETE FROM productos WHERE id = ?", (int(r['id']),))
            conn.commit(); r.rerun()
        with st.expander("➕ AGREGAR NUEVO PRODUCTO"):
            with st.form("n_p", clear_on_submit=True):
                n = st.text_input("Nombre")
                p = st.number_input("Precio", min_value=0)
                s = st.number_input("Stock Inicial", min_value=0)
                if st.form_submit_button("Añadir"):
                    c.execute("INSERT INTO productos (nombre, precio, stock) VALUES (?,?,?)", (n,p,s))
                    conn.commit(); st.rerun()

elif choice == "📊 Productos Vendidos":
    st.header("📊 Ranking de Productos Vendidos")
    df_v = pd.read_sql_query("SELECT detalle FROM ventas WHERE reporte_id IS NULL", conn)
    if not df_v.empty:
        df_res = obtener_conteo_productos(df_v)
        st.dataframe(df_res, hide_index=True, use_container_width=True)
    else: st.info("No hay
