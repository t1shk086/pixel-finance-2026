import streamlit as st
import pandas as pd
import re
import os
from datetime import date

# Настройки на страницата
st.set_page_config(page_title="Система за Анализ и Заявки на Кабели", layout="wide")

st.title("📊 Система за анализ на продажбите и управление на заявки")
st.write("Качете таблиците за анализ или използвайте модула за въвеждане на нови заявки.")

# ==========================================
# ⚙️ ФУНКЦИИ ЗА НОРМАЛИЗИРАНЕ И ПОМОЩНИ
# ==========================================
def clean_warehouse_name(val):
    if pd.isna(val) or not str(val).strip():
        return "Неизвестен склад"
    s = str(val).strip()
    s = re.sub(r'^[0-9\s\-_:\.]+', '', s).strip()
    return s if s else str(val).strip()

def find_column(columns, candidates):
    for candidate in candidates:
        if candidate in columns:
            return candidate
    for col in columns:
        col_clean = str(col).strip().lower()
        for candidate in candidates:
            if str(candidate).strip().lower() in col_clean:
                return col
    return columns[0] if len(columns) else None

# Локален файл за съхранение на заявките
ORDERS_FILE = "zayavki_orders.csv"

# ==========================================
# 1. ЗАРЕЖДАНЕ НА КОНСТАНТИТЕ (МЕРИЛКИТЕ)
# ==========================================
st.sidebar.header("1. Мерилки (Константи)")
constants_file = st.sidebar.file_uploader("Качете файла с мерилките (Excel или CSV)", type=["xlsx", "csv"], key="const_file")

db_metals = None
material_name_map = {}

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
            st.error("❌ Грешка: В качения файл липсват колони 'Материал', 'NF key' или 'Structural weight'!")
            
    except Exception as e:
        st.error(f"Грешка при обработката на константите: {e}")

# ==========================================
# 📝 МОДУЛ ЗА ЗАЯВКИ (ВЪВЕЖДАНЕ И ЗАПИС)
# ==========================================
st.write("---")
st.header("📝 Модул за създаване и натрупване на Заявки")

# Опит за извличане на имена на кабели за автоматично попълване
sales_file_temp = st.sidebar.file_uploader("Качете месечната таблица с продажби (Excel или CSV)", type=["xlsx", "csv"], key="sales_file")

# Подготовка на речник (mapping) ЕК Код -> Име на кабела
if sales_file_temp is not None:
    try:
        if sales_file_temp.name.endswith('.csv'):
            df_s_temp = pd.read_csv(sales_file_temp, dtype=str)
        else:
            df_s_temp = pd.read_excel(sales_file_temp, dtype=str)
        df_s_temp.columns = df_s_temp.columns.str.strip()
        ek_c = find_column(df_s_temp.columns, ['САП код', 'SAP код', 'ЕК Номер', 'Материал'])
        nm_c = find_column(df_s_temp.columns, ['Материал', 'Наименование', 'Име', 'Cable Name'])
        if ek_c and nm_c:
            temp_map = df_s_temp[[ek_c, nm_c]].dropna().drop_duplicates()
            material_name_map = dict(zip(
                temp_map[ek_c].astype(str).str.strip().str.upper(),
                temp_map[nm_c].astype(str).str.strip()
            ))
    except Exception:
        pass

with st.expander("➕ Въведи нова заявка", expanded=True):
    col_z1, col_z2, col_z3 = st.columns(3)

    with col_z1:
        input_ek = st.text_input("Въведете ЕК / САП Код:", key="order_ek_input").strip().upper()
        
        # Автоматично намиране на името
        detected_name = material_name_map.get(input_ek, "")
        if input_ek and not detected_name:
            detected_name = st.text_input("Наименование на кабела (въведете ръчно):", value="", key="manual_cable_name")
        elif input_ek and detected_name:
            st.info(f"📌 Намерено име: **{detected_name}**")

    with col_z2:
        step_choice = st.radio("Изберете кратност на опаковката:", ["Кратност 100 м.", "Кратност 1000 м."], horizontal=True)
        step_val = 100 if step_choice == "Кратност 100 м." else 1000
        
        num_units = st.number_input(
            f"Брой опаковки/бунти ({step_val} м. всяка):",
            min_value=1,
            value=1,
            step=1,
            key="order_units_input"
        )
        total_order_qty = num_units * step_val
        st.success(f"📏 Общо за заявяване: **{total_order_qty:,.0f} метра**")

    with col_z3:
        order_date = st.date_input("Дата на заявката:", value=date.today(), key="order_date_input")
        
        warehouse_list = ["София", "Пловдив", "Варна", "Бургас", "Централен склад"]
        order_warehouse = st.selectbox("Изберете склад за заявката:", warehouse_list, key="order_wh_input")

    # Бутон за запазване на заявката
    if st.button("💾 Запиши заявката", type="primary"):
        if not input_ek:
            st.error("❌ Моля, въведете ЕК / САП код!")
        else:
            final_cable_name = detected_name if detected_name else "Неизвестен кабел"
            
            # Нов ред
            new_order = pd.DataFrame([{
                'Дата на заявка': order_date.strftime('%Y-%m-%d'),
                'ЕК / САП Код': input_ek,
                'Наименование на кабела': final_cable_name,
                'Кратност (м)': step_val,
                'Брой опаковки': num_units,
                'Заявено количество (м)': total_order_qty,
                'Склад': order_warehouse
            }])

            # Записване / Натрупване във файла
            if os.path.exists(ORDERS_FILE):
                new_order.to_csv(ORDERS_FILE, mode='a', header=False, index=False, encoding='utf-8-sig')
            else:
                new_order.to_csv(ORDERS_FILE, mode='w', header=True, index=False, encoding='utf-8-sig')

            st.balloons()
            st.success(f"✅ Заявката за {total_order_qty:,.0f} м. {final_cable_name} за склад {order_warehouse} бе записана успешно!")

