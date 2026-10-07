import streamlit as st
import pandas as pd

# Настройки на страницата
st.set_page_config(page_title="Измерване на Продажбите на Мед и Алуминий", layout="wide")

st.title("📊 Система за анализ на метални тонажи в продажбите на кабели")
st.write("Качете таблицата с константите и месечната таблица с продажби, за да пресметнете тонажите на Мед и Алуминий.")

# 1. Зареждане на таблицата с константите (Мерилките)
st.sidebar.header("1. Константни величини")
constants_file = st.sidebar.file_uploader("Качете файла с meрилките (Excel или CSV)", type=["xlsx", "csv"])

# Логика за обработка на константите
db_metals = None
if constants_file is not None:
    try:
        if constants_file.name.endswith('.csv'):
            df_const = pd.read_csv(constants_file)
        else:
            df_const = pd.read_excel(constants_file)
            
        # Почистване на имената на колоните от интервали
        df_const.columns = df_const.columns.str.strip()
        
        # Преформатиране на таблицата, за да изкараме мед и алуминий на един ред за всеки ЕК номер
        # NF key: 001 = Мед, 002 = Алуминий
        df_const['Material'] = df_const['Материал'].astype(str).str.strip()
        df_const['NF_key'] = df_const['NF key'].astype(str).str.strip()
        df_const['Structural_weight'] = pd.to_numeric(df_const['Structural weight'], errors='coerce').fillna(0)
        
        # Извличане на теглата за Мед (001) и Алуминий (002)
        copper = df_const[df_const['NF_key'] == '001'][['Material', 'Structural_weight']].rename(columns={'Structural_weight': 'Cu_weight_per_km'})
        aluminum = df_const[df_const['NF_key'] == '002'][['Material', 'Structural_weight']].rename(columns={'Structural_weight': 'Al_weight_per_km'})
        
        # Обединяване в една базова референтна таблица
        db_metals = pd.merge(copper, aluminum, on='Material', how='outer').fillna(0)
        st.success("✅ Таблицата с константите е заредена успешно!")
        
        with st.expander("Преглед на базата данни с константи (Тегла в кг/км)"):
            st.dataframe(db_metals)
            
    except Exception as e:
        st.error(f"Грешка при обработката на константите: {e}")

# 2. Зареждане на месечните продажби
st.sidebar.header("2. Месечни продажби")
sales_file = st.sidebar.file_uploader("Качете месечната таблица с продажби (Excel или CSV)", type=["xlsx", "csv"])

if sales_file is not None and db_metals is not None:
    try:
        if sales_file.name.endswith('.csv'):
            df_sales = pd.read_csv(sales_file)
        else:
            df_sales = pd.read_excel(sales_file)
            
        df_sales.columns = df_sales.columns.str.strip()
        
        st.write("### 🔍 Настройка на колоните от файла с продажби")
        col1, col2 = st.columns(2)
        
        with col1:
            ek_col = st.selectbox("Изберете колоната с ЕК Номер:", df_sales.columns)
        with col2:
            qty_col = st.selectbox("Изберете колоната с Продадено количество (в МЕТРИ):", df_sales.columns)
            
        if st.button("🚀 Изчисли тонажите"):
            # Подготовка на данните за продажби
            df_sales['Material'] = df_sales[ek_col].astype(str).str.strip()
            df_sales['Quantity_m'] = pd.to_numeric(df_sales[qty_col], errors='coerce').fillna(0)
            
            # Марджиране (VLOOKUP) с константите по ЕК Номер (Material)
            final_df = pd.merge(df_sales, db_metals, on='Material', how='left')
            
            # Ако има ЕК номера, които липсват в базата с константи, ги запълваме с 0
            final_df['Cu_weight_per_km'] = final_df['Cu_weight_per_km'].fillna(0)
            final_df['Al_weight_per_km'] = final_df['Al_weight_per_km'].fillna(0)
            
            # Изчисления в ТОНОВЕ: (Метри * Кг/Км) / (1000 * 1000)
            final_df['Продадена Мед (Тона)'] = (final_df['Quantity_m'] * final_df['Cu_weight_per_km']) / 1000000
            final_df['Продаден Алуминий (Тона)'] = (final_df['Quantity_m'] * final_df['Al_weight_per_km']) / 1000000
            
            # Общи суми за месеца
            total_cu = final_df['Продадена Мед (Тона)'].sum()
            total_al = final_df['Продаден Алуминий (Тона)'].sum()
            total_len = final_df['Quantity_m'].sum()
            
            # Визуализация на резултатите (Красиви карти)
            st.write("### 📈 Общи резултати за периода")
            kpi1, kpi2, kpi3 = st.columns(3)
            kpi1.metric(label="Общо продадена Мед", value=f"{total_cu:.3f} тона")
            kpi2.metric(label="Общо продаден Алуминий", value=f"{total_al:.3f} тона")
            kpi3.metric(label="Обща дължина кабели", value=f"{total_len:,.0f} метра")
            
            # Проверка за липсващи ЕК Номера (Коригиран Pandas оператор)
            missing_ek = final_df[(final_df['Cu_weight_per_km'] == 0) & (final_df['Al_weight_per_km'] == 0)]['Material'].unique()
            # Премахваме празни стрингове от проверката
            missing_ek = [x for x in missing_ek if x != 'nan' and x != '']
            if len(missing_ek) > 0:
                st.warning(f"⚠️ Следните ЕК номера от продажбите липсват в таблицата с константи и не са обсметнати: {', '.join(missing_ek[:10])}...")
            
            # Подредба и извеждане на крайния файл за изтегляне
            st.write("### 📄 Детайлна таблица с изчисления")
            st.dataframe(final_df)
            
            # Бутон за сваляне на готовия резултат обратно в Excel
            @st.cache_data
            def convert_df(df):
                return df.to_csv(index=False).encode('utf-8-sig') # utf-8-sig за правилно четене на кирилица в Excel
                
            csv_data = convert_df(final_df)
            st.download_button(
                label="📥 Изтегли резултатите в Excel (CSV формат)",
                data=csv_data,
                file_name="Calculated_Cable_Sales_Tonnages.csv",
                mime="text/csv",
            )
            
    except Exception as e:
        st.error(f"Грешка при обработката на продажбите: {e}")
elif sales_file is not None and db_metals is None:
    st.info("ℹ️ Моля, първо качете таблицата с константите от лявото меню.")
