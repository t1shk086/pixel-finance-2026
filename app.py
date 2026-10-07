import streamlit as st
import pandas as pd

# Настройки на страницата
st.set_page_config(page_title="Измерване на Продажбите на Мед и Алуминий", layout="wide")

st.title("📊 Система за анализ на метални тонажи в продажбите на кабели")
st.write("Качете таблицата с константите и месечната таблица с продажби, за да пресметнете тонажите на Мед и Алуминий.")

# 1. Зареждане на таблицата с константите (Мерилките)
st.sidebar.header("1. Константни величини")
constants_file = st.sidebar.file_uploader("Качете файла с мерилките (Excel или CSV)", type=["xlsx", "csv"])

# База данни за металите
db_metals = None

if constants_file is not None:
    try:
        # Отваряне на файла и принудително четене на колоната за Материал като ТЕКСТ
        if constants_file.name.endswith('.csv'):
            df_const = pd.read_csv(constants_file, dtype={'Материал': str, 'Material': str})
        else:
            df_const = pd.read_excel(constants_file, dtype={'Материал': str, 'Material': str})
            
        # Почистване на интервали в имената на колоните
        df_const.columns = df_const.columns.str.strip()
        
        # Намиране на колоната за ЕК Номер (поддържа "Материал" или "Material")
        mat_col = 'Материал' if 'Материал' in df_const.columns else ('Material' if 'Material' in df_const.columns else None)
        nf_col = 'NF key' if 'NF key' in df_const.columns else ('NF_key' if 'NF_key' in df_const.columns else None)
        weight_col = 'Structural weight' if 'Structural weight' in df_const.columns else None
        
        if mat_col and nf_col and weight_col:
            # Преобразуване и почистване на ключовите полета
            df_const['Clean_Material'] = df_const[mat_col].astype(str).str.strip().str.upper()
            df_const['Clean_NF'] = df_const[nf_col].astype(str).str.strip().str.replace('.0', '', regex=False).str.zfill(3)
            df_const['Clean_Weight'] = pd.to_numeric(df_const[weight_col], errors='coerce').fillna(0)
            
            # Разделяне на Мед (001) и Алуминий (002)
            copper = df_const[df_const['Clean_NF'] == '001'][['Clean_Material', 'Clean_Weight']].rename(columns={'Clean_Weight': 'Cu_weight_per_km'})
            aluminum = df_const[df_const['Clean_NF'] == '002'][['Clean_Material', 'Clean_Weight']].rename(columns={'Clean_Weight': 'Al_weight_per_km'})
            
            # Премахване на дубликати, ако има такива
            copper = copper.drop_duplicates(subset=['Clean_Material'])
            aluminum = aluminum.drop_duplicates(subset=['Clean_Material'])
            
            # Обединяване в референтна база
            db_metals = pd.merge(copper, aluminum, on='Clean_Material', how='outer').fillna(0)
            st.success("✅ Базата с константи (мерилки) е заредена успешно!")
            
            with st.expander("Преглед на базата данни с константи (Тегла в кг/км)"):
                st.dataframe(db_metals)
        else:
            st.error("❌ Грешка: В качения файл липсват колони 'Материал', 'NF key' или 'Structural weight'!")
            
    except Exception as e:
        st.error(f"Грешка при обработката на константите: {e}")

# 2. Зареждане на месечните продажби
st.sidebar.header("2. Месечни продажби")
sales_file = st.sidebar.file_uploader("Качете месечната таблица с продажби (Excel или CSV)", type=["xlsx", "csv"])

