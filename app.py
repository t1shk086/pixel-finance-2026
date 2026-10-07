import streamlit as st
import pandas as pd

# Настройки на страницата
st.set_page_config(page_title="Анализ на Кабели: Продажби и Доставки", layout="wide")

st.title("📊 Единна система за анализ на продажби и доставки на кабели")
st.write("Качете трите таблици (Константи, Продажби, Доставки), за да стартирате пълния количествен, метален и складов анализ.")

# ==========================================
# 1. ЗАРЕЖДАНЕ НА КОНСТАНТИТЕ (МЕРИЛКИТЕ)
# ==========================================
st.sidebar.header("1. Избор на файлове")
constants_file = st.sidebar.file_uploader("Качете файла с мерилките (Excel/CSV)", type=["xlsx", "csv"], key="const_u")

db_metals = None

if constants_file is not None:
    try:
        if constants_file.name.endswith('.csv'):
            df_const = pd.read_csv(constants_file, dtype={'Материал': str, 'Material': str})
        else:
            df_const = pd.read_excel(constants_file, dtype={'Материал': str, 'Material': str})
            
        df_const.columns = df_const.columns.str.strip()
        
        mat_col = 'Материал' if 'Материал' in df_const.columns else ('Material' if 'Material' in df_const.columns else None)
        nf_col = 'NF key' if 'NF key' in df_const.columns else ('NF_key' if 'NF_key' in df_const.columns else None)
        weight_col = 'Structural weight' if 'Structural weight' in df_const.columns else None
        
        if mat_col and nf_col and weight_col:
            df_const['Clean_Material'] = df_const[mat_col].astype(str).str.strip().str.upper()
            df_const['Clean_NF'] = df_const[nf_col].astype(str).str.strip().str.replace('.0', '', regex=False).str.zfill(3)
            df_const['Clean_Weight'] = pd.to_numeric(df_const[weight_col], errors='coerce').fillna(0)
            
            copper = df_const[df_const['Clean_NF'] == '001'][['Clean_Material', 'Clean_Weight']].rename(columns={'Clean_Weight': 'Cu_weight_per_km'})
            aluminum = df_const[df_const['Clean_NF'] == '002'][['Clean_Material', 'Clean_Weight']].rename(columns={'Clean_Weight': 'Al_weight_per_km'})
            
            copper = copper.drop_duplicates(subset=['Clean_Material'])
            aluminum = aluminum.drop_duplicates(subset=['Clean_Material'])
            
            db_metals = pd.merge(copper, aluminum, on='Clean_Material', how='outer').fillna(0)
            st.success("✅ Базата с константи (мерилки) е заредена успешно!")
            
            with st.expander("Преглед на базата данни с константи (Тегла в кг/км)"):
                st.dataframe(db_metals)
        else:
            st.error("❌ Грешка: В константите липсват колони 'Материал', 'NF key' или 'Structural weight'!")
    except Exception as e:
        st.error(f"Грешка при обработката на константите: {e}")
# ==========================================
# 2. ЗАРЕЖДАНЕ НА МЕСЕЧНИТЕ ПРОДАЖБИ
# ==========================================
sales_file = st.sidebar.file_uploader("Качете файла с продажби (Excel/CSV)", type=["xlsx", "csv"], key="sales_u")

final_df = None

