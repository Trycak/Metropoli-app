import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime

# 1. Configuración de la página
st.set_page_config(page_title="Metropoli Basket Academy", page_icon="🏀", layout="wide")

# 2. Conexión a Base de Datos
def conectar_db():
    conn = sqlite3.connect('metropoli.db', check_same_thread=False)
    return conn

conn = conectar_db()
c = conn.cursor()
c.execute('CREATE TABLE IF NOT EXISTS productos (id INTEGER PRIMARY KEY, nombre TEXT, precio REAL, stock INTEGER)')
c.execute('CREATE TABLE IF NOT EXISTS ventas (id INTEGER PRIMARY KEY, fecha TEXT, total REAL, metodo TEXT, detalle TEXT, cliente TEXT)')
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
        
        if prods.empty:
            st.warning("No hay productos en inventario.")
        else:
            columnas = st.columns(3)
            for i, row in prods.iterrows():
                with columnas[i % 3]:
                    if st.button(f"{row['nombre']}\n₡{int(row['precio'])}", key=f"btn_{row['id']}"):
                        pid = str(row['id'])
                        if pid in st.session_state.carrito:
                            st.session_state.carrito[pid]['cantidad'] += 1
                        else:
                            st.session_state.carrito[pid] = {'nombre': row['nombre'], 'precio': row['precio'], 'cantidad': 1}
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
                # Buscar clientes que ya tienen deudas para facilitar la selección
                clientes_previos = pd.read_sql_query("SELECT DISTINCT cliente FROM ventas WHERE metodo = 'Crédito'", conn)['cliente'].tolist()
                cliente = st.selectbox("Seleccionar Cliente Existente", ["-- Nuevo Cliente --"] + clientes_previos)
                if cliente == "-- Nuevo Cliente --":
                    cliente = st.text_input("Nombre del Nuevo Cliente")

            if st.button("✅ Finalizar Venta", type="primary"):
                if metodo == "Crédito" and not cliente:
                    st.error("Debe asignar un nombre al cliente.")
                else:
                    fecha = datetime.now().strftime("%Y-%m-%d %H:%M")
                    detalle = ", ".join([f"{i['nombre']}({i['cantidad']})" for i in st.session_state.carrito.values()])
                    c.execute("INSERT INTO ventas (fecha, total, metodo, detalle, cliente) VALUES (?,?,?,?,?)", 
                              (fecha, total, metodo, detalle, cliente if cliente else ""))
                    # Restar Stock
                    for pid, item in st.session_state.carrito.items():
                        c.execute("UPDATE productos SET stock = stock - ? WHERE id = ?", (item['cantidad'], int(pid)))
                    conn.commit()
                    st.session_state.carrito = {}
                    st.success("¡Venta/Crédito registrado!")
                    st.rerun()
            
            if st.button("🗑️ Vaciar Carrito"):
                st.session_state.carrito = {}
                st.rerun()
        else:
            st.info("El carrito está vacío")

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

# --- SECCIÓN CUENTAS POR COBRAR ---
elif choice == "📝 Cuentas por Cobrar":
    st.header("Cuentas Pendientes")
    cuentas = pd.read_sql_query("SELECT * FROM ventas WHERE metodo = 'Crédito' ORDER BY id DESC", conn)
    
    if not cuentas.empty:
        # Resumen por cliente
        resumen = cuentas.groupby('cliente')['total'].sum().reset_index()
        st.subheader("Resumen de Deudas por Cliente")
        st.table(resumen)

        st.divider()
        st.subheader("💳 Cancelar Deuda")
        cliente_sel = st.selectbox("Seleccione Cliente que va a pagar:", resumen['cliente'].tolist())
        total_deuda = resumen[resumen['cliente'] == cliente_sel]['total'].values[0]
        
        st.warning(f"El cliente **{cliente_sel}** debe un total de: **₡{int(total_deuda)}**")
        
        metodo_pago = st.selectbox("¿Cómo cancela la deuda?", ["Efectivo", "SINPE Móvil"])
        
        if st.button(f"Confirmar Pago de ₡{int(total_deuda)}"):
            # Actualizamos todas las ventas de 'Crédito' a su nuevo método de pago
            fecha_pago = datetime.now().strftime("%Y-%m-%d %H:%M")
            c.execute("UPDATE ventas SET metodo = ?, fecha = ? WHERE cliente = ? AND metodo = 'Crédito'", 
                      (metodo_pago, f"{fecha_pago} (Pagado)", cliente_sel))
            conn.commit()
            st.success(f"¡Cuenta de {cliente_sel} cancelada con éxito!")
            st.rerun()
            
        st.subheader("Detalle de facturas pendientes")
        st.dataframe(cuentas[['id', 'fecha', 'cliente', 'total', 'detalle']], use_container_width=True)
    else:
        st.info("No hay cuentas por cobrar pendientes.")

# --- SECCIÓN REPORTE ---
elif choice == "📊 Reporte":
    st.header("Reporte de Ventas")
    df_v = pd.read_sql_query("SELECT * FROM ventas ORDER BY id DESC", conn)
    if not df_v.empty:
        total_dia = df_v[df_v['metodo'] != 'Crédito']['total'].sum() # Solo lo pagado
        st.metric("Ingresos Reales (Efectivo/SINPE)", f"₡{int(total_dia)}")
        st.dataframe(df_v[['id', 'fecha', 'total', 'metodo', 'detalle', 'cliente']], use_container_width=True)
