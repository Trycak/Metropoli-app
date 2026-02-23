import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
import io

# 1. CONFIGURACIÓN DE PÁGINA Y ESTILO VISUAL "HAIL MARY"
st.set_page_config(page_title="Metropoli Basket Academy", page_icon="🏀", layout="wide")

# Definición de colores originales
ACCENT_COLOR = '#279aa0'
HOVER_COLOR = '#1a7478'

st.markdown(f"""
    <style>
    /* Fondo general de la aplicación */
    .stApp {{
        background-color: #f8fafc;
    }}
    
    /* Sidebar Estilo MBA */
    [data-testid="stSidebar"] {{
        background-color: {ACCENT_COLOR};
    }}
    [data-testid="stSidebar"] * {{
        color: white !important;
    }}
    [data-testid="stSidebar"] .stRadio label {{
        background-color: transparent !important;
        padding: 10px;
        border-radius: 10px;
    }}
    
    /* Tarjetas de Producto Estilizadas */
    .product-card {{
        background-color: white;
        padding: 20px;
        border-radius: 15px;
        border-left: 6px solid {ACCENT_COLOR};
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        margin-bottom: 10px;
        transition: transform 0.2s;
    }}
    .product-card:hover {{
        transform: translateY(-3px);
        box-shadow: 0 8px 15px rgba(0,0,0,0.1);
    }}
    
    .price-badge {{
        color: {ACCENT_COLOR};
        font-weight: bold;
        font-size: 1.3rem;
    }}

    /* Botones de Streamlit personalizados */
    .stButton>button {{
        width: 100%;
        border-radius: 10px;
        background-color: {ACCENT_COLOR};
        color: white;
        font-weight: bold;
        border: none;
        height: 3.5em;
        transition: 0.3s;
    }}
    .stButton>button:hover {{
        background-color: {HOVER_COLOR};
        color: white;
        border: none;
    }}
    
    /* Estilo para el contenedor del carrito */
    .cart-container {{
        background-color: white;
        padding: 20px;
        border-radius: 15px;
        border: 1px solid #e2e8f0;
    }}
    </style>
    """, unsafe_allow_html=True)

# 2. CONEXIÓN A BASE DE DATOS
def conectar_db():
    conn = sqlite3.connect('metropoli.db', check_same_thread=False)
    return conn

conn = conectar_db()
c = conn.cursor()

# Crear tablas si no existen
c.execute('CREATE TABLE IF NOT EXISTS productos (id INTEGER PRIMARY KEY, nombre TEXT, precio REAL, stock INTEGER)')
try:
    c.execute('ALTER TABLE ventas ADD COLUMN reporte_id INTEGER')
except:
    pass
c.execute('CREATE TABLE IF NOT EXISTS ventas (id INTEGER PRIMARY KEY, fecha TEXT, total REAL, metodo TEXT, detalle TEXT, cliente TEXT, reporte_id INTEGER)')
c.execute('CREATE TABLE IF NOT EXISTS históricos_reportes (id INTEGER PRIMARY KEY AUTOINCREMENT, fecha_cierre TEXT, total_caja REAL)')
conn.commit()

# Función auxiliar para procesar conteo de artículos
def contar_articulos(dataframe):
    conteo = {}
    for d in dataframe['detalle']:
        partes = d.split(", ")
        for p in partes:
            if "(" in p and ")" in p:
                try:
                    nombre_item = p.split("(")[0]
                    cant_item = int(p.split("(")[1].replace(")", ""))
                    conteo[nombre_item] = conteo.get(nombre_item, 0) + cant_item
                except:
                    continue
    return conteo

# 3. MENÚ LATERAL
with st.sidebar:
    st.markdown("## 🏀 MBA Academy")
    st.write("---")
    menu = st.radio("Navegación", ["🛒 Ventas", "📦 Inventario", "📝 Cuentas por Cobrar", "📊 Reporte"])
    st.write("---")
    st.caption("MBA Café POS v1.1")