if sales_file is not None and db_metals is not None:
    try:
        if sales_file.name.endswith('.csv'):
            df_sales = pd.read_csv(sales_file, dtype=str)
        else:
            df_sales = pd.read_excel(sales_file, dtype=str)
            
        df_sales.columns = df_sales.columns.str.strip()
        
        default_ek = 'САП код' if 'САП код' in df_sales.columns else df_sales.columns[0]
        default_qty = 'Колич.по документ' if 'Колич.по документ' in df_sales.columns else df_sales.columns[0]
        default_wh = 'Склад' if 'Склад' in df_sales.columns else df_sales.columns[0]
        default_to = 'Всичко' if 'Всичко' in df_sales.columns else df_sales.columns[0]
        default_name = 'Материал' if 'Материал' in df_sales.columns else df_sales.columns[0]
        default_client = 'Клиент' if 'Клиент' in df_sales.columns else df_sales.columns[0]
        default_date = 'Дата' if 'Дата' in df_sales.columns else df_sales.columns[0]

        st.write("### 🔍 Настройка на колоните от файла с ПРОДАЖБИ")
        col1, col2, col3, col4, col5 = st.columns(5)
        
        with col1:
            ek_col = st.selectbox("Колона с ЕК Номер (Продажби):", df_sales.columns, index=int(df_sales.columns.get_loc(default_ek)))
            date_col = st.selectbox("Колона с Дата (Продажби):", df_sales.columns, index=int(df_sales.columns.get_loc(default_date)))
        with col2:
            qty_col = st.selectbox("Колона с Количество (Метри):", df_sales.columns, index=int(df_sales.columns.get_loc(default_qty)))
        with col3:
            wh_col = st.selectbox("Колона за Склад (Продажби):", df_sales.columns, index=int(df_sales.columns.get_loc(default_wh)))
        with col4:
            to_col = st.selectbox("Колона за Оборот:", df_sales.columns, index=int(df_sales.columns.get_loc(default_to)))
        with col5:
            name_col = st.selectbox("Колона за Описание на кабела:", df_sales.columns, index=int(df_sales.columns.get_loc(default_name)))
            client_col = st.selectbox("Колона за Име на Клиент:", df_sales.columns, index=int(df_sales.columns.get_loc(default_client)))
            
        df_sales = df_sales[df_sales[ek_col].notna()]
        df_sales = df_sales[~df_sales[ek_col].astype(str).str.contains('Записи:', case=False, na=False)]
        df_sales = df_sales[df_sales[ek_col].astype(str).str.strip() != '']
        
        df_sales['Clean_Material'] = df_sales[ek_col].astype(str).str.strip().str.upper()
        df_sales['Quantity_m'] = pd.to_numeric(df_sales[qty_col], errors='coerce').fillna(0)
        df_sales['Turnover_Clean'] = pd.to_numeric(df_sales[to_col], errors='coerce').fillna(0)
        df_sales['Warehouse_Clean'] = df_sales[wh_col].astype(str).str.strip()
        df_sales['Cable_Name_Clean'] = df_sales[name_col].astype(str).str.strip()
        df_sales['Client_Clean'] = df_sales[client_col].astype(str).str.strip()
        df_sales['Date_Clean'] = df_sales[date_col].astype(str).str.strip()
        
        final_df = pd.merge(df_sales, db_metals, on='Clean_Material', how='left').fillna(0)
        
        final_df['Продадена Мед (Тона)'] = (final_df['Quantity_m'] * final_df['Cu_weight_per_km']) / 1000000
        final_df['Продаден Алуминий (Тона)'] = (final_df['Quantity_m'] * final_df['Al_weight_per_km']) / 1000000
        
        st.write("---")
        st.write("### 📈 Обобщени продажби за периода")
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Общ Оборот", f"{final_df['Turnover_Clean'].sum():,.2f} лв.")
        k2.metric("Общо Мед", f"{final_df['Продадена Мед (Тона)'].sum():.3f} тона")
        k3.metric("Общо Алуминий", f"{final_df['Продаден Алуминий (Тона)'].sum():.3f} тона")
        k4.metric("Общо продадени", f"{final_df['Quantity_m'].sum():,.0f} метра")
        
    except Exception as e:
        st.error(f"Грешка при обработката на файла с продажби: {e}")
# ==========================================
# 3. ЗАРЕЖДАНЕ НА ДОСТАВКИТЕ И КРОС-АНАЛИЗ
# ==========================================
st.sidebar.header("3. Доставки")
deliveries_file = st.sidebar.file_uploader("Качете файла с ДОСТАВКИ (Excel/CSV)", type=["xlsx", "csv"], key="del_u")