# ==========================================
# 📋 ПРЕГЛЕД НА ВСИЧКИ ЗАПИСАНИ ЗАЯВКИ
# ==========================================
if os.path.exists(ORDERS_FILE):
    st.write("### 📋 Списък с всички записани заявки (натрупани локално)")
    df_orders_all = pd.read_csv(ORDERS_FILE, dtype=str)
    
    col_f1, col_f2 = st.columns(2)
    with col_f1:
        filter_ord_wh = st.selectbox("Филтрирай заявките по склад:", ["Всички складове"] + list(df_orders_all['Склад'].unique()))
    with col_f2:
        st.write("") # визуален спасер

    view_orders = df_orders_all.copy()
    if filter_ord_wh != "Всички складове":
        view_orders = view_orders[view_orders['Склад'] == filter_ord_wh]

    st.dataframe(view_orders, use_container_width=True, hide_index=True)

    # Бутон за изтегляне на пълния експорт
    orders_csv = df_orders_all.to_csv(index=False).encode('utf-8-sig')
    st.download_button(
        label="📥 Изтегли всички заявки (CSV)",
        data=orders_csv,
        file_name="Zayavki_Kabeli.csv",
        mime="text/csv"
    )

# ==========================================
# 2. ПРОДЪЛЖЕНИЕ С АНАЛИЗА НА ПРОДАЖБИТЕ
# ==========================================
sales_file = sales_file_temp # използваме качения файл отгоре

