import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
import re

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
st.subheader("Sistema de Gestión de Inventario y Ventas")

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
            st.warning("No hay productos en el inventario. Ve a la pestaña de Inventario para agregar.")
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
                cliente = st.text_input("Nombre del Cliente")

            if st.button("✅ Finalizar Venta", type="primary"):
                if metodo == "Crédito" and not cliente:
                    st.error("Debe poner el nombre del cliente para ventas a crédito")
                else:
                    fecha = datetime.now().strftime("%Y-%m-%d %H:%M")
                    # Formato: Nombre(Cantidad)
                    detalle = ", ".join([f"{i['nombre']}({i['cantidad']})" for i in st.session_state.carrito.values()])
                    c.execute("INSERT INTO ventas (fecha, total, metodo, detalle, cliente) VALUES (?,?,?,?,?)", 
                              (fecha, total, metodo, detalle, cliente))
                    for pid, item in st.session_state.carrito.items():
                        c.execute("UPDATE productos SET stock = stock - ? WHERE id = ?", (item['cantidad'], int(pid)))
                    conn.commit()
                    st.session_state.carrito = {}
                    st.success("¡Venta registrada con éxito!")
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
            precio = st.number_input("Precio (₡)", min_value=0, step=100)
            stock = st.number_input("Cantidad inicial", min_value=0, step=1)
            if st.form_submit_button("Guardar Producto"):
                if nombre:
                    c.execute("INSERT INTO productos (nombre, precio, stock) VALUES (?,?,?)", (nombre, precio, stock))
                    conn.commit()
                    st.success(f"Producto {nombre} agregado")
                    st.rerun()

    st.subheader("Productos Actuales")
    df = pd.read_sql_query("SELECT id, nombre, precio, stock FROM productos", conn)
    st.dataframe(df, use_container_width=True)
    
    st.write("---")
    st.write("### Eliminar o Editar Stock")
    del_id = st.number_input("ID del producto", min_value=1, step=1)
    if st.button("❌ Eliminar Producto"):
        c.execute("DELETE FROM productos WHERE id=?", (del_id,))
        conn.commit()
        st.success("Producto eliminado")
        st.rerun()

# --- SECCIÓN REPORTE ---
elif choice == "📊 Reporte":
    st.header("Reporte de Ventas")
    df_v = pd.read_sql_query("SELECT * FROM ventas ORDER BY id DESC", conn)
    
    if not df_v.empty:
        total_dia = df_v['total'].sum()
        c1, c2 = st.columns(2)
        c1.metric("Ingresos Totales", f"₡{int(total_dia)}")
        c2.metric("Ventas Realizadas", len(df_v))

        # CONTABILIZAR ÍTEMS
        st.subheader("📈 Artículos más vendidos")
        conteo_items = {}
        for d in df_v['detalle']:
            partes = d.split(", ")
            for p in partes:
                if "(" in p and ")" in p:
                    nombre_item = p.split("(")[0]
                    cant_item = int(p.split("(")[1].replace(")", ""))
                    conteo_items[nombre_item] = conteo_items.get(nombre_item, 0) + cant_item
        
        if conteo_items:
            df_items = pd.DataFrame(list(conteo_items.items()), columns=['Producto', 'Cantidad Vendida'])
            st.table(df_items.sort_values(by='Cantidad Vendida', ascending=False))

        # ELIMINAR VENTA CON DEVOLUCIÓN DE STOCK
        st.write("---")
        st.subheader("🗑️ Eliminar Venta y Devolver Stock")
        st.dataframe(df_v[['id', 'fecha', 'total', 'detalle', 'cliente']], use_container_width=True)
        
        venta_a_borrar = st.number_input("ID de la venta a eliminar:", min_value=1, step=1)
        
        if "confirmar_borrado" not in st.session_state:
            st.session_state.confirmar_borrado = False

        if st.button("⚠️ Solicitar Borrado"):
            st.session_state.confirmar_borrado = True

        if st.session_state.confirmar_borrado:
            st.warning(f"¿Confirmar eliminación de Venta #{int(venta_a_borrar)}? El stock será devuelto al inventario.")
            col_si, col_no = st.columns(2)
            
            if col_si.button("SÍ, ELIMINAR Y DEVOLVER STOCK"):
                # 1. Obtener el detalle de la venta antes de borrarla
                res = c.execute("SELECT detalle FROM ventas WHERE id=?", (venta_a_borrar,)).fetchone()
                if res:
                    detalle_texto = res[0]
                    # 2. Procesar el texto para devolver stock
                    # Ejemplo: "Agua(2), Galleta(1)"
                    items_venta = detalle_texto.split(", ")
                    for item in items_venta:
                        try:
                            nombre_p = item.split("(")[0]
                            cantidad_p = int(item.split("(")[1].replace(")", ""))
                            # 3. Actualizar la tabla de productos sumando la cantidad
                            c.execute("UPDATE productos SET stock = stock + ? WHERE nombre = ?", (cantidad_p, nombre_p))
                        except:
                            continue
                    
                    # 4. Borrar la venta
                    c.execute("DELETE FROM ventas WHERE id=?", (venta_a_borrar,))
                    conn.commit()
                    st.session_state.confirmar_borrado = False
                    st.success(f"Venta #{int(venta_a_borrar)} eliminada. El stock ha sido actualizado.")
                    st.rerun()
                else:
                    st.error("ID de venta no encontrado.")
                    st.session_state.confirmar_borrado = False

            if col_no.button("CANCELAR"):
                st.session_state.confirmar_borrado = False
                st.rerun()
    else:
        st.info("No hay ventas registradas")

elif choice == "📝 Cuentas por Cobrar":
    st.header("Cuentas Pendientes (Crédito)")
    cuentas = pd.read_sql_query("SELECT * FROM ventas WHERE metodo = 'Crédito'", conn)
    if not cuentas.empty:
        st.dataframe(cuentas)
    else:
        st.info("No hay cuentas pendientes")
