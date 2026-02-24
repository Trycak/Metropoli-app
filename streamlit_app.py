import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
import io

# 1. Configuración de la página
st.set_page_config(page_title="Metropoli Cafe", page_icon="🏀", layout="wide")

# 2. Conexión a Base de Datos
def conectar_db():
    conn = sqlite3.connect('metropoli.db', check_same_thread=False)
    return conn

conn = conectar_db()
c = conn.cursor()

# Asegurar tablas
c.execute('CREATE TABLE IF NOT EXISTS productos (id INTEGER PRIMARY KEY, nombre TEXT, precio REAL, stock INTEGER)')
c.execute('CREATE TABLE IF NOT EXISTS ventas (id INTEGER PRIMARY KEY, fecha TEXT, total REAL, metodo TEXT, detalle TEXT, cliente TEXT, reporte_id INTEGER)')
c.execute('CREATE TABLE IF NOT EXISTS históricos_reportes (id INTEGER PRIMARY KEY AUTOINCREMENT, fecha_cierre TEXT, total_caja REAL)')
conn.commit()

# --- ESTILOS VISUALES PERSONALIZADOS ---
st.markdown("""
    <style>
    .stApp { background-color: #134971 !important; }

    /* LOGO DE FONDO GENERAL */
    .stApp::before {
        content: "";
        background-image: url("https://github.com/Trycak/Metropoli-app/blob/main/Logo%20Metropoli%20opacidad.png?raw=true");
        background-repeat: no-repeat;
        background-attachment: fixed;
        background-position: center;
        background-size: 600px;
        position: fixed;
        top: 0; left: 0; width: 100%; height: 100%; z-index: -1;
    }

    /* BARRA LATERAL */
    [data-testid="stSidebar"] {
        background-image: url("https://github.com/Trycak/Metropoli-app/blob/main/Back%20large.png?raw=true");
        background-size: cover;
    }

    /* ELIMINAR ESPACIO DEL TÍTULO DE NAVEGACIÓN VACÍO */
    [data-testid="stSidebar"] .stRadio > label {
        display: none !important;
    }

    /* BOTONES DE LA BARRA LATERAL */
    [data-testid="stSidebar"] .stRadio div[role="radiogroup"] label {
        background-color: rgba(255, 255, 255, 0.1) !important;
        border-radius: 10px !important;
        padding: 20px 15px !important;
        margin-bottom: 15px !important;
        width: 100% !important;
        border: 1px solid rgba(255,255,255,0.2) !important;
    }

    [data-testid="stSidebar"] .stRadio div[role="radiogroup"] label p {
        color: white !important;
        font-weight: bold !important;
        font-size: 22px !important;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.8);
    }

    /* BOTONES DE PRODUCTOS */
    div.stButton > button[key^="p_"] {
        background-color: #28a5a9 !important;
        color: white !important;
        border-radius: 12px !important;
        height: 130px !important;
        width: 100% !important;
        font-weight: bold !important;
        font-size: 20px !important;
        white-space: pre !important; 
        display: block !important;
        line-height: 1.4 !important;
    }

    /* BOTONES DE ACCIÓN (#28a5a9) */
    div.stButton > button, div.stDownloadButton > button {
        background-color: #28a5a9 !important;
        color: white !important;
        font-weight: bold !important;
        font-size: 18px !important;
    }

    /* TABLAS OSCURAS */
    .stDataEditor, .stDataFrame {
        background-color: #134971 !important;
        border: 1px solid rgba(255, 255, 255, 0.2) !important;
        border-radius: 10px !important;
    }

    [data-testid="stDataEditor"] div, [data-testid="stDataFrame"] div {
        color: white !important;
    }

    h1, h2, h3, p, span, label { color: white !important; }

    /* AJUSTE PARA EL LOGO SUPERIOR */
    [data-testid="stSidebar"] [data-testid="stImage"] {
        padding-top: 20px !important;
        padding-bottom: 10px !important;
    }
    </style>
    """, unsafe_allow_html=True)

