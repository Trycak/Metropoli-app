import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
import io
import xml.etree.ElementTree as ET

# 1. Configuración de la página
st.set_page_config(page_title="Metropoli Basket Academy", page_icon="🏀", layout="wide")

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

# --- ESTILOS VISUALES ---
st.markdown("""
    <style>
    .main { background-color: #f4f7f9; }
    [data-testid="stSidebar"] { background-color: #16a5b5 !important; }
    [data-testid="stSidebar"] div[role="radiogroup"] label { font-size: 18px !important; color: white !important; font-weight: bold !important; }
    div.stButton > button[key^="p_"] { background-color: #ffffff !important; color: #1f1f1f !important; border: 1px solid #e0e4e8 !important; border-radius: 12px !important; height: 110px !important; width: 100% !important; }
    div[data-testid="column"] button[key^="del_"] { background-color: #ff4b4b !important; color: white !important; border-radius: 50% !important; width: 32px !important; height: 32px !important; display: flex !important; align-items: center !important; justify-content: center !important; }
    </style>
    """, unsafe_allow_html=True)

# --- FUNCIONES ---
def obtener_conteo_productos(df):
    conteo = {}
    for detalle in df['detalle']:
        partes = detalle.split(", ")
        for p in partes:
            if "(" in p and ")" in p:
                try:
                    nombre = p.split("(")[0]; cantidad = int(p.split("(")[1].replace(")", ""))
                    conteo[nombre] = conteo.get(nombre, 0) + cantidad
                except: continue
    return pd.DataFrame(list(conteo.items()), columns=['Producto', 'Cantidad']).sort_values(by='Cantidad', ascending=False) if conteo else pd.DataFrame()

def convertir_a_xml(df):
    root = ET.Element("ReporteVentas")
    for _, row in df.iterrows():
        venta = ET.SubElement(root, "Venta")
        for field in df.columns:
            child = ET.SubElement(venta, field)
            child.text = str(row[field])
    return ET.tostring(root, encoding='utf-8', method='xml')

# Función para convertir a CSV (Solución al error de xlsxwriter)
def to_csv(df):
    return df.to_csv(index=False).encode('utf-8')

# --- MENÚ ---
st.sidebar.title("🏀 Metropoli POS")
menu = ["🛒 Ventas", "📊 Resumen de Productos", "📦 Inventario", "📝 Cuentas por Cobrar", "📋 Reporte de Pagos"]
choice = st.sidebar.radio("Navegación", menu)

if choice == "🛒 Ventas":
    if 'carrito' not in st.session_state: st.session_state.carrito = {}
    col_prods, col_cart = st.columns([2, 1])
    with col_prods:
        st.subheader("Productos")
        prods = pd.read_sql_query("SELECT * FROM productos ORDER BY nombre ASC", conn)
        grid = st.columns(3)
        for i, row in prods.iterrows():
            with grid[i % 3]:
                if st.button(f"{row['nombre']}\n({int(row['stock'])})\n₡{int(row['precio'])}", key=f"p_{row['id']}", disabled=row['stock']<=0):
                    pid = str(row['id'])
                    if pid in st.session_state.carrito: st.session_state.carrito[pid]['cantidad'] += 1
                    else: st.session_state.carrito[pid] = {'nombre': row['nombre'], 'precio': row['precio'], 'cantidad': 1}
                    st.rerun()
    with col_cart:
        st.subheader("Carrito")
        if st.session_state.carrito:
            total_v = 0
            for pid, item in list(st.session_state.carrito.items()):
                sub = item['precio'] * item['cantidad']; total_v += sub
                c1, c2 = st.columns([5, 1])
                c1.write(f"**{item['nombre']} x{item['cantidad']}** (₡{int(sub)})")
                if c2.button("X", key=f"del_{pid}"):
                    del st.session_state.carrito[pid]; st.rerun()
            st.divider()
            metodo = st.selectbox("Pago", ["Efectivo", "SINPE Móvil", "Crédito"])
            cliente_n = ""
            if metodo == "Crédito":
                clientes_db = pd.read_sql_query("SELECT DISTINCT cliente FROM ventas WHERE metodo = 'Crédito' AND cliente != ''", conn)['cliente'].tolist()
                opc = st.selectbox("Seleccionar Cliente", ["-- Nuevo --"] + clientes_db)
                cliente_n = st.text_input("Nombre") if opc == "-- Nuevo --" else opc
            if st.button("✅ Finalizar", type="primary", use_container_width=True):
                if metodo == "Crédito" and not cliente_n: st.error("Falta nombre")
                else:
                    det = ", ".join([f"{v['nombre']}({v['cantidad']})" for v in st.session_state.carrito.values()])
                    c.execute("INSERT INTO ventas (fecha, total, metodo, detalle, cliente) VALUES (?,?,?,?,?)", (datetime.now().strftime("%Y-%m-%d %H:%M"), total_v, metodo, det, cliente_n))
                    for pid, item in st.session_state.carrito.items():
                        c.execute("UPDATE productos SET stock = stock - ? WHERE id = ?", (item['cantidad'], int(pid)))
                    conn.commit(); st.session_state.carrito = {}; st.success("¡Venta Lista!"); st.rerun()
        else: st.info("Carrito vacío")

