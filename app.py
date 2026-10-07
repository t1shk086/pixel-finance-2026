import streamlit as st
import pandas as pd

# Настройки на страницата
st.set_page_config(page_title="Измерване на Продажбите на Мед и Алуминий", layout="wide")

st.title("📊 Система за анализ на продажбите на кабели")
st.write("Качете таблицата с константите и месечната таблица с продажби, за да пресметнете тонажите, оборотите, топ продуктите и топ клиентите.")

# ==========================================
# 1. ЗАРЕЖДАНЕ НА КОНСТАНТИТЕ (МЕРИЛКИТЕ)
# ==========================================
st.sidebar.header("1. Избор на файлове")
constants_file = st.sidebar.file_uploader("Качете файла с мерилките (Excel или CSV)", type=["xlsx", "csv"])

# База данни за металите
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
            
            # Разделяне на Мед (001) and Алуминий (002)
            copper = df_const[df_const['Clean_NF'] == '001'][['Clean_Material', 'Clean_Weight']].rename(columns={'Clean_Weight': 'Cu_weight_per_km'})
            aluminum = df_const[df_const['Clean_NF'] == '002'][['Clean_Material', 'Clean_Weight']].rename(columns={'Clean_Weight': 'Al_weight_per_km'})
            
            copper = copper.drop_duplicates(subset=['Clean_Material'])
            aluminum = aluminum.drop_duplicates(subset=['Clean_Material'])
            
            db_metals = pd.merge(copper, aluminum, on='Clean_Material', how='outer').fillna(0)
            st.success("✅ Базата с константи (мерилки) е заредена успешно!")
            
            with st.expander("Преглед на базата данни с константи (Тегла в кг/км)"):
                st.dataframe(db_metals)
        else:
            st.error("❌ Грешка: В качения файл липсват колони 'Материал', 'NF key' или 'Structural weight'!")
            
    except Exception as e:
        st.error(f"Грешка при обработката на константите: {e}")
# ==========================================
# 2. ЗАРЕЖДАНЕ НА МЕСЕЧНИТЕ ПРОДАЖБИ И ИЗЧИСЛЕНИЯ
# ==========================================
sales_file = st.sidebar.file_uploader("Качете месечната таблица с продажби (Excel или CSV)", type=["xlsx", "csv"])