# --- BARRA LATERAL (SIDEBAR) ---
# Insertamos solo el logo
st.sidebar.image("https://github.com/Trycak/Metropoli-app/blob/main/Logo%20Metropoli.png?raw=true", use_container_width=True)

# Menú de navegación sin título
menu = ["🛒 Ventas", "📊 Resumen de Productos", "📦 Inventario", "📝 Cuentas por Cobrar", "📋 Reporte de Pagos"]
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
                texto_final = f"{row['nombre']} ({int(row['stock'])})\n₡{int(row['precio'])}"
                if st.button(texto_final, key=f"p_{row['id']}", disabled=row['stock']<=0):
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
                if c2.button("X", key=f"del_{pid}"):
                    del st.session_state.carrito[pid]; st.rerun()
            st.divider()
            metodo = st.selectbox("Forma de Pago", ["Efectivo", "SINPE Móvil", "Crédito"])
            cliente_n = ""
            if metodo == "Crédito":
                clientes_db = pd.read_sql_query("SELECT DISTINCT cliente FROM ventas WHERE metodo = 'Crédito' AND cliente != ''", conn)['cliente'].tolist()
                opc = st.selectbox("Seleccionar Cliente", ["-- Nuevo --"] + clientes_db)
                cliente_n = st.text_input("Nombre del Cliente") if opc == "-- Nuevo --" else opc
            if st.button("✅ FINALIZAR VENTA", use_container_width=True):
                if metodo == "Crédito" and not cliente_n: st.error("Falta nombre")
                else:
                    det = ", ".join([f"{v['nombre']}({v['cantidad']})" for v in st.session_state.carrito.values()])
                    c.execute("INSERT INTO ventas (fecha, total, metodo, detalle, cliente) VALUES (?,?,?,?,?)", (datetime.now().strftime("%Y-%m-%d %H:%M"), total_v, metodo, det, cliente_n))
                    for pid, item in st.session_state.carrito.items():
                        c.execute("UPDATE productos SET stock = stock - ? WHERE id = ?", (item['cantidad'], int(pid)))
                    conn.commit(); st.session_state.carrito = {}; st.success("¡Venta Lista!"); st.rerun()
        else: st.info("El carrito está vacío")

elif choice == "📊 Resumen de Productos":
    st.header("📊 Resumen de Ventas por Artículo")
    df_v = pd.read_sql_query("SELECT detalle FROM ventas WHERE reporte_id IS NULL", conn)
    if not df_v.empty:
        df_res = obtener_conteo_productos(df_v)
        st.dataframe(df_res, use_container_width=True, hide_index=True)
        st.download_button(label="📥 EXPORTAR RESUMEN A CSV", data=to_csv(df_res), file_name=f"resumen_{datetime.now().strftime('%Y%m%d')}.csv", mime="text/csv", use_container_width=True)
    else: st.info("No hay ventas registradas.")

elif choice == "📦 Inventario":
    st.header("📦 Gestión de Inventario")
    df_inv = pd.read_sql_query("SELECT id, nombre, precio, stock FROM productos ORDER BY nombre ASC", conn)
    df_ed = st.data_editor(df_inv, column_config={"id": None}, hide_index=True, use_container_width=True)
    if st.button("💾 Guardar Cambios", use_container_width=True):
        for _, row in df_ed.iterrows(): c.execute("UPDATE productos SET nombre=?, precio=?, stock=? WHERE id=?", (row['nombre'], row['precio'], row['stock'], int(row['id'])))
        conn.commit(); st.success("Actualizado"); st.rerun()
    with st.expander("➕ Agregar Nuevo Producto"):
        with st.form("new_p"):
            n, p, s = st.text_input("Nombre"), st.number_input("Precio"), st.number_input("Stock")
            if st.form_submit_button("Añadir"):
                c.execute("INSERT INTO productos (nombre, precio, stock) VALUES (?,?,?)", (n,p,s)); conn.commit(); st.rerun()

elif choice == "📝 Cuentas por Cobrar":
    st.header("📝 Gestión de Créditos")
    # ... (Resto del código sin cambios)
