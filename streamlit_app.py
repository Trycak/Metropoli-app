import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
import io

# 1. Configuración de la página
st.set_page_config(page_title="Metropoli Basket Academy", page_icon="🏀", layout="wide")

# 2. Conexión a Base de Datos
def conectar_db():
    conn = sqlite3.connect('metropoli.db', check_same_thread=False)
    return conn

conn = conectar_db()
c = conn.cursor()
# Tabla de productos
c.execute('CREATE TABLE IF NOT EXISTS productos (id INTEGER PRIMARY KEY, nombre TEXT, precio REAL, stock INTEGER)')
# Tabla de ventas (añadimos columna reporte_id)
try:
    c.execute('ALTER TABLE ventas ADD COLUMN reporte_id INTEGER')
except:
    pass
c.execute('CREATE TABLE IF NOT EXISTS ventas (id INTEGER PRIMARY KEY, fecha TEXT, total REAL, metodo TEXT, detalle TEXT, cliente TEXT, reporte_id INTEGER)')
# Tabla para controlar los consecutivos de reportes
c.execute('CREATE TABLE IF NOT EXISTS históricos_reportes (id INTEGER PRIMARY KEY AUTOINCREMENT, fecha_cierre TEXT, total_caja REAL)')
conn.commit()

# --- ESTILOS ---
st.markdown("""
    <style>
    .main { background-color: #f5f5f5; }
    .stButton>button { width: 100%; border-radius: 10px; height: 3em; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# 3. Encabezado
st.title("🏀 Metropoli Basket Academy")

# 4. Menú Lateral
menu = ["🛒 Ventas", "📦 Inventario", "📝 Cuentas por Cobrar", "📊 Reporte"]
choice = st.sidebar.radio("Menú Principal", menu)

# --- SECCIÓN VENTAS ---
if choice == "🛒 Ventas":
    if 'carrito' not in st.session_state: st.session_state.carrito = {}
    col1, col2 = st.columns([2, 1])
    with col1:
        st.write("### Productos Disponibles")
        prods = pd.read_sql_query("SELECT * FROM productos WHERE stock > 0 ORDER BY nombre ASC", conn)
        if prods.empty: st.warning("No hay productos en inventario.")
        else:
            columnas = st.columns(3)
            for i, row in prods.iterrows():
                with columnas[i % 3]:
                    if st.button(f"{row['nombre']}\n₡{int(row['precio'])}", key=f"btn_{row['id']}"):
                        pid = str(row['id'])
                        if pid in st.session_state.carrito: st.session_state.carrito[pid]['cantidad'] += 1
                        else: st.session_state.carrito[pid] = {'nombre': row['nombre'], 'precio': row['precio'], 'cantidad': 1}
                        st.rerun()
    with col2:
        st.write("### Detalle de Venta")
        if st.session_state.carrito:
            total = 0
            for pid, item in list(st.session_state.carrito.items()):
                subtotal = item['precio'] * item['cantidad']
                total += subtotal
                st.write(f"**{item['nombre']}** x{item['cantidad']} = ₡{int(subtotal)}")
            st.divider()
            st.write(f"## Total: ₡{int(total)}")
            metodo = st.selectbox("Método de Pago", ["Efectivo", "SINPE Móvil", "Crédito"])
            cliente = ""
            if metodo == "Crédito":
                clientes_previos = pd.read_sql_query("SELECT DISTINCT cliente FROM ventas WHERE metodo = 'Crédito'", conn)['cliente'].tolist()
                cliente = st.selectbox("Seleccionar Cliente", ["-- Nuevo Cliente --"] + clientes_previos)
                if cliente == "-- Nuevo Cliente --": cliente = st.text_input("Nombre del Nuevo Cliente")
            if st.button("✅ Finalizar Venta", type="primary"):
                if metodo == "Crédito" and not cliente: st.error("Debe asignar un nombre.")
                else:
                    fecha = datetime.now().strftime("%Y-%m-%d %H:%M")
                    detalle = ", ".join([f"{i['nombre']}({i['cantidad']})" for i in st.session_state.carrito.values()])
                    # Se guarda con reporte_id NULL (indicando que es del reporte abierto actual)
                    c.execute("INSERT INTO ventas (fecha, total, metodo, detalle, cliente, reporte_id) VALUES (?,?,?,?,?, NULL)", 
                              (fecha, total, metodo, detalle, cliente if cliente else ""))
                    for pid, item in st.session_state.carrito.items():
                        c.execute("UPDATE productos SET stock = stock - ? WHERE id = ?", (item['cantidad'], int(pid)))
                    conn.commit(); st.session_state.carrito = {}; st.success("¡Venta registrada!"); st.rerun()
        else: st.info("El carrito está vacío")

# --- SECCIÓN INVENTARIO ---
elif choice == "📦 Inventario":
    st.header("Gestión de Inventario")
    tab1, tab2, tab3 = st.tabs(["📋 Lista Actual", "➕ Nuevo Producto", "✏️ Editar / 🗑️ Eliminar"])
    with tab1:
        df = pd.read_sql_query("SELECT id, nombre, precio, stock FROM productos ORDER BY nombre ASC", conn)
        st.dataframe(df, use_container_width=True, hide_index=True)
    with tab2:
        with st.form("nuevo_p"):
            n = st.text_input("Nombre"); p = st.number_input("Precio", min_value=0); s = st.number_input("Stock", min_value=0)
            if st.form_submit_button("Guardar"):
                c.execute("INSERT INTO productos (nombre, precio, stock) VALUES (?,?,?)", (n, p, s)); conn.commit(); st.rerun()
    with tab3:
        prods_list = pd.read_sql_query("SELECT * FROM productos ORDER BY nombre ASC", conn)
        if not prods_list.empty:
            seleccionado = st.selectbox("Producto:", prods_list['nombre'].tolist())
            datos_p = prods_list[prods_list['nombre'] == seleccionado].iloc[0]
            with st.form("edit_p"):
                nuevo_n = st.text_input("Nombre", value=datos_p['nombre'])
                nuevo_p = st.number_input("Precio", value=float(datos_p['precio']))
                nuevo_s = st.number_input("Stock", value=int(datos_p['stock']))
                if st.form_submit_button("Actualizar"):
                    c.execute("UPDATE productos SET nombre=?, precio=?, stock=? WHERE id=?", (nuevo_n, nuevo_p, nuevo_s, datos_p['id']))
                    conn.commit(); st.rerun()
                if st.form_submit_button("Eliminar Permanentemente"):
                    c.execute("DELETE FROM productos WHERE id=?", (datos_p['id'],)); conn.commit(); st.rerun()

# --- SECCIÓN CUENTAS POR COBRAR ---
elif choice == "📝 Cuentas por Cobrar":
    st.header("Cuentas Pendientes")
    cuentas = pd.read_sql_query("SELECT * FROM ventas WHERE metodo = 'Crédito' ORDER BY id DESC", conn)
    if not cuentas.empty:
        resumen = cuentas.groupby('cliente')['total'].sum().reset_index()
        st.table(resumen)
        cliente_sel = st.selectbox("Seleccione Cliente para pagar:", resumen['cliente'].tolist())
        total_deuda = resumen[resumen['cliente'] == cliente_sel]['total'].sum()
        metodo_pago = st.selectbox("Método de pago:", ["Efectivo", "SINPE Móvil"])
        if st.button(f"Confirmar Pago de ₡{int(total_deuda)}"):
            fecha_pago = datetime.now().strftime("%Y-%m-%d %H:%M")
            c.execute("UPDATE ventas SET metodo = ?, fecha = ? WHERE cliente = ? AND metodo = 'Crédito'", (metodo_pago, f"{fecha_pago} (Pagado)", cliente_sel))
            conn.commit(); st.success("¡Pagado!"); st.rerun()
    else: st.info("Sin cuentas pendientes.")

# --- SECCIÓN REPORTE (CON CIERRE Y CONSECUTIVOS) ---
elif choice == "📊 Reporte":
    st.header("Gestión de Reportes")
    tab_actual, tab_historial = st.tabs(["📄 Reporte Abierto (Actual)", "📜 Historial de Reportes"])

    with tab_actual:
        # Solo ventas que NO pertenecen a un reporte cerrado (reporte_id IS NULL)
        df_actual = pd.read_sql_query("SELECT * FROM ventas WHERE reporte_id IS NULL ORDER BY id DESC", conn)
        
        if not df_actual.empty:
            ingresos_caja = df_actual[df_actual['metodo'] != 'Crédito']['total'].sum()
            st.metric("Total en Caja (Reporte Actual)", f"₡{int(ingresos_caja)}")
            
            st.subheader("Ventas del Turno")
            st.dataframe(df_actual[['id', 'fecha', 'total', 'metodo', 'detalle', 'cliente']], use_container_width=True)

            st.divider()
            if st.button("🔴 CERRAR REPORTE E INICIAR NUEVO"):
                # 1. Crear el registro histórico
                fecha_cierre = datetime.now().strftime("%Y-%m-%d %H:%M")
                c.execute("INSERT INTO históricos_reportes (fecha_cierre, total_caja) VALUES (?,?)", (fecha_cierre, ingresos_caja))
                nuevo_id = c.lastrowid
                # 2. Asignar el ID de reporte a las ventas actuales
                c.execute("UPDATE ventas SET reporte_id = ? WHERE reporte_id IS NULL", (nuevo_id,))
                conn.commit()
                st.success(f"Reporte #{nuevo_id} cerrado con éxito. Iniciando nuevo reporte...")
                st.rerun()
        else:
            st.info("No hay ventas en el reporte actual. Inicia una venta para ver datos.")

    with tab_historial:
        st.subheader("Consulta de Reportes Anteriores")
        reportes_lista = pd.read_sql_query("SELECT * FROM históricos_reportes ORDER BY id DESC", conn)
        
        if not reportes_lista.empty:
            # Selector por consecutivo y fecha
            reportes_lista['info'] = "Reporte #" + reportes_lista['id'].astype(str) + " - " + reportes_lista['fecha_cierre']
            rep_sel = st.selectbox("Seleccione un reporte para consultar:", reportes_lista['info'].tolist())
            id_rep = int(rep_sel.split("#")[1].split(" - ")[0])
            
            # Cargar datos de ese reporte específico
            df_hist = pd.read_sql_query("SELECT * FROM ventas WHERE reporte_id = ?", conn, params=(id_rep,))
            
            col_a, col_b = st.columns(2)
            col_a.metric("Total Caja", f"₡{int(df_hist[df_hist['metodo'] != 'Crédito']['total'].sum())}")
            col_b.write(f"**Fecha Cierre:** {reportes_lista[reportes_lista['id']==id_rep]['fecha_cierre'].values[0]}")
            
            st.dataframe(df_hist[['id', 'fecha', 'total', 'metodo', 'detalle', 'cliente']], use_container_width=True)
            
            # Exportar ese reporte específico a Excel
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df_hist.to_excel(writer, index=False)
            st.download_button("📥 Descargar este Reporte (Excel)", data=output.getvalue(), file_name=f"Reporte_{id_rep}.xlsx")
        else:
            st.write("Aún no hay reportes cerrados en el historial.")