elif choice == "📦 Inventario":
    st.header("Inventario")
    df_inv = pd.read_sql_query("SELECT id, nombre, precio, stock FROM productos ORDER BY nombre ASC", conn)
    df_ed = st.data_editor(df_inv, column_config={"id": st.column_config.NumberColumn(disabled=True)}, hide_index=True, use_container_width=True)
    if st.button("💾 Guardar Cambios"):
        for _, row in df_ed.iterrows(): c.execute("UPDATE productos SET nombre=?, precio=?, stock=? WHERE id=?", (row['nombre'], row['precio'], row['stock'], int(row['id'])))
        conn.commit(); st.success("Actualizado"); st.rerun()
    with st.expander("➕ Agregar Nuevo Producto"):
        with st.form("new_p"):
            n, p, s = st.text_input("Nombre"), st.number_input("Precio"), st.number_input("Stock")
            if st.form_submit_button("Añadir"):
                c.execute("INSERT INTO productos (nombre, precio, stock) VALUES (?,?,?)", (n,p,s)); conn.commit(); st.rerun()

elif choice == "📊 Resumen de Productos":
    st.header("Ventas por Artículo")
    df_v = pd.read_sql_query("SELECT detalle FROM ventas WHERE reporte_id IS NULL", conn)
    if not df_v.empty:
        df_res = obtener_conteo_productos(df_v)
        st.table(df_res)
        # BOTÓN NUEVO PARA EXPORTAR RESUMEN (Ahora en CSV para evitar errores)
        st.download_button(
            label="📥 Exportar Resumen (Excel/CSV)",
            data=to_csv(df_res),
            file_name=f"resumen_ventas_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )
    else: st.info("No hay ventas registradas en este turno.")

elif choice == "📝 Cuentas por Cobrar":
    st.header("Gestión de Créditos")
    df_cc = pd.read_sql_query("SELECT cliente, SUM(total) as deuda FROM ventas WHERE metodo = 'Crédito' GROUP BY cliente", conn)
    if not df_cc.empty:
        st.dataframe(df_cc, use_container_width=True, hide_index=True)
        cl_paga = st.selectbox("Cliente:", df_cc['cliente'].tolist())
        monto = df_cc[df_cc['cliente'] == cl_paga]['deuda'].values[0]
        metodo_pago_deuda = st.selectbox("Recibir pago por:", ["Efectivo", "SINPE Móvil"])
        if st.button(f"Saldar Deuda (₡{int(monto)})"):
            c.execute("UPDATE ventas SET metodo = ?, fecha = ? WHERE cliente = ? AND metodo = 'Crédito'", (metodo_pago_deuda, f"{datetime.now().strftime('%Y-%m-%d %H:%M')} (Saldado)", cl_paga))
            conn.commit(); st.success("Cuenta cancelada"); st.rerun()
    else: st.info("No hay deudas pendientes.")

elif choice == "📋 Reporte de Pagos":
    st.header("Auditoría de Ventas")
    df_p = pd.read_sql_query("SELECT id, fecha, total, metodo, detalle, cliente FROM ventas WHERE reporte_id IS NULL", conn)
    if not df_p.empty:
        df_p['Eliminar'] = False
        df_p_ed = st.data_editor(df_p, column_config={
            "id": st.column_config.NumberColumn(disabled=True),
            "metodo": st.column_config.SelectboxColumn("Método", options=["Efectivo", "SINPE Móvil", "Crédito"]),
            "Eliminar": st.column_config.CheckboxColumn("Borrar?", default=False)
        }, hide_index=True, use_container_width=True)
        col_r1, col_r2 = st.columns(2)
        with col_r1:
            if st.button("💾 Guardar Cambios en Métodos"):
                for _, row in df_p_ed.iterrows(): c.execute("UPDATE ventas SET metodo = ? WHERE id = ?", (row['metodo'], int(row['id'])))
                conn.commit(); st.success("Métodos actualizados"); st.rerun()
        with col_r2:
            if st.button("🗑️ ELIMINAR VENTAS SELECCIONADAS"):
                ventas_a_borrar = df_p_ed[df_p_ed['Eliminar'] == True]
                for _, v in ventas_a_borrar.iterrows():
                    det = v['detalle'].split(", ")
                    for item in det:
                        if "(" in item:
                            n_prod = item.split("(")[0]
                            cant = int(item.split("(")[1].replace(")", ""))
                            c.execute("UPDATE productos SET stock = stock + ? WHERE nombre = ?", (cant, n_prod))
                    c.execute("DELETE FROM ventas WHERE id = ?", (int(v['id']),))
                conn.commit(); st.success("Ventas eliminadas y stock devuelto"); st.rerun()
        st.divider()
        st.download_button("📥 Descargar XML", data=convertir_a_xml(df_p_ed.drop(columns=['Eliminar'])), file_name="reporte.xml", mime="application/xml")
        if st.button("🔴 CERRAR CAJA"):
            tot = df_p_ed[(df_p_ed['metodo']!='Crédito') & (df_p_ed['Eliminar']==False)]['total'].sum()
            c.execute("INSERT INTO históricos_reportes (fecha_cierre, total_caja) VALUES (?,?)", (datetime.now().strftime("%Y-%m-%d %H:%M"), tot))
            c.execute("UPDATE ventas SET reporte_id = (SELECT max(id) FROM históricos_reportes) WHERE reporte_id IS NULL")
            conn.commit(); st.rerun()
    else: st.info("No hay ventas.")
