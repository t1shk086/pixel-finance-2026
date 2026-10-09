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
        default_ek = 'САП код' if 'САП код' in df_sales.columns else df_sales.columns[0]
        default_qty = 'Колич.по документ' if 'Колич.по документ' in df_sales.columns else df_sales.columns[0]
        default_wh = 'Склад' if 'Склад' in df_sales.columns else df_sales.columns[0]
        default_to = 'Всичко' if 'Всичко' in df_sales.columns else df_sales.columns[0]
        default_name = 'Материал' if 'Материал' in df_sales.columns else df_sales.columns[0]
        default_client = 'Клиент' if 'Клиент' in df_sales.columns else df_sales.columns[0]

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
        final_df['Продадена Мед (Тона)'] = (