if deliveries_file is not None and final_df is not None:
    try:
        if deliveries_file.name.endswith('.csv'):
            df_del = pd.read_csv(deliveries_file, dtype=str)
        else:
            df_del = pd.read_excel(deliveries_file, dtype=str)
            
        df_del.columns = df_del.columns.str.strip()
        
        # Автоматично засичане на база популярни имена
        del_mat_col = [c for c in df_del.columns if any(x in c.lower() for x in ['код', 'сап', 'материал', 'material', 'art'])]
        del_qty_col = [c for c in df_del.columns if any(x in c.lower() for x in ['колич', 'qty', 'доставен', 'к-во'])]
        del_date_col = [c for c in df_del.columns if any(x in c.lower() for x in ['дата', 'date'])]
        del_wh_col = [c for c in df_del.columns if any(x in c.lower() for x in ['склад', 'wh', 'warehouse'])]
        
        st.write("---")
        st.write("### 🔍 Настройка на колоните от файла с ДОСТАВКИ")
        d_col1, d_col2, d_col3, d_col4 = st.columns(4)
        
        with d_col1:
            d_m = st.selectbox("Колона с ЕК/САП Код (Доставки):", df_del.columns, index=df_del.columns.get_loc(del_mat_col[0]) if del_mat_col else 0)
        with d_col2:
            d_q = st.selectbox("Колона с Доставено количество (Метри):", df_del.columns, index=df_del.columns.get_loc(del_qty_col[0]) if del_qty_col else 0)
        with d_col3:
            d_d = st.selectbox("Колона с Дата на Доставка:", df_del.columns, index=df_del.columns.get_loc(del_date_col[0]) if del_date_col else 0)
        with d_col4:
            d_w = st.selectbox("Колона за Склад (Доставки):", df_del.columns, index=df_del.columns.get_loc(del_wh_col[0]) if del_wh_col else 0)
            
        # Почистване на доставките
        df_del['Clean_Material'] = df_del[d_m].astype(str).str.strip().str.upper()
        df_del['Delivered_Qty'] = pd.to_numeric(df_del[d_q], errors='coerce').fillna(0)
        df_del['Del_Date'] = df_del[d_d].astype(str).str.strip()
        df_del['Del_Warehouse'] = df_del[d_w].astype(str).str.strip()
        
        # Премахване на дефектни/празни редове
        df_del = df_del[df_del['Clean_Material'] != 'NAN']
        df_del = df_del[df_del['Clean_Material'] != '']
        
        # Крос-анализ по избран артикул
        st.write("---")
        st.write("### 🎯 Картон на артикула: Сравнение Доставки vs Продажби")
        
        # Подсигуряване, че няма float стойности при сортиране на списъка
        sales_mats = [str(x) for x in final_df['Clean_Material'].dropna().unique() if str(x) != '']
        del_mats = [str(x) for x in df_del['Clean_Material'].dropna().unique() if str(x) != '']
        available_materials = sorted(list(set(sales_mats) | set(del_mats)))
        
        selected_art = st.selectbox("Изберете ЕК/САП код за детайлна проверка:", available_materials)
        
        if selected_art:
            # Извличане на име на кабела, ако съществува
            cable_names = final_df[final_df['Clean_Material'] == selected_art]['Cable_Name_Clean'].unique()
            cable_title = cable_names[0] if len(cable_names) > 0 else selected_art
            st.markdown(f"#### Продукт: **{cable_title}**")
            
            # Филтриране
            art_sales = final_df[final_df['Clean_Material'] == selected_art]
            art_deliveries = df_del[df_del['Clean_Material'] == selected_art]
            
            # 1. Общ баланс за този артикул
            total_delivered_art = art_deliveries['Delivered_Qty'].sum()
            total_sold_art = art_sales['Quantity_m'].sum()
            
            b_col1, b_col2, b_col3 = st.columns(3)
            b_col1.metric("Общо Доставено количество за периода", f"{total_delivered_art:,.0f} метра")
            b_col2.metric("Общо Продадено количество за периода", f"{total_sold_art:,.0f} метра")
            b_col3.metric("Разлика (Доставка - Продажба)", f"{total_delivered_art - total_sold_art:,.0f} метра")
            
            # 2. Складова разбивка (Доставки vs Продажби)
            st.write("##### 🏢 Сравнение по Складове (в Метри)")
            
            wh_del_sum = art_deliveries.groupby('Del_Warehouse')['Delivered_Qty'].sum().rename('Доставено количество')
            wh_sale_sum = art_sales.groupby('Warehouse_Clean')['Quantity_m'].sum().rename('Продадено количество')
            
            wh_compare = pd.concat([wh_del_sum, wh_sale_sum], axis=1).fillna(0)
            wh_compare['Разлика'] = wh_compare['Доставено количество'] - wh_compare['Продадено количество']
            wh_compare.index.name = 'Склад'
            
            # Форматиране
            wh_compare_formatted = wh_compare.copy()
            for c in wh_compare_formatted.columns:
                wh_compare_formatted[c] = wh_compare_formatted[c].map('{:,.0f}'.format)
                
            st.dataframe(wh_compare_formatted.reset_index(), use_container_width=True, hide_index=True)
            
            # 3. Детайлни хронологични таблици за артикула
            t_col1, t_col2 = st.columns(2)
            
            with t_col1:
                st.write("##### 📥 Хронология на Доставките")
                show_del_table = art_deliveries[['Del_Date', 'Del_Warehouse', 'Delivered_Qty']].rename(
                    columns={'Del_Date': 'Дата', 'Del_Warehouse': 'Склад', 'Delivered_Qty': 'Количество (м)'}
                )
                st.dataframe(show_del_table, use_container_width=True, hide_index=True)
                
            with t_col2:
                st.write("##### 📤 Хронология на Продажбите")
                show_sale_table = art_sales[['Date_Clean', 'Warehouse_Clean', 'Quantity_m', 'Client_Clean']].rename(
                    columns={'Date_Clean': 'Дата', 'Warehouse_Clean': 'Склад', 'Quantity_m': 'Количество (м)', 'Client_Clean': 'Клиент'}
                )
                st.dataframe(show_sale_table, use_container_width=True, hide_index=True)
                
    except Exception as e:
        st.error(f"Грешка при обработката на доставките: {e}")
elif sales_file is not None and db_metals is None:
    st.sidebar.info("ℹ️ Моля, първо качете таблицата с константите.")

