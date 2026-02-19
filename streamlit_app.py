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

# --- SECCIÓN INVENTARIO (ACTUALIZADA CON EDICIÓN) ---
elif choice == "📦 Inventario":
    st.header("Gestión de Inventario")
    
    # Pestañas dentro de inventario para organizar mejor
    tab1, tab2, tab3 = st.tabs(["📋 Lista Actual", "➕ Nuevo Producto", "✏️ Editar / 🗑️ Eliminar"])

    with tab1:
        st.subheader("Productos en Catálogo")
        df = pd.read_sql_query("SELECT id, nombre, precio, stock FROM productos ORDER BY nombre ASC", conn)
        st.dataframe(df, use_container_width=True, hide_index=True)

    with tab2:
        st.subheader("Agregar Nuevo Producto")
        with st.form("nuevo_producto", clear_on_submit=True):
            nombre_n = st.text_input("Nombre del Producto")
            precio_n = st.number_input("Precio (₡)", min_value=0, step=100)
            stock_n = st.number_input("Cantidad inicial", min_value=0, step=1)
            if st.form_submit_button("💾 Guardar"):
                if nombre_n:
                    c.execute("INSERT INTO productos (nombre, precio, stock) VALUES (?,?,?)", (nombre_n, precio_n, stock_n))
                    conn.commit()
                    st.success(f"'{nombre_n}' agregado correctamente.")
                    st.rerun()

    with tab3:
        st.subheader("Modificar Producto Existente")
        prods_list = pd.read_sql_query("SELECT * FROM productos ORDER BY nombre ASC", conn)
        
        if not prods_list.empty:
            # Crear lista de nombres para el selector
            nombres = prods_list['nombre'].tolist()
            seleccionado = st.selectbox("Seleccione el producto a editar o eliminar:", nombres)
            
            # Obtener datos del producto seleccionado
            datos_p = prods_list[prods_list['nombre'] == seleccionado].iloc[0]
            
            with st.form("editar_producto"):
                col_e1, col_e2 = st.columns(2)
                nuevo_nombre = col_e1.text_input("Editar Nombre", value=datos_p['nombre'])
                nuevo_precio = col_e2.number_input("Editar Precio (₡)", value=float(datos_p['precio']), step=50.0)
                nuevo_stock = st.number_input("Ajustar Stock Actual", value=int(datos_p['stock']), step=1)
                
                col_b1, col_b2 = st.columns(2)
                if col_b1.form_submit_button("🔄 Actualizar Datos"):
                    c.execute("UPDATE productos SET nombre=?, precio=?, stock=? WHERE id=?", 
                              (nuevo_nombre, nuevo_precio, nuevo_stock, datos_p['id']))
                    conn.commit()
                    st.success("¡Producto actualizado!")
                    st.rerun()
                
                if col_b2.form_submit_button("🗑️ Eliminar Permanentemente"):
                    c.execute("DELETE FROM productos WHERE id=?", (datos_p['id'],))
                    conn.commit()
                    st.warning(f"'{seleccionado}' ha sido eliminado.")
                    st.rerun()
        else:
            st.info("No hay productos para editar.")

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

        # ELIMINAR VENTA CON SELECCIÓN
        st.write("---")
        st.subheader("🗑️ Eliminar Venta y Devolver Stock")
        df_v['display'] = df_v['id'].astype(str) + " | " + df_v['fecha'] + " | ₡" + df_v['total'].astype(int).astype(str) + " | " + df_v['cliente']
        opciones_ventas = df_v['display'].tolist()
        
        seleccion = st.selectbox("Ventas recientes:", opciones_ventas)
        id_seleccionado = int(seleccion.split(" | ")[0])
        detalle_seleccionado = df_v[df_v['id'] == id_seleccionado].iloc[0]['detalle']

        if st.button("⚠️ Solicitar Borrado de Venta Seleccionada"):
            st.session_state.confirmar_borrado = True

        if st.session_state.get('confirmar_borrado', False):
            st.warning(f"¿Confirmar eliminación de Venta #{id_seleccionado}?\nContenido: {detalle_seleccionado}")
            col_si, col_no = st.columns(2)
            
            if col_si.button("SÍ, ELIMINAR Y DEVOLVER STOCK"):
                items_venta = detalle_seleccionado.split(", ")
                for item in items_venta:
                    try:
                        nombre_p = item.split("(")[0]
                        cantidad_p = int(item.split("(")[1].replace(")", ""))
                        c.execute("UPDATE productos SET stock = stock + ? WHERE nombre = ?", (cantidad_p, nombre_p))
                    except:
                        continue
                
                c.execute("DELETE FROM ventas WHERE id=?", (id_seleccionado,))
                conn.commit()
                st.session_state.confirmar_borrado = False
                st.success(f"Venta #{id_seleccionado} eliminada y stock devuelto.")
                st.rerun()

            if col_no.button("CANCELAR"):
                st.session_state.confirmar_borrado = False
                st.rerun()
        
        st.write("### Historial Completo")
        st.dataframe(df_v[['id', 'fecha', 'total', 'metodo', 'detalle', 'cliente']], use_container_width=True)
    else:
        st.info("No hay ventas registradas")

elif choice == "📝 Cuentas por Cobrar":
    st.header("Cuentas Pendientes (Crédito)")
    cuentas = pd.read_sql_query("SELECT * FROM ventas WHERE metodo = 'Crédito'", conn)
    if not cuentas.empty:
        st.dataframe(cuentas)
    else:
        st.info("No hay cuentas pendientes")
