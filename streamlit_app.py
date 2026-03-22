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

# --- ESTILOS VISUALES ---
st.markdown("""
    <style>
    .stApp { background-color: #134971 !important; }
    [data-testid="stSidebar"] { background-image: url("https://github.com/Trycak/Metropoli-app/blob/main/Back%20large.png?raw=true"); background-size: cover; }
    h1, h2, h3, p, span, label { color: white !important; text-align: center; }
    .stDataEditor, .stDataFrame { background-color: #134971 !important; border-radius: 10px !important; }
    
    div.stButton > button[key^="p_"] {
        background-color: #28a5a9 !important; color: white !important; border-radius: 12px !important;
        height: 115px !important; width: 100% !important; font-weight: bold !important; font-size: 18px !important;
    }
    
    .info-caja {
        background-color: rgba(255, 255, 255, 0.1);
        padding: 15px;
        border-radius: 10px;
        border: 2px solid #28a5a9;
        margin-bottom: 20px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- FUNCIONES ---
def to_csv(df):
    return df.to_csv(index=False).encode('utf-8')

# --- BARRA LATERAL ---
st.sidebar.image("https://github.com/Trycak/Metropoli-app/blob/main/Logo%20Metropoli.png?raw=true", use_container_width=True)
menu = ["🛒 Ventas", "📦 Inventario", "📊 Productos Vendidos", "📝 Cuentas por Cobrar", "📋 Reportes"]
choice = st.sidebar.radio("Nav", menu, label_visibility="collapsed")

# --- SECCIÓN VENTAS ---
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
                if c2.button("X", key=f"del_{pid}"): del st.session_state.carrito[pid]; st.rerun()
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

# --- SECCIÓN REPORTES (CON CIERRE DE CAJA CORREGIDO) ---
elif choice == "📋 Reportes":
    st.header("📋 Gestión de Ventas y Cierre")
    df_p = pd.read_sql_query("SELECT id, fecha, total, metodo, detalle, cliente FROM ventas WHERE reporte_id IS NULL", conn)
    
    if not df_p.empty:
        st.subheader("Ventas del Turno Actual")
        df_p['Borrar?'] = False
        df_p_ed = st.data_editor(df_p, column_config={
            "id": None, "fecha": st.column_config.TextColumn("Hora", width="small"),
            "total": st.column_config.NumberColumn("Total", format="₡%d"),
            "metodo": st.column_config.SelectboxColumn("Pago", options=["Efectivo", "SINPE Móvil", "Crédito"]),
            "detalle": "Productos", "cliente": "Cliente",
            "Borrar?": st.column_config.CheckboxColumn("Eliminar", default=False)
        }, hide_index=True, use_container_width=True)
        
        c1, c2 = st.columns(2)
        with c1:
            if st.button("💾 Guardar Cambios en Ventas", use_container_width=True):
                for _, row in df_p_ed.iterrows():
                    c.execute("UPDATE ventas SET metodo = ?, total = ? WHERE id = ?", (row['metodo'], row['total'], int(row['id'])))
                conn.commit(); st.success("Ventas actualizadas"); st.rerun()
        with c2:
            if st.button("🗑️ Eliminar Seleccionadas", use_container_width=True):
                a_borrar = df_p_ed[df_p_ed['Borrar?'] == True]
                for _, row in a_borrar.iterrows():
                    c.execute("DELETE FROM ventas WHERE id = ?", (int(row['id']),))
                conn.commit(); st.success("Venta eliminada"); st.rerun()
        
        st.divider()
        # LÓGICA DE CIERRE REFORZADA
        efectivo = df_p_ed[df_p_ed['metodo'] == 'Efectivo']['total'].sum()
        sinpe = df_p_ed[df_p_ed['metodo'] == 'SINPE Móvil']['total'].sum()
        total_caja = efectivo + sinpe

        st.markdown(f"""
            <div class='info-caja'>
                <h2>RESUMEN DE CAJA ACTUAL</h2>
                <p>Efectivo: ₡{int(efectivo)} | SINPE: ₡{int(sinpe)}</p>
                <h1 style='color: #28a5a9;'>TOTAL: ₡{int(total_caja)}</h1>
            </div>
        """, unsafe_allow_html=True)

        if st.button("🔴 EJECUTAR CIERRE DE CAJA", use_container_width=True):
            # 1. Crear el reporte histórico
            c.execute("INSERT INTO históricos_reportes (fecha_cierre, total_caja) VALUES (?,?)", 
                     (datetime.now().strftime("%Y-%m-%d %H:%M"), total_caja))
            
            # 2. Vincular todas las ventas actuales al nuevo reporte
            c.execute("UPDATE ventas SET reporte_id = (SELECT max(id) FROM históricos_reportes) WHERE reporte_id IS NULL")
            
            conn.commit()
            st.balloons()
            st.success(f"Caja cerrada con ₡{int(total_caja)}. Las ventas se han archivado.")
            st.rerun()
    else:
        st.info("No hay ventas activas en el turno actual.")
        
    # Mostrar Historial de Cierres
    st.subheader("📚 Historial de Cierres")
    df_hist = pd.read_sql_query("SELECT fecha_cierre, total_caja FROM históricos_reportes ORDER BY id DESC LIMIT 10", conn)
    st.table(df_hist)

# (Se omiten las secciones de Inventario y Cuentas por cobrar para ahorrar espacio, pero siguen igual)