# --- SECCIÓN VENTAS ---
if menu == "🛒 Ventas":
    if 'carrito' not in st.session_state:
        st.session_state.carrito = {}
    
    col_izq, col_der = st.columns([2, 1])
    
    with col_izq:
        st.markdown(f"<h2 style='color:{ACCENT_COLOR};'>Punto de Venta</h2>", unsafe_allow_html=True)
        busqueda = st.text_input("🔍 Buscar productos...", placeholder="Nombre del producto...")
        
        # Consulta de productos
        query = f"SELECT * FROM productos WHERE stock > 0 AND nombre LIKE '%{busqueda}%' ORDER BY nombre ASC"
        prods = pd.read_sql_query(query, conn)
        
        if prods.empty:
            st.warning("No hay productos disponibles con ese nombre.")
        else:
            # Grid de 2 columnas para los productos
            p_cols = st.columns(2)
            for i, row in prods.iterrows():
                with p_cols[i % 2]:
                    st.markdown(f"""
                        <div class="product-card">
                            <div style="display: flex; justify-content: space-between; align-items: center;">
                                <div>
                                    <h4 style="margin:0;">{row['nombre']}</h4>
                                    <small style="color:gray;">Stock: {row['stock']} unidades</small>
                                </div>
                                <div class="price-badge">₡{int(row['precio']):,}</div>
                            </div>
                        </div>
                    """, unsafe_allow_html=True)
                    if st.button(f"Añadir {row['nombre']}", key=f"add_{row['id']}"):
                        pid = str(row['id'])
                        if pid in st.session_state.carrito:
                            st.session_state.carrito[pid]['cantidad'] += 1
                        else:
                            st.session_state.carrito[pid] = {'nombre': row['nombre'], 'precio': row['precio'], 'cantidad': 1}
                        st.toast(f"✅ {row['nombre']} en carrito")
                        st.rerun()

    with col_der:
        st.markdown("<div class=" + "'cart-container'" + ">", unsafe_allow_html=True)
        st.subheader("🛒 Carrito Actual")
        
        if st.session_state.carrito:
            total_venta = 0
            for pid, item in list(st.session_state.carrito.items()):
                subtotal = item['precio'] * item['cantidad']
                total_venta += subtotal
                c1, c2 = st.columns([3, 1])
                c1.write(f"**{item['nombre']}** (x{item['cantidad']})")
                c2.write(f"₡{int(subtotal):,}")
            
            st.divider()
            st.markdown(f"<h2 style='text-align:right; color:#1e293b;'>Total: ₡{int(total_venta):,}</h2>", unsafe_allow_html=True)
            
            metodo = st.selectbox("Método de Pago", ["Efectivo", "SINPE Móvil", "Crédito"])
            cliente = ""
            
            if metodo == "Crédito":
                clientes_df = pd.read_sql_query("SELECT DISTINCT cliente FROM ventas WHERE metodo = 'Crédito'", conn)
                clientes_previos = clientes_df['cliente'].tolist() if not clientes_df.empty else []
                cliente = st.selectbox("Cliente:", ["-- Nuevo --"] + clientes_previos)
                if cliente == "-- Nuevo --":
                    cliente = st.text_input("Nombre del Cliente")
            
            if st.button("🚀 FINALIZAR VENTA", type="primary"):
                if metodo == "Crédito" and not cliente:
                    st.error("Por favor, ingrese el nombre del cliente para el crédito.")
                else:
                    fecha_actual = datetime.now().strftime("%Y-%m-%d %H:%M")
                    detalle_str = ", ".join([f"{i['nombre']}({i['cantidad']})" for i in st.session_state.carrito.values()])
                    
                    # 1. Insertar Venta
                    c.execute("INSERT INTO ventas (fecha, total, metodo, detalle, cliente, reporte_id) VALUES (?,?,?,?,?, NULL)", 
                              (fecha_actual, total_venta, metodo, detalle_str, cliente if cliente else ""))
                    
                    # 2. Descontar Stock
                    for pid, item in st.session_state.carrito.items():
                        c.execute("UPDATE productos SET stock = stock - ? WHERE id = ?", (item['cantidad'], int(pid)))
                    
                    conn.commit()
                    st.session_state.carrito = {}
                    st.balloons()
                    st.success("¡Venta procesada con éxito!")
                    st.rerun()
            
            if st.button("🗑️ Vaciar"):
                st.session_state.carrito = {}
                st.rerun()
        else:
            st.info("Agregue productos a la izquierda")
        st.markdown("</div>", unsafe_allow_html=True)

# --- SECCIÓN INVENTARIO ---
elif menu == "📦 Inventario":
    st.header("📦 Gestión de Inventario")
    t1, t2, t3 = st.tabs(["📋 Ver Todo", "➕ Nuevo Producto", "✏️ Editar / Borrar"])
    
    with t1:
        df_inv = pd.read_sql_query("SELECT id, nombre, precio, stock FROM productos ORDER BY nombre ASC", conn)
        st.dataframe(df_inv, use_container_width=True, hide_index=True)
    
    with t2:
        with st.form("form_nuevo"):
            st.write("### Datos del Producto")
            nombre_n = st.text_input("Nombre")
            precio_n = st.number_input("Precio (₡)", min_value=0)
            stock_n = st.number_input("Stock Inicial", min_value=0)
            if st.form_submit_button("Guardar"):
                c.execute("INSERT INTO productos (nombre, precio, stock) VALUES (?,?,?)", (nombre_n, precio_n, stock_n))
                conn.commit()
                st.success("Producto creado")
                st.rerun()

    with t3:
        lista_p = pd.read_sql_query("SELECT * FROM productos ORDER BY nombre ASC", conn)
        if not lista_p.empty:
            sel_p = st.selectbox("Elegir producto:", lista_p['nombre'].tolist())
            datos_sel = lista_p[lista_p['nombre'] == sel_p].iloc[0]
            with st.form("form_edit"):
                ed_nombre = st.text_input("Nombre", value=datos_sel['nombre'])
                ed_precio = st.number_input("Precio", value=float(datos_sel['precio']))
                ed_stock = st.number_input("Stock", value=int(datos_sel['stock']))
                col_btn1, col_btn2 = st.columns(2)
                if col_btn1.form_submit_button("Actualizar"):
                    c.execute("UPDATE productos SET nombre=?, precio=?, stock=? WHERE id=?", (ed_nombre, ed_precio, ed_stock, datos_sel['id']))
                    conn.commit(); st.rerun()
                if col_btn2.form_submit_button("Eliminar"):
                    c.execute("DELETE FROM productos WHERE id=?", (datos_sel['id'],))
                    conn.commit(); st.rerun()

