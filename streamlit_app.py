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
        border: 1px solid #28a5a9;
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

elif choice == "📦 Inventario":
    st.header("📦 Inventario")
    df_inv = pd.read_sql_query("SELECT id, nombre, precio, stock FROM productos ORDER BY nombre ASC", conn)
    df_inv['Eliminar'] = False
    _, mid, _ = st.columns([1, 5, 1])
    with mid:
        df_ed = st.data_editor(df_inv, column_config={
            "id": None, "nombre": st.column_config.TextColumn("Producto", width="medium"),
            "precio": st.column_config.NumberColumn("Precio", width="small", format="₡%d"),
            "stock": st.column_config.NumberColumn("Stock", width="small"),
            "Eliminar": st.column_config.CheckboxColumn("Seleccionar", default=False)
        }, hide_index=True, use_container_width=True)
        
        if st.button("💾 Guardar Cambios Inventario", use_container_width=True):
            for _, row in df_ed.iterrows(): 
                c.execute("UPDATE productos SET nombre=?, precio=?, stock=? WHERE id=?", (row['nombre'], row['precio'], row['stock'], int(row['id'])))
            conn.commit(); st.success("Actualizado"); st.rerun()

elif choice == "📝 Cuentas por Cobrar":
    st.header("📝 Gestión de Créditos")
    df_cc = pd.read_sql_query("SELECT cliente, SUM(total) as deuda FROM ventas WHERE metodo = 'Crédito' GROUP BY cliente", conn)
    
    if not df_cc.empty:
        col_lista, col_detalle = st.columns([1, 2])
        with col_lista:
            st.subheader("Deudores")
            cl_paga = st.selectbox("Seleccionar Cliente:", df_cc['cliente'].tolist())
            monto_resumen = df_cc[df_cc['cliente'] == cl_paga]['deuda'].values[0]
            st.markdown(f"<div class='info-caja'><h4>Total Deuda:<br>₡{int(monto_resumen)}</h4></div>", unsafe_allow_html=True)

        with col_detalle:
            st.subheader(f"Detalle y Edición: {cl_paga}")
            # Cargamos ventas específicas de ese cliente con su ID para poder editarlas
            df_det = pd.read_sql_query("SELECT id, fecha, detalle, total FROM ventas WHERE cliente = ? AND metodo = 'Crédito'", conn, params=(cl_paga,))
            df_det['Borrar?'] = False
            
            # EDITOR DE CUENTA
            df_det_ed = st.data_editor(df_det, column_config={
                "id": None, 
                "fecha": st.column_config.TextColumn("Fecha", disabled=True),
                "detalle": st.column_config.TextColumn("Artículos", width="large"),
                "total": st.column_config.NumberColumn("Monto", format="₡%d"),
                "Borrar?": st.column_config.CheckboxColumn("Seleccionar", default=False)
            }, hide_index=True, use_container_width=True)

            c1, c2 = st.columns(2)
            with c1:
                if st.button("💾 Guardar Cambios en Notas", use_container_width=True):
                    for _, row in df_det_ed.iterrows():
                        c.execute("UPDATE ventas SET detalle = ?, total = ? WHERE id = ?", (row['detalle'], row['total'], int(row['id'])))
                    conn.commit(); st.success("Cambios guardados"); st.rerun()
            
            with c2:
                if st.button("🗑️ Eliminar Notas Seleccionadas", use_container_width=True):
                    a_borrar = df_det_ed[df_det_ed['Borrar?'] == True]
                    for _, row in a_borrar.iterrows():
                        # Devolver stock antes de borrar (opcional, pero recomendado)
                        items = row['detalle'].split(", ")
                        for item in items:
                            if "(" in item:
                                n_p = item.split("(")[0]; cant = int(item.split("(")[1].replace(")", ""))
                                c.execute("UPDATE productos SET stock = stock + ? WHERE nombre = ?", (cant, n_p))
                        c.execute("DELETE FROM ventas WHERE id = ?", (int(row['id']),))
                    conn.commit(); st.success("Eliminado correctamente"); st.rerun()

            st.divider()
            metodo_pago_deuda = st.selectbox("Recibir pago por:", ["Efectivo", "SINPE Móvil"])
            if st.button(f"Saldar Deuda Completa (₡{int(monto_resumen)})", use_container_width=True):
                c.execute("UPDATE ventas SET metodo = ?, fecha = ? WHERE cliente = ? AND metodo = 'Crédito'", (metodo_pago_deuda, f"{datetime.now().strftime('%Y-%m-%d %H:%M')} (Saldado)", cl_paga))
                conn.commit(); st.success(f"¡Cuenta de {cl_paga} saldada!"); st.rerun()
    else:
        st.info("No hay deudas pendientes.")

elif choice == "📊 Productos Vendidos":
    # (Mantener igual que antes)
    st.header("📊 Resumen de Productos Vendidos")
    df_v = pd.read_sql_query("SELECT detalle FROM ventas WHERE reporte_id IS NULL", conn)
    if not df_v.empty:
        # Aquí llamarías a tu función de conteo anterior
        st.info("Resumen disponible")
    else: st.info("No hay ventas.")

elif choice == "📋 Reportes":
    # (Mantener igual que antes)
    st.header("📋 Ventas del Periodo Actual")
    df_p = pd.read_sql_query("SELECT id, fecha, total, metodo, detalle, cliente FROM ventas WHERE reporte_id IS NULL", conn)
    if not df_p.empty:
        st.dataframe(df_p, hide_index=True)
        if st.button("🔴 CERRAR CAJA"):
             # Lógica de cierre anterior
             pass