if sales_file is not None and db_metals is not None:
    try:
        # Принудително прочитане на целия файл като стрингове първоначално за безопасност
        if sales_file.name.endswith('.csv'):
            df_sales = pd.read_csv(sales_file, dtype=str)
        else:
            df_sales = pd.read_excel(sales_file, dtype=str)
            
        df_sales.columns = df_sales.columns.str.strip()
        
        st.write("### 🔍 Настройка на колоните от файла с продажби")
        col1, col2 = st.columns(2)
        
        with col1:
            ek_col = st.selectbox("Изберете колоната с ЕК Номер:", df_sales.columns)
        with col2:
            qty_col = st.selectbox("Изберете колоната с Продадено количество (в МЕТРИ):", df_sales.columns)
            
        if st.button("🚀 Изчисли тонажите"):
            # Подготовка на данните за продажби - безопасно преобразуване в текст
            df_sales['Clean_Material'] = df_sales[ek_col].astype(str).str.strip().str.upper()
            
            # Изчистване на числовите стойности за дължината
            df_sales['Quantity_m'] = pd.to_numeric(df_sales[qty_col], errors='coerce').fillna(0)
            
            # Обединяване (VLOOKUP) с константната база данни
            final_df = pd.merge(df_sales, db_metals, on='Clean_Material', how='left')
            
            # Запълване на липсващите референции с 0
            final_df['Cu_weight_per_km'] = final_df['Cu_weight_per_km'].fillna(0)
            final_df['Al_weight_per_km'] = final_df['Al_weight_per_km'].fillna(0)
            
            # Формула за изчисление в ТОНОВЕ: (Метри * Кг/Км) / 1 000 000
            final_df['Продадена Мед (Тона)'] = (final_df['Quantity_m'] * final_df['Cu_weight_per_km']) / 1000000
            final_df['Продаден Алуминий (Тона)'] = (final_df['Quantity_m'] * final_df['Al_weight_per_km']) / 1000000
            
            # Изчисляване на крайната статистика
            total_cu = final_df['Продадена Мед (Тона)'].sum()
            total_al = final_df['Продаден Алуминий (Тона)'].sum()
            total_len = final_df['Quantity_m'].sum()
            
            # Показване на KPI Карти
            st.write("### 📈 Общи резултати за периода")
            kpi1, kpi2, kpi3 = st.columns(3)
            kpi1.metric(label="Общо продадена Мед", value=f"{total_cu:.3f} тона")
            kpi2.metric(label="Общо продаден Алуминий", value=f"{total_al:.3f} тона")
            kpi3.metric(label="Обща дължина кабели", value=f"{total_len:,.0f} метра")
            
            # Проверка за липсващи ЕК Номера в номенклатурата
            missing_condition = (final_df['Cu_weight_per_km'] == 0) & (final_df['Al_weight_per_km'] == 0)
            missing_ek = final_df[missing_condition]['Clean_Material'].dropna().unique()
            missing_ek_str = [str(x) for x in missing_ek if str(x).lower() not in ['nan', '', 'none']]
            
            if len(missing_ek_str) > 0:
                st.warning(f"⚠️ Общо {len(missing_ek_str)} ЕК номера от продажбите липсват в базата с константи и не са начислили тегло (записани с 0 тона):")
                st.write(missing_ek_str[:15])  # Покажи първите 15 липсващи
            
            # Извеждане на таблицата с резултатите
            st.write("### 📄 Детайлна таблица с изчисления")
            # Премахваме помощната временна колона преди показване
            display_df = final_df.copy()
            st.dataframe(display_df)
            
            # Функция за изтегляне на резултата
            @st.cache_data
            def convert_df(df):
                return df.to_csv(index=False).encode('utf-8-sig')
                
            csv_data = convert_df(final_df)
            st.download_button(
                label="📥 Изтегли пресметнатата таблица (Excel / CSV)",
                data=csv_data,
                file_name="Пресметнати_Продажби_Мед_Алуминий.csv",
                mime="text/csv",
            )
            
    except Exception as e:
        st.error(f"Грешка при обработката на продажбите: {e}")
elif sales_file is not None and db_metals is None:
    st.info("ℹ️ Моля, първо качете таблицата с константите (мерилките) от лявото меню.")