if sales_file is not None and db_metals is not None:
    try:
        if sales_file.name.endswith('.csv'):
            df_sales = pd.read_csv(sales_file, dtype=str)
        else:
            df_sales = pd.read_excel(sales_file, dtype=str)
            
        df_sales.columns = df_sales.columns.str.strip()
        
        default_ek = find_column(df_sales.columns, ['САП код', 'SAP код', 'ЕК Номер', 'Материал'])
        default_qty = find_column(df_sales.columns, ['Колич.по документ', 'Количество', 'Количество (м)', 'Qty', 'Quantity'])
        default_wh = find_column(df_sales.columns, ['Склад', 'Warehouse', 'Plant'])
        default_to = find_column(df_sales.columns, ['Всичко', 'Оборот', 'Сума', 'Total', 'Amount'])
        default_name = find_column(df_sales.columns, ['Материал', 'Наименование', 'Име', 'Cable Name'])
        default_client = find_column(df_sales.columns, ['Клиент', 'Client', 'Customer'])
        default_date = find_column(df_sales.columns, ['Дата', 'Дата на фактура', 'Дата документ', 'Posting Date', 'Date', 'Document Date'])

        st.write("---")
        st.write("## 📈 Анализ на качения файл с продажби")
        
        col1, col2, col3, col4, col5, col6, col7 = st.columns(7)
        with col1:
            ek_col = st.selectbox("ЕК / САП Номер:", df_sales.columns, index=int(df_sales.columns.get_loc(default_ek)))
        with col2:
            qty_col = st.selectbox("Количество (МЕТРИ):", df_sales.columns, index=int(df_sales.columns.get_loc(default_qty)))
        with col3:
            wh_col = st.selectbox("Склад:", df_sales.columns, index=int(df_sales.columns.get_loc(default_wh)))
        with col4:
            to_col = st.selectbox("Оборот (Сума):", df_sales.columns, index=int(df_sales.columns.get_loc(default_to)))
        with col5:
            name_col = st.selectbox("Име на кабела:", df_sales.columns, index=int(df_sales.columns.get_loc(default_name)))
        with col6:
            client_options = ["— Няма —"] + list(df_sales.columns)
            c_idx = client_options.index(default_client) if default_client in client_options else 0
            client_col = st.selectbox("Клиент:", client_options, index=c_idx)
        with col7:
            date_options = ["— Няма дата —"] + list(df_sales.columns)
            d_idx = date_options.index(default_date) if default_date in date_options else 0
            sales_date_col = st.selectbox("Дата на продажба:", date_options, index=d_idx)

        # Премахване на системните обобщаващи редове
        df_sales = df_sales[df_sales[ek_col].notna()]
        df_sales = df_sales[~df_sales[ek_col].astype(str).str.contains('Записи:', case=False, na=False)]
        df_sales = df_sales[df_sales[ek_col].astype(str).str.strip() != '']
        
        df_sales['Clean_Material'] = df_sales[ek_col].astype(str).str.strip().str.upper()
        df_sales['Quantity_m'] = pd.to_numeric(df_sales[qty_col], errors='coerce').fillna(0)
        df_sales['Turnover_Clean'] = pd.to_numeric(df_sales[to_col], errors='coerce').fillna(0)
        df_sales['Warehouse_Clean'] = df_sales[wh_col].apply(clean_warehouse_name)
        df_sales['Cable_Name_Clean'] = df_sales[name_col].astype(str).str.strip()
        
        if client_col != "— Няма —":
            df_sales['Client_Clean'] = df_sales[client_col].astype(str).str.strip()
        else:
            df_sales['Client_Clean'] = "Неизвестен клиент"
        
        if sales_date_col != "— Няма дата —":
            df_sales['Sales_Date'] = pd.to_datetime(df_sales[sales_date_col], errors='coerce', dayfirst=True)
            df_sales['Year_Month'] = df_sales['Sales_Date'].dt.strftime('%Y-%m')
        else:
            df_sales['Sales_Date'] = pd.NaT
            df_sales['Year_Month'] = "Всички"

        df_sales = df_sales[df_sales['Clean_Material'] != 'NAN']
        
        final_df = pd.merge(df_sales, db_metals, on='Clean_Material', how='left')
        final_df['Cu_weight_per_km'] = final_df['Cu_weight_per_km'].fillna(0)
        final_df['Al_weight_per_km'] = final_df['Al_weight_per_km'].fillna(0)
        
        final_df['Продадена Мед (Тона)'] = (final_df['Quantity_m'] * final_df['Cu_weight_per_km']) / 1000000
        final_df['Продаден Алуминий (Тона)'] = (final_df['Quantity_m'] * final_df['Al_weight_per_km']) / 1000000
        
        # 📅 ФИЛТЪР ПО МЕСЕЦ
        if sales_date_col != "— Няма дата —" and final_df['Year_Month'].nunique() > 1:
            available_months = sorted([m for m in final_df['Year_Month'].dropna().unique() if m != "Всички"])
            month_filter = st.selectbox("📅 Филтрирай продажбите по месец:", ["Всички месеци"] + available_months, key="month_selector")
            filtered_sales_df = final_df[final_df['Year_Month'] == month_filter].copy() if month_filter != "Всички месеци" else final_df.copy()
        else:
            filtered_sales_df = final_df.copy()

        # KPI Картите за продажбите
        total_cu = filtered_sales_df['Продадена Мед (Тона)'].sum()
        total_al = filtered_sales_df['Продаден Алуминий (Тона)'].sum()
        total_len = filtered_sales_df['Quantity_m'].sum()
        total_turnover = filtered_sales_df['Turnover_Clean'].sum()
        
        kpi1, kpi2, kpi3, kpi4 = st.columns(4)
        kpi1.metric(label="Общ Оборот", value=f"{total_turnover:,.2f} лв.")
        kpi2.metric(label="Общо продадена Мед", value=f"{total_cu:.3f} тона")
        kpi3.metric(label="Общо продаден Алуминий", value=f"{total_al:.3f} тона")
        kpi4.metric(label="Обща дължина кабели", value=f"{total_len:,.0f} метра")

    except Exception as e:
        st.error(f"Грешка при обработката на данните: {e}")

# ==========================================
# 3. ДОСТАВКИ
# ==========================================
st.sidebar.write("---")
st.sidebar.header("3. Доставки")
delivery_file = st.sidebar.file_uploader("Качете файла с доставки (Excel или CSV)", type=["xlsx", "csv"], key="delivery_file")

if delivery_file is not None:
    try:
        if delivery_file.name.endswith('.csv'):
            df_delivery = pd.read_csv(delivery_file, dtype=str)
        else:
            df_delivery = pd.read_excel(delivery_file, dtype=str)
        st.success("✅ Файлът с доставки е зареден успешно!")
    except Exception as e:
        st.error(f"Грешка при доставките: {e}")

# ==========================================
# 4. НАЛИЧНОСТИ
# ==========================================
st.sidebar.write("---")
st.sidebar.header("4. Наличности")
stock_file = st.sidebar.file_uploader("Качете файла с наличности (Excel или CSV)", type=["xlsx", "csv"], key="stock_file")

if stock_file is not None and db_metals is not None:
    try:
        if stock_file.name.endswith('.csv'):
            df_stock = pd.read_csv(stock_file, dtype=str)
        else:
            df_stock = pd.read_excel(stock_file, dtype=str)
        st.success("✅ Файлът с наличности е зареден успешно!")
    except Exception as e:
        st.error(f"Грешка при наличностите: {e}")