# --- SECCIÓN CUENTAS POR COBRAR ---
elif menu == "📝 Cuentas por Cobrar":
    st.header("📝 Cuentas Pendientes")
    cuentas_df = pd.read_sql_query("SELECT * FROM ventas WHERE metodo = 'Crédito' ORDER BY id DESC", conn)
    if not cuentas_df.empty:
        res_cuentas = cuentas_df.groupby('cliente')['total'].sum().reset_index()
        st.table(res_cuentas)
        c_sel = st.selectbox("Seleccione Cliente que paga:", res_cuentas['cliente'].tolist())
        deuda = res_cuentas[res_cuentas['cliente'] == c_sel]['total'].sum()
        
        if st.button(f"Registrar Pago de ₡{int(deuda):,}"):
            fecha_pago = datetime.now().strftime("%Y-%m-%d %H:%M")
            c.execute("UPDATE ventas SET metodo = 'Saldado', fecha = ? WHERE cliente = ? AND metodo = 'Crédito'", 
                      (f"{fecha_pago} (Pagado)", c_sel))
            conn.commit()
            st.success("¡Deuda saldada!")
            st.rerun()
    else:
        st.info("No hay deudas activas.")

# --- SECCIÓN REPORTE ---
elif menu == "📊 Reporte":
    st.header("📊 Reportes y Cierres")
    tab_a, tab_h = st.tabs(["📄 Turno Abierto", "📜 Historial"])

    with tab_a:
        df_hoy = pd.read_sql_query("SELECT * FROM ventas WHERE reporte_id IS NULL ORDER BY id DESC", conn)
        if not df_hoy.empty:
            caja_actual = df_hoy[df_hoy['metodo'] != 'Crédito']['total'].sum()
            st.metric("Efectivo/SINPE en Caja", f"₡{int(caja_actual):,}")
            
            st.subheader("Ventas por Producto")
            conteo_hoy = contar_articulos(df_hoy)
            if conteo_hoy:
                df_c_hoy = pd.DataFrame(list(conteo_hoy.items()), columns=['Item', 'Cant']).sort_values(by='Cant', ascending=False)
                st.table(df_c_hoy)

            if st.button("🔴 CERRAR TURNO (Corte de Caja)"):
                f_cierre = datetime.now().strftime("%Y-%m-%d %H:%M")
                c.execute("INSERT INTO históricos_reportes (fecha_cierre, total_caja) VALUES (?,?)", (f_cierre, caja_actual))
                id_nuevo_rep = c.lastrowid
                c.execute("UPDATE ventas SET reporte_id = ? WHERE reporte_id IS NULL", (id_nuevo_rep,))
                conn.commit(); st.success("Cierre completado"); st.rerun()
        else:
            st.info("Sin ventas en el turno actual.")

    with tab_h:
        hist_reps = pd.read_sql_query("SELECT * FROM históricos_reportes ORDER BY id DESC", conn)
        if not hist_reps.empty:
            hist_reps['label'] = "Cierre #" + hist_reps['id'].astype(str) + " - " + hist_reps['fecha_cierre']
            rep_opcion = st.selectbox("Ver reporte anterior:", hist_reps['label'].tolist())
            id_h = int(rep_opcion.split("#")[1].split(" - ")[0])
            
            df_h_detalle = pd.read_sql_query("SELECT * FROM ventas WHERE reporte_id = ?", conn, params=(id_h,))
            st.write(f"### Detalle de Ventas - Cierre #{id_h}")
            st.dataframe(df_h_detalle[['fecha', 'total', 'metodo', 'detalle']], use_container_width=True)
            
            # Exportación Excel
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                df_h_detalle.to_excel(writer, index=False)
            st.download_button("📥 Descargar Reporte Excel", data=buffer.getvalue(), file_name=f"Reporte_MBA_{id_h}.xlsx")
        else:
            st.write("No hay cierres previos registrados.")
