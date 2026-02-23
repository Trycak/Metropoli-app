# --- SECCIÓN INVENTARIO ---
elif choice == "📦 Inventario":
    st.header("Gestión de Inventario")
    tab1, tab2, tab3 = st.tabs(["📋 Lista Actual", "➕ Nuevo Producto", "✏️ Editar / Eliminar"])
    
    with tab1:
        # Forzamos la lectura fresca de la base de datos
        df = pd.read_sql_query("SELECT id, nombre, precio, stock FROM productos ORDER BY nombre ASC", conn)
        st.dataframe(df, use_container_width=True, hide_index=True)
    
    with tab2:
        with st.form("nuevo_p", clear_on_submit=True):
            n = st.text_input("Nombre")
            p = st.number_input("Precio", min_value=0, step=1)
            s = st.number_input("Stock Inicial", min_value=0, step=1)
            if st.form_submit_button("Guardar"):
                if n:
                    c.execute("INSERT INTO productos (nombre, precio, stock) VALUES (?,?,?)", (n, p, s))
                    conn.commit()
                    st.success(f"Producto {n} guardado")
                    st.rerun()
                else:
                    st.error("Poner un nombre")

    with tab3:
        # Volvemos a consultar para tener los datos más recientes
        prods_list = pd.read_sql_query("SELECT * FROM productos ORDER BY nombre ASC", conn)
        if not prods_list.empty:
            seleccionado = st.selectbox("Seleccione producto para modificar:", prods_list['nombre'].tolist())
            datos_p = prods_list[prods_list['nombre'] == seleccionado].iloc[0]
            
            # Usamos columnas sin formulario para que el botón responda mejor
            col_edit1, col_edit2 = st.columns(2)
            with col_edit1:
                nuevo_n = st.text_input("Nombre del producto", value=datos_p['nombre'], key="edit_nom")
                nuevo_p = st.number_input("Precio actual", value=float(datos_p['precio']), step=1.0, key="edit_pre")
            with col_edit2:
                nuevo_s = st.number_input("Stock actual", value=int(datos_p['stock']), step=1, key="edit_sto")
            
            st.write("") # Espacio
            col_btn1, col_btn2 = st.columns(2)
            
            with col_btn1:
                if st.button("💾 ACTUALIZAR AHORA", type="primary"):
                    c.execute("UPDATE productos SET nombre=?, precio=?, stock=? WHERE id=?", 
                              (nuevo_n, nuevo_p, nuevo_s, int(datos_p['id'])))
                    conn.commit()
                    st.success(f"¡{nuevo_n} actualizado!")
                    st.rerun()
            
            with col_btn2:
                confirmar_del = st.checkbox("Confirmar eliminación definitiva")
                if st.button("🗑️ ELIMINAR PRODUCTO"):
                    if confirmar_del:
                        c.execute("DELETE FROM productos WHERE id=?", (int(datos_p['id']),))
                        conn.commit()
                        st.warning("Producto eliminado")
                        st.rerun()
                    else:
                        st.info("Debe marcar la casilla para eliminar")
        else:
            st.info("No hay productos para editar.")
