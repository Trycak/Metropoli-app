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
# Aseguramos que la tabla ventas tenga la columna fecha correctamente
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
menu = ["🛒 Ventas", "📦 Inventario", "📝 Cuentas por Cobrar", "📊 Reporte Histórico"]
choice = st.sidebar.radio("Menú Principal", menu)

# --- SECCIÓN VENTAS ---
if choice == "🛒 Ventas":
    if 'carrito' not in st.session_state: st.session_state.carrito = {}
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.write("### Productos Disponibles")
        prods = pd.read_sql_query("SELECT * FROM productos WHERE stock > 0 ORDER BY nombre ASC", conn)
        
        if prods.empty:
            st.warning("No hay productos en el inventario.")
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
        st.write("### Ticket Actual")
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
                cliente = st.text_input("Nombre del Cliente")

            if st.button("✅ Finalizar Venta", type="primary"):
                if metodo == "Crédito" and not cliente:
                    st.error("Debe poner el nombre del cliente")
                else:
                    # Guardamos la fecha con año-mes-día para facilitar el filtro
                    fecha_hoy = datetime.now().strftime("%Y-%m-%d")
                    hora_hoy = datetime.now().strftime("%H:%M")
                    detalle = ", ".join([f"{i['nombre']}({i['cantidad']})" for i in st.session_state.carrito.values()])
                    
                    c.execute("INSERT INTO ventas (fecha, total, metodo, detalle, cliente) VALUES (?,?,?,?,?)", 
                              (fecha_hoy, total, metodo, detalle, cliente))
                    
                    for pid, item in st.session_state.carrito.items():
                        c.execute("UPDATE productos SET stock = stock - ? WHERE id = ?", (item['cantidad'], int(pid)))
                    
                    conn.commit()
                    st.session_state.carrito = {}
                    st.success("¡Venta registrada!")
                    st.rerun()
            
            if st.button("🗑️ Vaciar Carrito"):
                st.session_state.carrito = {}
                st.rerun()
        else:
            st.info("El carrito está vacío")

# --- SECCIÓN INVENTARIO ---
elif choice == "📦 Inventario":
    st.header("Gestión de Inventario")
    with st.expander("➕ Agregar Nuevo Producto"):
        with st.form("nuevo_producto"):
            nombre = st.text_input("Nombre")
            precio = st.number_input("Precio (₡)", min_value=0)
            stock = st.number_input("Cantidad inicial", min_value=0)
            if st.form_submit_button("Guardar"):
                if nombre:
                    c.execute("INSERT INTO productos (nombre, precio, stock) VALUES (?,?,?)", (nombre, precio, stock))
                    conn.commit()
                    st.rerun()

    df = pd.read_sql_query("SELECT id, nombre, precio, stock FROM productos", conn)
    st.dataframe(df, use_container_width=True)

# --- SECCIÓN REPORTE INTELIGENTE ---
elif choice == "📊 Reporte Histórico":
    st.header("Historial de Ventas")
    
    # Selector de fecha para consultar
    fecha_consulta = st.date_input("Selecciona el día que quieres consultar", datetime.now())
    fecha_str = fecha_consulta.strftime("%Y-%m-%d")
    
    st.write(f"### Ventas del día: {fecha_str}")
    
    # Filtramos la base de datos por la fecha seleccionada
    query = "SELECT * FROM ventas WHERE fecha = ?"
    df_v = pd.read_sql_query(query, conn, params=(fecha_str,))
    
    if not df_v.empty:
        # Mostrar resumen rápido
        col_r1, col_r2 = st.columns(2)
        total_dia = df_v['total'].sum()
        col_r1.metric("Ventas Totales", f"₡{int(total_dia)}")
        col_r2.metric("Cant. Transacciones", len(df_v))
        
        st.dataframe(df_v, use_container_width=True)
        
        # Botón para exportar solo lo que se está viendo
        csv = df_v.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Descargar Reporte (CSV)",
            data=csv,
            file_name=f'reporte_{fecha_str}.csv',
            mime='text/csv',
        )
    else:
        st.info(f"No hay ventas registradas para el día {fecha_str}.")

elif choice == "📝 Cuentas por Cobrar":
    st.header("Cuentas Pendientes (Crédito)")
    cuentas = pd.read_sql_query("SELECT * FROM ventas WHERE metodo = 'Crédito'", conn)
    if not cuentas.empty:
        st.dataframe(cuentas, use_container_width=True)
    else:
        st.info("No hay cuentas pendientes.")
