import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
import re
import os

# --- 1. CAPA DE DATOS & DB ---

def conectar_db(db_path=None):
    """
    Conecta a la base de datos. Pasa db_path=":memory:" para pruebas unitarias aisladas.
    """
    if db_path is None:
        ruta_volumen = '/app/data/metropoli.db'
        db_path = ruta_volumen if os.path.exists('/app/data') else 'metropoli.db'
    
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def inicializar_tablas(conn):
    with conn:
        conn.execute('CREATE TABLE IF NOT EXISTS productos (id INTEGER PRIMARY KEY, nombre TEXT, precio REAL, stock INTEGER)')
        conn.execute('CREATE TABLE IF NOT EXISTS ventas (id INTEGER PRIMARY KEY, fecha TEXT, total REAL, metodo TEXT, detalle TEXT, cliente TEXT, reporte_id INTEGER)')
        conn.execute('CREATE TABLE IF NOT EXISTS históricos_reportes (id INTEGER PRIMARY KEY AUTOINCREMENT, fecha_cierre TEXT, total_caja REAL)')

# --- 2. LÓGICA DE NEGOCIO (TESTEABLE) ---

def parsear_detalle_items(detalle_str):
    """Extrae (nombre, cantidad) usando Regex para soportar paréntesis dentro del nombre del producto."""
    items = []
    if not detalle_str:
        return items
    # Busca la última ocurrencia de (número) al final de cada ítem separado por coma
    patron = re.compile(r"^(.*?)\((\d+)\)$")
    for parte in str(detalle_str).split(", "):
        match = patron.match(parte.strip())
        if match:
            nombre = match.group(1).strip()
            cantidad = int(match.group(2))
            items.append((nombre, cantidad))
    return items

def obtener_conteo_productos(df):
    conteo = {}
    if df.empty or 'detalle' not in df.columns:
        return pd.DataFrame(columns=['Producto', 'Cant.'])
        
    for detalle in df['detalle'].dropna():
        for nombre, cantidad in parsear_detalle_items(detalle):
            conteo[nombre] = conteo.get(nombre, 0) + cantidad
            
    if not conteo:
        return pd.DataFrame(columns=['Producto', 'Cant.'])
    
    return pd.DataFrame(list(conteo.items()), columns=['Producto', 'Cant.']).sort_values(by='Cant.', ascending=False)

def unificar_detalles_texto(lista_detalles):
    conteo = {}
    for detalle in lista_detalles:
        for nombre, cantidad in parsear_detalle_items(detalle):
            conteo[nombre] = conteo.get(nombre, 0) + cantidad
    return ", ".join([f"{prod}({cant})" for prod, cant in conteo.items()])

def registrar_venta(conn, carrito, metodo, cliente=""):
    """Procesa una venta y descuenta el stock dentro de una transacción segura."""
    monto_total = sum(item['precio'] * item['cantidad'] for item in carrito.values())
    detalle_str = ", ".join([f"{v['nombre']}({v['cantidad']})" for v in carrito.values()])
    rep_id_inicial = -1 if metodo == "Crédito" else None
    
    with conn:
        conn.execute(
            "INSERT INTO ventas (fecha, total, metodo, detalle, cliente, reporte_id) VALUES (?,?,?,?,?,?)",
            (datetime.now().strftime("%Y-%m-%d %H:%M"), monto_total, metodo, detalle_str, cliente, rep_id_inicial)
        )
        for pid, item in carrito.items():
            conn.execute("UPDATE productos SET stock = stock - ? WHERE id = ?", (item['cantidad'], int(pid)))
    return True

def saldar_deuda_cliente(conn, cliente, monto_total, metodo_pago, detalles_viejos):
    detalle_unificado = unificar_detalles_texto(detalles_viejos)
    fecha = f"{datetime.now().strftime('%Y-%m-%d %H:%M')} (Saldado)"
    
    with conn:
        conn.execute(
            "INSERT INTO ventas (fecha, total, metodo, detalle, cliente, reporte_id) VALUES (?, ?, ?, ?, ?, NULL)",
            (fecha, monto_total, metodo_pago, detalle_unificado, cliente)
        )
        conn.execute("UPDATE ventas SET reporte_id = -2 WHERE cliente = ? AND metodo = 'Crédito' AND reporte_id = -1", (cliente,))