if sales_file is not None and db_metals is not None:
    try:
        if sales_file.name.endswith('.csv'):
            df_sales = pd.read_csv(sales_file, dtype=str)
        else:
            df_sales = pd.read_excel(sales_file, dtype=str)
            
        df_sales.columns = df_sales.columns.str.strip()
        
        # Автоматично напасване към заглавията от вашия SAP/Excel файл
        default_ek = 'САП код' if 'САП код' in df_sales.columns else df_sales.columns
        default_qty = 'Колич.по документ' if 'Колич.по документ' in df_sales.columns else df_sales.columns
        default_wh = 'Склад' if 'Склад' in df_sales.columns else df_sales.columns
        default_to = 'Всичко' if 'Всичко' in df_sales.columns else df_sales.columns
        default_name = 'Материал' if 'Материал' in df_sales.columns else df_sales.columns
        default_client = 'Клиент' if 'Клиент' in df_sales.columns else df_sales.columns

        st.write("### 🔍 Настройка на колоните от файла с продажби")
        col1, col2, col3, col4, col5, col6 = st.columns(5) if 'Клиент' not in df_sales.columns else st.columns(6)
        
        with col1:
            ek_col = st.selectbox("Колона с ЕК Номер:", df_sales.columns, index=int(df_sales.columns.get_loc(default_ek)))
        with col2:
            qty_col = st.selectbox("Колона с Количество (в МЕТРИ):", df_sales.columns, index=int(df_sales.columns.get_loc(default_qty)))
        with col3:
            wh_col = st.selectbox("Колона за Склад:", df_sales.columns, index=int(df_sales.columns.get_loc(default_wh)))
        with col4:
            to_col = st.selectbox("Колона за Оборот (Сума):", df_sales.columns, index=int(df_sales.columns.get_loc(default_to)))
        with col5:
            name_col = st.selectbox("Колона за Име на кабела:", df_sales.columns, index=int(df_sales.columns.get_loc(default_name)))
        if 'Клиент' in df_sales.columns or default_client in df_sales.columns:
            with col6:
                client_col = st.selectbox("Колона за Клиент:", df_sales.columns, index=int(df_sales.columns.get_loc(default_client)))
        else:
            client_col = None
            
        # Премахване на системните обобщаващи редове от края на файла
        df_sales = df_sales[df_sales[ek_col].notna()]
        df_sales = df_sales[~df_sales[ek_col].astype(str).str.contains('Записи:', case=False, na=False)]
        df_sales = df_sales[df_sales[ek_col].astype(str).str.strip() != '']
        
        # Подготовка на чисти данни
        df_sales['Clean_Material'] = df_sales[ek_col].astype(str).str.strip().str.upper()
        df_sales['Quantity_m'] = pd.to_numeric(df_sales[qty_col], errors='coerce').fillna(0)
        df_sales['Turnover_Clean'] = pd.to_numeric(df_sales[to_col], errors='coerce').fillna(0)
        df_sales['Warehouse_Clean'] = df_sales[wh_col].astype(str).str.strip()
        df_sales['Cable_Name_Clean'] = df_sales[name_col].astype(str).str.strip()
        if client_col:
            df_sales['Client_Clean'] = df_sales[client_col].astype(str).str.strip()
        else:
            df_sales['Client_Clean'] = "Неизвестен клиент"
        
        df_sales = df_sales[df_sales['Clean_Material'] != 'NAN']
        
        # Сливане (VLOOKUP) с теглата на металите
        final_df = pd.merge(df_sales, db_metals, on='Clean_Material', how='left')
        final_df['Cu_weight_per_km'] = final_df['Cu_weight_per_km'].fillna(0)
        final_df['Al_weight_per_km'] = final_df['Al_weight_per_km'].fillna(0)
        
        # Изчисление в тонове: (Метри * Кг/Км) / 1 000 000
        final_df['Продадена Мед (Тона)'] = (final_df['Quantity_m'] * final_df['Cu_weight_per_km']) / 1000000
        final_df['Продаден Алуминий (Тона)'] = (final_df['Quantity_m'] * final_df['Al_weight_per_km']) / 1000000
        
        # Сметки за KPI картите
        total_cu = final_df['Продадена Мед (Тона)'].sum()
        total_al = final_df['Продаден Алуминий (Тона)'].sum()
        total_len = final_df['Quantity_m'].sum()
        total_turnover = final_df['Turnover_Clean'].sum()
        
        # Картите с обобщени данни
        st.write("---")
        st.write("### 📈 Общи резултати за компанията")
        kpi1, kpi2, kpi3, kpi4 = st.columns(4)
        kpi1.metric(label="Общ Оборот", value=f"{total_turnover:,.2f} лв.")
        kpi2.metric(label="Общо продадена Мед", value=f"{total_cu:.3f} тона")
        kpi3.metric(label="Общо продаден Алуминий", value=f"{total_al:.3f} тона")
        kpi4.metric(label="Обща дължина кабели", value=f"{total_len:,.0f} метра")
        # --- РАЗБИВКА ПО СКЛАДОВЕ ---
        st.write("### 🏢 Обобщена разбивка по Складове")
        summary_wh = final_df.groupby('Warehouse_Clean').agg({
            'Turnover_Clean': 'sum',
            'Quantity_m': 'sum',
            'Продадена Мед (Тона)': 'sum',
            'Продаден Алуминий (Тона)': 'sum'
        }).reset_index()
        
        summary_wh = summary_wh.sort_values(by='Turnover_Clean', ascending=False)
        
        formatted_wh = pd.DataFrame()
        formatted_wh['Склад'] = summary_wh['Warehouse_Clean']
        formatted_wh['Оборот (лв.)'] = summary_wh['Turnover_Clean'].map('{:,.2f}'.format)
        formatted_wh['Продадена Дължина (Метри)'] = summary_wh['Quantity_m'].map('{:,.0f}'.format)
        formatted_wh['Мед (Тона)'] = summary_wh['Продадена Мед (Тона)'].map('{:.3f}'.format)
        formatted_wh['Алуминий (Тона)'] = summary_wh['Продаден Алуминий (Тона)'].map('{:.3f}'.format)
        
        st.dataframe(formatted_wh, use_container_width=True, hide_index=True)
        
        # Списък със складовете за филтриране на Топ 10
        list_warehouses = ["Всички складове общо"] + list(final_df['Warehouse_Clean'].unique())
        
        st.write("---")
        # --- ТОП 10 НАЙ-ПРОДАВАНИ КАБЕЛА С ИМЕНА ---
        st.write("### 🔝 Топ 10 Най-продавани Кабела")
        
        p_filter_wh = st.selectbox("Филтрирай ТОП 10 Кабели по склад:", list_warehouses, key="wh_products")
        sort_criterion = st.radio(
            "Класирай кабелите по:",
            ["Реализиран Оборот", "Продадена дължина (Метри)", "Тонаж на Мед", "Тонаж на Алуминий"],
            horizontal=True, key="prod_crit"
        )
        
        prod_df_filtered = final_df.copy()
        if p_filter_wh != "Всички складове общо":
            prod_df_filtered = prod_df_filtered[prod_df_filtered['Warehouse_Clean'] == p_filter_wh]
            
        criterion_map = {
            "Реализиран Оборот": "Turnover_Clean",
            "Продадена дължина (Метри)": "Quantity_m",
            "Тонаж на Мед": "Продадена Мед (Тона)",
            "Тонаж на Алуминий": "Продаден Алуминий (Тона)"
        }
        active_column = criterion_map[sort_criterion]
        
        top_products = prod_df_filtered.groupby('Cable_Name_Clean').agg({
            'Turnover_Clean': 'sum',
            'Quantity_m': 'sum',
            'Продадена Мед (Тона)': 'sum',
            'Продаден Алуминий (Тона)': 'sum'
        }).reset_index()
        
        top_10 = top_products.sort_values(by=active_column, ascending=False).head(10).reset_index(drop=True)
        
        top_10_formatted = pd.DataFrame()
        top_10_formatted['Позиция'] = top_10.index + 1
        top_10_formatted['Наименование на кабела'] = top_10['Cable_Name_Clean']
        top_10_formatted['Общ Оборот (лв.)'] = top_10['Turnover_Clean'].map('{:,.2f}'.format)
        top_10_formatted['Общо Метри'] = top_10['Quantity_m'].map('{:,.0f}'.format)
        top_10_formatted['Мед (Тона)'] = top_10['Продадена Мед (Тона)'].map('{:.3f}'.format)
        top_10_formatted['Алуминий (Тона)'] = top_10['Продаден Алуминий (Тона)'].map('{:.3f}'.format)
        
        st.dataframe(top_10_formatted, use_container_width=True, hide_index=True)
        
        st.write("---")
        # --- ТОП 10 КЛИЕНТИ ---
        st.write("### 👥 Топ 10  Клиенти")
        
        c_filter_wh = st.selectbox("Филтрирай ТОП 10 Клиенти по склад:", list_warehouses, key="wh_clients")
        client_sort_criterion = st.radio(
            "Класирай клиентите по:",
            ["Реализиран Оборот (лв.)", "Закупена дължина (Метри)"],
            horizontal=True, key="client_crit"
        )
        
        client_df_filtered = final_df.copy()
        if c_filter_wh != "Всички складове общо":
            client_df_filtered = client_df_filtered[client_df_filtered['Warehouse_Clean'] == c_filter_wh]
            
        client_active_col = "Turnover_Clean" if client_sort_criterion == "Реализиран Оборот (лв.)" else "Quantity_m"
        
        top_clients = client_df_filtered.groupby('Client_Clean').agg({
            'Turnover_Clean': 'sum',
            'Quantity_m': 'sum',
            'Продадена Мед (Тона)': 'sum',
            'Продаден Алуминий (Тона)': 'sum'
        }).reset_index()
        
        top_10_clients = top_clients.sort_values(by=client_active_col, ascending=False).head(10).reset_index(drop=True)
        
        top_10_clients_fmt = pd.DataFrame()
        top_10_clients_fmt['Позиция'] = top_10_clients.index + 1
        top_10_clients_fmt['Име на Клиента'] = top_10_clients['Client_Clean']
        top_10_clients_fmt['Общ Оборот от Клиента (лв.)'] = top_10_clients['Turnover_Clean'].map('{:,.2f}'.format)
        top_10_clients_fmt['Общо Закупени Метри'] = top_10_clients['Quantity_m'].map('{:,.0f}'.format)
        top_10_clients_fmt['Тонаж Мед'] = top_10_clients['Продадена Мед (Тона)'].map('{:.3f}'.format)
        top_10_clients_fmt['Тонаж Алуминий'] = top_10_clients['Продаден Алуминий (Тона)'].map('{:.3f}'.format)
        
        st.dataframe(top_10_clients_fmt, use_container_width=True, hide_index=True)
        
        # Предупреждения за липсващи кодове
        missing_condition = (final_df['Cu_weight_per_km'] == 0) & (final_df['Al_weight_per_km'] == 0)
        missing_ek = final_df[missing_condition]['Clean_Material'].dropna().unique()
        missing_ek_str = [str(x) for x in missing_ek if str(x).lower() not in ['nan', '', 'none']]
        
        if len(missing_ek_str) > 0:
            st.warning(f"⚠️ Общо {len(missing_ek_str)} SAP кода от продажбите липсват в таблицата с константи (сметнати с 0 кг):")
            st.write(missing_ek_str[:10])
        
        # Пълна таблица
        st.write("### 📄 Пълна детайлна таблица")
        st.dataframe(final_df)
        
        @st.cache_data
        def convert_df(df):
            return df.to_csv(index=False).encode('utf-8-sig')
            
        csv_data = convert_df(final_df)
        st.download_button(
            label="📥 Изтегли детайлните резултати (CSV)",
            data=csv_data,
            file_name="Изчислени_Продажби_Кабели.csv",
            mime="text/csv",
        )
            
    except Exception as e:
        st.error(f"Грешка при обработката на данните: {e}")
elif sales_file is not None and db_metals is None:
    st.sidebar.info("ℹ️ Моля, първо качете таблицата с константите от лявото меню.")

