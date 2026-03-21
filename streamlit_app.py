import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
import io
import os

# 1. Configuración de la página
st.set_page_config(page_title="Metropoli Cafe", page_icon="🏀", layout="wide")

# 2. Conexión a Base de Datos (AJUSTADA PARA RAILWAY)
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

# --- ESTILOS VISUALES PERSONALIZADOS ---
st.markdown("""
    <style>
    .stApp { background-color: #134971 !important; }
    .stApp::before {
        content: "";
        background-image: url("https://github.com/Trycak/Metropoli-app/blob/main/Logo%20Metropoli%20opacidad.png?raw=true");
        background-repeat: no-repeat; background-attachment: fixed; background-position: center; background-size: 600px;
        position: fixed; top: 0; left: 0; width: 100%; height: 100%; z-index: -1;
    }
    [data-testid="stSidebar"] {
        background-image: url("https://github.com/Trycak/Metropoli-app/blob/main/Back%20large.png?raw=true");
        background-size: cover;
    }
    [data-testid="stSidebar"] [data-testid="stVerticalBlock"] { padding-top: 0rem !important; gap: 0rem !important; }
    [data-testid="stSidebar"] .stRadio > label { display: none !important; }
    [data-testid="stSidebar"] .stRadio div[role="radiogroup"] label {
        background-color: rgba(255, 255, 255, 0.1) !important;
        border-radius: 10px !important; padding: 10px 15px !important; 
        margin-bottom: 6px !important; width: 100% !important;
        border: 1px solid rgba(255,255,255,0.2) !important;
    }
    [data-testid="stSidebar"] .stRadio div[role="radiogroup"] label p {
        color: white !important; font-weight: bold !important; font-size: 18px !important;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.8);
    }
    [data-testid="stSidebar"] [data-testid="stImage"] { padding-top: 10px !important; margin-top: -20px !important; }
    div.stButton > button[key^="p_"] {
        background-color: #28a5a9 !important; color: white !important; border-radius: 12px !important;
        height: 115px !important; width: 100% !important; font-weight: bold !important; font-size: 18px !important;
    }
    .stDataEditor, .stDataFrame { background-color: #134971 !important; border-radius: 10px !important; }
    h1, h2, h3, p, span, label { color: white !important; text-align: center; }
    
    /* Estilo para el Total Resaltado */
    .total-container {
        background-color: rgba(40, 165, 169, 0.3);
        padding: 15px;
        border-radius: 10px;
        border: 1px solid #28a5a9;
        margin: 10px 0px;
    }
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
    if not conteo: return pd.DataFrame()
    return pd.DataFrame(list(conteo.items()), columns=['Producto', 'Cantidad']).sort_values(by='Cantidad', ascending=False)

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
                sub = item['precio'] * item['cantidad']
                total_v += sub
                c1, c2 = st.columns([5, 1])
                c1.write(f"**{item['nombre']} x{item['cantidad']}** (₡{int(sub)})")
                if c2.button("X", key=f"del_{pid}"): del st.session_state.carrito[pid]; st.rerun()
            
            # --- SECCIÓN DEL TOTAL (NUEVA) ---
            st.markdown(f"""
                <div class="total-container">
                    <h3 style="margin:0;">TOTAL A CANCELAR:</h3>
                    <h1 style="margin:0; color: #28a5a9;">₡{int(total_v)}</h1>
                </div>
            """, unsafe_allow_html=True)
            
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

# --- (El resto del código se mantiene igual que tu versión madre) ---
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
        
        c1, c2, c3 = st.columns([1, 1, 1])
        with c1:
            if st.button("💾 Guardar Cambios", use_container_width=True):
                for _, row in df_ed.iterrows(): 
                    c.execute("UPDATE productos SET nombre=?, precio=?, stock=? WHERE id=?", (row['nombre'], row['precio'], row['stock'], int(row['id'])))
                conn.commit(); st.success("Actualizado"); st.rerun()
        with c2:
            st.download_button(label="📥 EXPORTAR CSV", data=to_csv(df_inv.drop(columns=['Eliminar'])), file_name=f"inventario_{datetime.now().strftime('%Y%m%d')}.csv", mime="text/csv", use_container_width=True)
        with c3:
            if st.button("🗑️ ELIMINAR SELECCIONADOS", use_container_width=True):
                seleccionados = df_ed[df_ed['Eliminar'] == True]
                if not seleccionados.empty:
                    for _, row in seleccionados.iterrows():
                        c.execute("DELETE FROM productos WHERE id = ?", (int(row['id']),))
                    conn.commit(); st.success(f"{len(seleccionados)} producto(s) eliminado(s)"); st.rerun()
        
        st.divider()
        with st.expander("➕ Agregar Nuevo Producto"):
            with st.form("new_p", clear_on_submit=True):
                n = st.text_input("Nombre")
                p = st.number_input("Precio", min_value=0)
                s = st.number_input("Stock", min_value=0)
                if st.form_submit_button("Añadir"):
                    if n:
                        c.execute("INSERT INTO productos (nombre, precio, stock) VALUES (?,?,?)", (n,p,s))
                        conn.commit(); st.success(f"{n} guardado."); st.rerun()
                    else: st.error("El nombre es obligatorio")

elif choice == "📊 Productos Vendidos":
    st.header("📊 Resumen de Productos Vendidos")
    df_v = pd.read_sql_query("SELECT detalle FROM ventas WHERE reporte_id IS NULL", conn)
    if not df_v.empty:
        df_res = obtener_conteo_productos(df_v)
        _, mid, _ = st.columns([1, 2, 1])
        with mid:
            st.dataframe(df_res, hide_index=True, use_container_width=True)
            st.download_button(label="📥 EXPORTAR RESUMEN", data=to_csv(df_res), file_name=f"resumen_{datetime.now().strftime('%Y%m%d')}.csv", mime="text/csv", use_container_width=True)
    else: st.info("No hay ventas registradas.")

elif choice == "📝 Cuentas por Cobrar":
    st.header("📝 Gestión de Créditos")
    df_cc = pd.read_sql_query("SELECT cliente, SUM(total) as deuda FROM ventas WHERE metodo = 'Crédito' GROUP BY cliente", conn)
    if not df_cc.empty:
        _, mid, _ = st.columns([1, 2, 1])
        with mid:
            st.dataframe(df_cc, hide_index=True, use_container_width=True,
                         column_config={"cliente": "Cliente", "deuda": st.column_config.NumberColumn("Deuda", format="₡%d")})
            cl_paga = st.selectbox("Cliente:", df_cc['cliente'].tolist())
            monto = df_cc[df_cc['cliente'] == cl_paga]['deuda'].values[0]
            metodo_pago_deuda = st.selectbox("Recibir pago por:", ["Efectivo", "SINPE Móvil"])
            if st.button(f"Saldar Deuda (₡{int(monto)})", use_container_width=True):
                c.execute("UPDATE ventas SET metodo = ?, fecha = ? WHERE cliente = ? AND metodo = 'Crédito'", (metodo_pago_deuda, f"{datetime.now().strftime('%Y-%m-%d %H:%M')} (Saldado)", cl_paga))
                conn.commit(); st.success("Cuenta cancelada"); st.rerun()
    else: st.info("No hay deudas pendientes.")

elif choice == "📋 Reportes":
    st.header("📋 Ventas")
    df_p = pd.read_sql_query("SELECT id, fecha, total, metodo, detalle, cliente FROM ventas WHERE reporte_id IS NULL", conn)
    if not df_p.empty:
        df_p['Eliminar'] = False
        df_p_ed = st.data_editor(df_p, column_config={
            "id": None, "fecha": st.column_config.TextColumn("Fecha", width="small"),
            "total": st.column_config.NumberColumn("Total", format="₡%d", width="small"),
            "metodo": st.column_config.SelectboxColumn("Método", options=["Efectivo", "SINPE Móvil", "Crédito"], width="small"),
            "detalle": st.column_config.TextColumn("Detalle", width="large"),
            "Eliminar": st.column_config.CheckboxColumn("Borrar?", default=False)
        }, hide_index=True, use_container_width=True)
        
        col_r1, col_r2 = st.columns(2)
        with col_r1:
            if st.button("💾 Guardar Cambios en Métodos", use_container_width=True):
                for _, row in df_p_ed.iterrows(): c.execute("UPDATE ventas SET metodo = ? WHERE id = ?", (row['metodo'], int(row['id'])))
                conn.commit(); st.success("Métodos actualizados"); st.rerun()
        with col_r2:
            if st.button("🗑️ ELIMINAR SELECCIONADAS", use_container_width=True):
                ventas_a_borrar = df_p_ed[df_p_ed['Eliminar'] == True]
                for _, v in ventas_a_borrar.iterrows():
                    det = v['detalle'].split(", ")
                    for item in det:
                        if "(" in item:
                            n_prod = item.split("(")[0]; cant = int(item.split("(")[1].replace(")", ""))
                            c.execute("UPDATE productos SET stock = stock + ? WHERE nombre = ?", (cant, n_prod))
                    c.execute("DELETE FROM ventas WHERE id = ?", (int(v['id']),))
                conn.commit(); st.success("Ventas eliminadas"); st.rerun()
        
        st.divider()
        st.download_button(label="📥 EXPORTAR REPORTE CSV", data=to_csv(df_p_ed.drop(columns=['Eliminar'])), file_name=f"reporte_{datetime.now().strftime('%Y%m%d')}.csv", mime="text/csv", use_container_width=True)
        
        if st.button("🔴 CERRAR CAJA", use_container_width=True):
            tot = df_p_ed[(df_p_ed['metodo']!='Crédito') & (df_p_ed['Eliminar']==False)]['total'].sum()
            c.execute("INSERT INTO históricos_reportes (fecha_cierre, total_caja) VALUES (?,?)", (datetime.now().strftime("%Y-%m-%d %H:%M"), tot))
            c.execute("UPDATE ventas SET reporte_id = (SELECT max(id) FROM históricos_reportes) WHERE reporte_id IS NULL")
            conn.commit(); st.rerun()
    else: st.info("No hay ventas registradas.")