def registrar_consumo_interno(conn, cliente, monto_total, detalles_viejos):
    detalle_unificado = unificar_detalles_texto(detalles_viejos)
    fecha = f"{datetime.now().strftime('%Y-%m-%d %H:%M')} (Consumo)"
    
    with conn:
        conn.execute(
            "INSERT INTO ventas (fecha, total, metodo, detalle, cliente, reporte_id) VALUES (?, ?, ?, ?, ?, -2)",
            (fecha, monto_total, "Consumo Interno", detalle_unificado, cliente)
        )
        conn.execute("UPDATE ventas SET reporte_id = -2 WHERE cliente = ? AND metodo = 'Crédito' AND reporte_id = -1", (cliente,))

def realizar_cierre_caja(conn, total_caja):
    with conn:
        cursor = conn.execute("INSERT INTO históricos_reportes (fecha_cierre, total_caja) VALUES (?,?)", 
                              (datetime.now().strftime("%Y-%m-%d %H:%M"), total_caja))
        ultimo_id = cursor.lastrowid
        conn.execute("UPDATE ventas SET reporte_id = ? WHERE reporte_id IS NULL", (ultimo_id,))

# --- 3. CONFIGURACIÓN Y ESTILOS STREAMLIT ---

st.set_page_config(page_title="Metropoli Cafe", page_icon="🏀", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #134971 !important; }
    [data-testid="stSidebar"] { background-image: url("https://github.com/Trycak/Metropoli-app/blob/main/Back%20large.png?raw=true"); background-size: cover; }
    h1, h2, h3, p, span, label, .stMarkdown { color: white !important; text-align: center; }
    
    div.stButton > button {
        -webkit-appearance: none !important;
        appearance: none !important;
        background-color: #ff6b1d !important; 
        color: #000000 !important;           
        border: 2px solid #d15615 !important; 
        border-radius: 12px !important;
        font-weight: bold !important;
        font-size: 18px !important;
        height: 115px !important; 
        width: 100% !important; 
        margin-bottom: 10px !important;
        display: block !important;
        white-space: pre-line !important;
    }

    div.stButton > button:disabled {
        background-color: #000000 !important;
        color: #444444 !important;
        border: 2px solid #333333 !important;
        opacity: 1 !important;
    }
    
    .total-carrito {
        background-color: rgba(255, 107, 29, 0.15);
        padding: 20px;
        border-radius: 15px;
        border: 2px solid #ff6b1d;
        margin: 15px 0px;
        text-align: center;
    }
    .info-caja {
        background-color: rgba(255, 255, 255, 0.1);
        padding: 15px;
        border-radius: 10px;
        border: 1px solid #ff6b1d;
        margin-bottom: 20px;
    }
    </style>
    """, unsafe_allow_html=True)

# MODO PRUEBAS: Permite alternar a DB en memoria desde la barra lateral si se activa un checkbox
if "modo_test" not in st.session_state:
    st.session_state.modo_test = False

st.sidebar.image("https://github.com/Trycak/Metropoli-app/blob/main/Logo%20Metropoli.png?raw=true", use_container_width=True)

# Toggle para pruebas en tiempo de ejecución
modo_test = st.sidebar.checkbox("🧪 Modo Pruebas (Memoria RAM)")
if modo_test != st.session_state.modo_test:
    st.session_state.modo_test = modo_test
    if "conn" in st.session_state:
        st.session_state.conn.close()
        del st.session_state.conn

if "conn" not in st.session_state:
    st.session_state.conn = conectar_db(":memory:" if st.session_state.modo_test else None)
    inicializar_tablas(st.session_state.conn)

conn = st.session_state.conn

# --- 4. NAVEGACIÓN Y VISTAS ---

menu = ["🛒 Ventas", "📦 Inventario", "📊 Productos Vendidos", "📝 Cuentas por Cobrar", "📋 Reportes"]
choice = st.sidebar.radio("Nav", menu, label_visibility="collapsed")

if choice == "🛒 Ventas":
    if 'carrito' not in st.session_state: 
        st.session_state.carrito = {}
        
    col_prods, col_cart = st.columns([2, 1])
    
    with col_prods:
        st.subheader("🛒 Productos Disponibles")
        prods = pd.read_sql_query("SELECT * FROM productos ORDER BY nombre ASC", conn)
        grid = st.columns(3)
        for i, row in prods.iterrows():
            with grid[i % 3]:
                label_stock = f"({int(row['stock'])})" if row['stock'] > 0 else "(AGOTADO)"
                texto_final = f"{row['nombre']} {label_stock}\n₡{int(row['precio'])}"
                if st.button(texto_final, key=f"p_{row['id']}", disabled=row['stock'] <= 0):
                    pid = str(row['id'])
                    if pid in st.session_state.carrito: 
                        st.session_state.carrito[pid]['cantidad'] += 1
                    else: 
                        st.session_state.carrito[pid] = {'nombre': row['nombre'], 'precio': row['precio'], 'cantidad': 1}
                    st.rerun()

    with col_cart:
        st.subheader("🛒 Carrito")
        if st.session_state.carrito:
            total_v = 0
            for pid, item in list(st.session_state.carrito.items()):
                sub = item['precio'] * item['cantidad']
                total_v += sub
                c1, c2 = st.columns([5, 1])
                c1.write(f"**{item['nombre']} x{item['cantidad']}** (₡{int(sub)})")
                if c2.button("X", key=f"del_{pid}"): 
                    del st.session_state.carrito[pid]
                    st.rerun()
                    
            st.markdown(f"""<div class="total-carrito"><p style="margin:0; font-size:16px; color:#ff6b1d;">MONTO A PAGAR</p><h1 style="margin:0; font-size:45px; color:white;">₡{int(total_v)}</h1></div>""", unsafe_allow_html=True)
            st.divider()
            
            metodo = st.selectbox("Forma de Pago", ["Efectivo", "SINPE Móvil", "Crédito"])
            cliente_n = ""
            if metodo == "Crédito":
                clientes_db = pd.read_sql_query("SELECT DISTINCT cliente FROM ventas WHERE metodo = 'Crédito' AND reporte_id = -1 AND cliente != ''", conn)['cliente'].tolist()
                opc = st.selectbox("Seleccionar Cliente", ["-- Nuevo --"] + clientes_db)
                cliente_n = st.text_input("Nombre del Cliente") if opc == "-- Nuevo --" else opc
                
            if st.button("✅ FINALIZAR VENTA", use_container_width=True):
                if metodo == "Crédito" and not cliente_n.strip(): 
                    st.error("Falta ingresar el nombre del cliente")
                else:
                    registrar_venta(conn, st.session_state.carrito, metodo, cliente_n)
                    st.session_state.carrito = {}
                    st.success("¡Venta Lista!")
                    st.rerun()
        else: 
            st.info("El carrito está vacío")

elif choice == "📦 Inventario":
    st.header("📦 Gestión de Inventario")
    df_inv = pd.read_sql_query("SELECT id, nombre, precio, stock FROM productos ORDER BY nombre ASC", conn)
    df_inv['Eliminar'] = False
    
    _, mid, _ = st.columns([1, 6, 1])
    with mid:
        df_ed = st.data_editor(df_inv, column_config={"id": None, "Eliminar": st.column_config.CheckboxColumn("¿Borrar?", default=False)}, hide_index=True, use_container_width=True)
        c_inv1, c_inv2 = st.columns(2)
        
        if c_inv1.button("💾 Guardar Cambios", use_container_width=True):
            with conn:
                for _, r in df_ed.iterrows(): 
                    conn.execute("UPDATE productos SET nombre=?, precio=?, stock=? WHERE id=?", (r['nombre'], r['precio'], r['stock'], int(r['id'])))
            st.success("Inventario Actualizado")
            st.rerun()
            
        if c_inv2.button("🗑️ Eliminar Seleccionados", use_container_width=True):
            with conn:
                for _, r in df_ed[df_ed['Eliminar']].iterrows(): 
                    conn.execute("DELETE FROM productos WHERE id = ?", (int(r['id']),))
            st.rerun()  # Corregido de r.rerun() a st.rerun()
            
        with st.expander("➕ AGREGAR NUEVO PRODUCTO"):
            with st.form("n_p", clear_on_submit=True):
                n = st.text_input("Nombre")
                p = st.number_input("Precio", min_value=0.0)
                s = st.number_input("Stock Inicial", min_value=0)
                if st.form_submit_button("Añadir"):
                    if n.strip():
                        with conn:
                            conn.execute("INSERT INTO productos (nombre, precio, stock) VALUES (?,?,?)", (n, p, s))
                        st.rerun()
                    else:
                        st.error("El nombre no puede estar vacío.")

elif choice == "📊 Productos Vendidos":
    st.header("📊 Ranking de Productos Vendidos")
    df_v = pd.read_sql_query("SELECT detalle FROM ventas WHERE reporte_id IS NULL", conn)
    if not df_v.empty:
        df_res = obtener_conteo_productos(df_v)
        st.dataframe(df_res, hide_index=True, use_container_width=True)
    else: 
        st.info("No hay ventas en este turno.")

elif choice == "📝 Cuentas por Cobrar":
    st.header("📝 Gestión de Créditos")
    df_cc = pd.read_sql_query("SELECT cliente, SUM(total) as deuda FROM ventas WHERE metodo = 'Crédito' AND reporte_id = -1 GROUP BY cliente", conn)
    
    if not df_cc.empty:
        col_lista, col_detalle = st.columns([1, 2])
        with col_lista:
            cl_paga = st.selectbox("Seleccionar Cliente:", df_cc['cliente'].tolist())
            monto_resumen = df_cc[df_cc['cliente'] == cl_paga]['deuda'].values[0]
            st.markdown(f"<div class='info-caja'><h4>Total Deuda:<br>₡{int(monto_resumen)}</h4></div>", unsafe_allow_html=True)
            
        with col_detalle:
            df_det = pd.read_sql_query("SELECT id, fecha, detalle, total FROM ventas WHERE cliente = ? AND metodo = 'Crédito' AND reporte_id = -1", conn, params=(cl_paga,))
            df_det['Borrar?'] = False
            df_det_ed = st.data_editor(df_det, column_config={"id": None}, hide_index=True, use_container_width=True)
            
            c_c1, c_c2 = st.columns(2)
            if c_c1.button("💾 Guardar Cambios", use_container_width=True):
                with conn:
                    for _, r in df_det_ed.iterrows(): 
                        conn.execute("UPDATE ventas SET detalle=?, total=? WHERE id=?", (r['detalle'], r['total'], int(r['id'])))
                st.rerun()
                
            if c_c2.button("🗑️ Eliminar Notas", use_container_width=True):
                with conn:
                    for _, row in df_det_ed[df_det_ed['Borrar?']].iterrows(): 
                        conn.execute("DELETE FROM ventas WHERE id = ?", (int(row['id']),))
                st.rerun()
                
            st.divider()
            
            if 'confirmar_pago' not in st.session_state: st.session_state.confirmar_pago = False
            if 'confirmar_consumo' not in st.session_state: st.session_state.confirmar_consumo = False
            if 'cliente_actual' not in st.session_state: st.session_state.cliente_actual = cl_paga

            if st.session_state.cliente_actual != cl_paga:
                st.session_state.confirmar_pago = False
                st.session_state.confirmar_consumo = False
                st.session_state.cliente_actual = cl_paga

            c_pago1, c_pago2 = st.columns(2)
            with c_pago1:
                metodo_p = st.selectbox("Pago por:", ["Efectivo", "SINPE Móvil"])
                if st.button(f"Saldar Deuda (₡{int(monto_resumen)})", use_container_width=True):
                    st.session_state.confirmar_pago = True
                    st.session_state.confirmar_consumo = False
            with c_pago2:
                st.write("")
                st.write("")
                if st.button("🎁 Registrar como Consumo Interno", use_container_width=True):
                    st.session_state.confirmar_consumo = True
                    st.session_state.confirmar_pago = False

            if st.session_state.confirmar_pago:
                st.warning(f"⚠️ ¿Estás seguro de cancelar con **{metodo_p}** la cuenta de **{cl_paga}** por ₡{int(monto_resumen)}?")
                cc1, cc2 = st.columns(2)
                if cc1.button("❌ NO, CANCELAR", key="btn_no_pago", use_container_width=True):
                    st.session_state.confirmar_pago = False
                    st.rerun()
                if cc2.button("✅ SÍ, CONFIRMAR PAGO", key="btn_si_pago", use_container_width=True):
                    saldar_deuda_cliente(conn, cl_paga, monto_resumen, metodo_p, df_det['detalle'].tolist())
                    st.session_state.confirmar_pago = False
                    st.success(f"¡Cuenta de {cl_paga} unificada y saldada con éxito!")
                    st.rerun()

            if st.session_state.confirmar_consumo:
                st.warning(f"⚠️ ¿Estás seguro de registrar como **Consumo Interno** la cuenta de **{cl_paga}**?")
                cc3, cc4 = st.columns(2)
                if cc3.button("❌ NO, CANCELAR", key="btn_no_consumo", use_container_width=True):
                    st.session_state.confirmar_consumo = False
                    st.rerun()
                if cc4.button("✅ SÍ, CONFIRMAR CONSUMO", key="btn_si_consumo", use_container_width=True):
                    registrar_consumo_interno(conn, cl_paga, monto_resumen, df_det['detalle'].tolist())
                    st.session_state.confirmar_consumo = False
                    st.success(f"Cuenta de {cl_paga} registrada como consumo interno.")
                    st.rerun()
    else: 
        st.info("Sin deudas pendientes.")

elif choice == "📋 Reportes":
    tab_actual, tab_historico = st.tabs(["🔴 Turno Actual", "💾 Historial de Cierres"])
    
    with tab_actual:
        st.header("Ventas del Periodo Activo")
        df_p = pd.read_sql_query("SELECT id, fecha, total, metodo, detalle, cliente FROM ventas WHERE reporte_id IS NULL", conn)
        if not df_p.empty:
            st.dataframe(df_p, hide_index=True, use_container_width=True)
            t_caja = df_p[df_p['metodo'].isin(['Efectivo', 'SINPE Móvil'])]['total'].sum()
            st.subheader(f"Dinero en Caja Real: ₡{int(t_caja)}")
            
            if st.button("🔴 CERRAR CAJA Y ARCHIVAR", use_container_width=True):
                realizar_cierre_caja(conn, t_caja)
                st.success("Caja Cerrada y Guardada en el Historial")
                st.rerun()
        else: 
            st.info("No hay ventas en el turno actual.")

    with tab_historico:
        st.header("Consulta de Cierres Pasados")
        historicos = pd.read_sql_query("SELECT * FROM históricos_reportes ORDER BY id DESC", conn)
        if not historicos.empty:
            opciones_cierre = {f"ID: {r['id']} | Fecha: {r['fecha_cierre']} | Total: ₡{int(r['total_caja'])}": r['id'] for _, r in historicos.iterrows()}
            seleccion = st.selectbox("Seleccione un cierre para ver detalle:", list(opciones_cierre.keys()))
            id_cierre = opciones_cierre[seleccion]
            
            df_hist = pd.read_sql_query("SELECT fecha, total, metodo, detalle, cliente FROM ventas WHERE reporte_id = ?", conn, params=(id_cierre,))
            st.markdown(f"<div class='info-caja'><h3>Reporte #{id_cierre}</h3></div>", unsafe_allow_html=True)
            st.dataframe(df_hist, hide_index=True, use_container_width=True)
            
            st.subheader("Ranking de Productos en este Cierre")
            df_prod_hist = obtener_conteo_productos(df_hist)
            st.dataframe(df_prod_hist, hide_index=True, use_container_width=True)
        else:
            st.info("Aún no hay reportes cerrados en el historial.")
