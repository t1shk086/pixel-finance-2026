import streamlit as st
import pandas as pd
import re

# Настройки на страницата
st.set_page_config(page_title="Измерване на Продажбите на Мед и Алуминий", layout="wide")

st.title("📊 Система за анализ на продажбите на кабели")
st.write("Качете таблицата с константите и месечната таблица с продажби, за да пресметнете тонажите, оборотите, топ продуктите и топ клиентите.")

# ==========================================
# ⚙️ ФУНКЦИЯ ЗА НОРМАЛИЗИРАНЕ НА СКЛАДОВЕ
# ==========================================
def clean_warehouse_name(val):
    if pd.isna(val) or not str(val).strip():
        return "Неизвестен склад"
    s = str(val).strip()
    s = re.sub(r'^[0-9\s\-_:\.]+', '', s).strip()
    return s if s else str(val).strip()

# ==========================================
# 1. ЗАРЕЖДАНЕ НА КОНСТАНТИТЕ (МЕРИЛКИТЕ)
# ==========================================
st.sidebar.header("1. Избор на файлове")
constants_file = st.sidebar.file_uploader("Качете файла с мерилките (Excel или CSV)", type=["xlsx", "csv"])

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
        
        default_ek = 'САП код' if 'САП код' in df_sales.columns else df_sales.columns[0]
        default_qty = 'Колич.по документ' if 'Колич.по документ' in df_sales.columns else df_sales.columns[0]
        default_wh = 'Склад' if 'Склад' in df_sales.columns else df_sales.columns[0]
        default_to = 'Всичко' if 'Всичко' in df_sales.columns else df_sales.columns[0]
        default_name = 'Материал' if 'Материал' in df_sales.columns else df_sales.columns[0]
        default_client = 'Клиент' if 'Клиент' in df_sales.columns else df_sales.columns[0]

        st.write("### 🔍 Настройка на колоните от файла с продажби")
        col1, col2, col3, col4, col5, col6 = st.columns(5) if 'Клиент' not in df_sales.columns else st.columns(6)
        
        with col1:
            ek_col = st.selectbox("Колона с ЕК / САП Номер:", df_sales.columns, index=int(df_sales.columns.get_loc(default_ek)))
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
            
        df_sales = df_sales[df_sales[ek_col].notna()]
        df_sales = df_sales[~df_sales[ek_col].astype(str).str.contains('Записи:', case=False, na=False)]
        df_sales = df_sales[df_sales[ek_col].astype(str).str.strip() != '']
        
        df_sales['Clean_Material'] = df_sales[ek_col].astype(str).str.strip().str.upper()
        df_sales['Quantity_m'] = pd.to_numeric(df_sales[qty_col], errors='coerce').fillna(0)
        df_sales['Turnover_Clean'] = pd.to_numeric(df_sales[to_col], errors='coerce').fillna(0)
        df_sales['Warehouse_Clean'] = df_sales[wh_col].apply(clean_warehouse_name)
        df_sales['Cable_Name_Clean'] = df_sales[name_col].astype(str).str.strip()
        if client_col:
            df_sales['Client_Clean'] = df_sales[client_col].astype(str).str.strip()
        else:
            df_sales['Client_Clean'] = "Неизвестен клиент"
        
        df_sales = df_sales[df_sales['Clean_Material'] != 'NAN']
        
        final_df = pd.merge(df_sales, db_metals, on='Clean_Material', how='left')
        final_df['Cu_weight_per_km'] = final_df['Cu_weight_per_km'].fillna(0)
        final_df['Al_weight_per_km'] = final_df['Al_weight_per_km'].fillna(0)
        
        final_df['Продадена Мед (Тона)'] = (final_df['Quantity_m'] * final_df['Cu_weight_per_km']) / 1000000
        final_df['Продаден Алуминий (Тона)'] = (final_df['Quantity_m'] * final_df['Al_weight_per_km']) / 1000000
        
        total_cu = final_df['Продадена Мед (Тона)'].sum()
        total_al = final_df['Продаден Алуминий (Тона)'].sum()
        total_len = final_df['Quantity_m'].sum()
        total_turnover = final_df['Turnover_Clean'].sum()
        
        st.write("---")
        st.write("### 📈 Общи резултати за компанията")
        kpi1, kpi2, kpi3, kpi4 = st.columns(4)
        kpi1.metric(label="Общ Оборот", value=f"{total_turnover:,.2f} лв.")
        kpi2.metric(label="Общо продадена Мед", value=f"{total_cu:.3f} тона")
        kpi3.metric(label="Общо продаден Алуминий", value=f"{total_al:.3f} тона")
        kpi4.metric(label="Обща дължина кабели", value=f"{total_len:,.0f} метра")
        
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
        
        list_warehouses = ["Всички складове общо"] + list(final_df['Warehouse_Clean'].unique())
        
        st.write("---")
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
        st.write("### 👥 Топ 10 Клиенти")
        
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
        
        missing_condition = (final_df['Cu_weight_per_km'] == 0) & (final_df['Al_weight_per_km'] == 0)
        missing_ek = final_df[missing_condition]['Clean_Material'].dropna().unique()
        missing_ek_str = [str(x) for x in missing_ek if str(x).lower() not in ['nan', '', 'none']]
        
        if len(missing_ek_str) > 0:
            st.warning(f"⚠️ Общо {len(missing_ek_str)} SAP кода от продажбите липсват в таблицата с константи (сметнати с 0 кг):")
            st.write(missing_ek_str[:10])
        
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

# ==========================================
# 3. ЗАРЕЖДАНЕ И АНАЛИЗ НА ДОСТАВКИТЕ
# ==========================================
st.sidebar.write("---")
st.sidebar.header("2. Доставки")
delivery_file = st.sidebar.file_uploader(
    "Качете файла с доставки (Excel или CSV)",
    type=["xlsx", "csv"],
    key="delivery_file"
)

if delivery_file is not None:
    try:
        if delivery_file.name.endswith('.csv'):
            df_delivery = pd.read_csv(delivery_file, dtype=str)
        else:
            df_delivery = pd.read_excel(delivery_file, dtype=str)

        df_delivery.columns = df_delivery.columns.str.strip()

        st.write("---")
        st.write("## 🚚 2. Доставки")
        st.write(
            "Качете таблица с доставките. Приложението ще сравни доставеното "
            "количество с продаденото количество от точка 1."
        )

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

        delivery_name_default = find_column(
            df_delivery.columns,
            ['Материал', 'Наименование', 'Име', 'Име на кабела',
             'Описание', 'Cable Name', 'Material']
        )

        delivery_code_default = find_column(
            df_delivery.columns,
            ['САП код', 'SAP код', 'SAP', 'ЕК Номер', 'ЕК номер',
             'Материален номер', 'Material Code']
        )

        delivery_qty_default = find_column(
            df_delivery.columns,
            ['Количество', 'Колич.', 'Количеството', 'Количество (м)',
             'Колич.по документ', 'Quantity', 'Qty', 'Метри', 'МЕТРИ']
        )

        delivery_article_default = find_column(
            df_delivery.columns,
            ['Артикулен номер', 'Артикул', 'Номер артикул',
             'Article Number', 'Article No', 'Item Number', 'Item No', 'SKU']
        )

        delivery_warehouse_default = find_column(
            df_delivery.columns,
            ['Склад', 'Склад получател', 'Място на съхранение', 'Warehouse',
             'Storage Location', 'Plant']
        )

        delivery_date_default = find_column(
            df_delivery.columns,
            ['Дата', 'Дата на доставка', 'Дата документ', 'Дата на документа',
             'Posting Date', 'Document Date', 'Delivery Date']
        )

        st.write("### 🔍 Настройка на колоните от файла с доставки")

        dcol1, dcol2, dcol3, dcol4, dcol5, dcol6 = st.columns(6)

        with dcol1:
            delivery_name_col = st.selectbox(
                "Колона с име на продукта:",
                df_delivery.columns,
                index=int(df_delivery.columns.get_loc(delivery_name_default)),
                key="delivery_name_col"
            )

        with dcol2:
            code_idx = (list(df_delivery.columns).index(delivery_code_default) + 1) if delivery_code_default in df_delivery.columns else 0
            delivery_code_col = st.selectbox(
                "Колона със САП код:",
                ["— Няма —"] + list(df_delivery.columns),
                index=code_idx,
                key="delivery_code_col"
            )

        with dcol3:
            delivery_qty_col = st.selectbox(
                "Колона с доставено количество:",
                df_delivery.columns,
                index=int(df_delivery.columns.get_loc(delivery_qty_default)),
                key="delivery_qty_col"
            )

        with dcol4:
            delivery_article_options = ["— Няма —"] + list(df_delivery.columns)
            delivery_article_index = (
                delivery_article_options.index(delivery_article_default)
                if delivery_article_default in delivery_article_options else 0
            )
            delivery_article_col = st.selectbox(
                "Колона с АРТИКУЛЕН НОМЕР:",
                delivery_article_options,
                index=delivery_article_index,
                key="delivery_article_col"
            )

        with dcol5:
            delivery_warehouse_options = ["— Всички складове —"] + list(df_delivery.columns)
            delivery_warehouse_index = (
                delivery_warehouse_options.index(delivery_warehouse_default)
                if delivery_warehouse_default in delivery_warehouse_options else 0
            )
            delivery_warehouse_col = st.selectbox(
                "Колона със склад:",
                delivery_warehouse_options,
                index=delivery_warehouse_index,
                key="delivery_warehouse_col"
            )

        with dcol6:
            delivery_date_options = ["— Няма дата —"] + list(df_delivery.columns)
            delivery_date_index = (
                delivery_date_options.index(delivery_date_default)
                if delivery_date_default in delivery_date_options else 0
            )
            delivery_date_col = st.selectbox(
                "Колона с дата:",
                delivery_date_options,
                index=delivery_date_index,
                key="delivery_date_col"
            )

        df_delivery = df_delivery[df_delivery[delivery_name_col].notna()].copy()
        df_delivery = df_delivery[
            df_delivery[delivery_name_col].astype(str).str.strip() != ''
        ]

        df_delivery['Delivery_Name_Clean'] = (
            df_delivery[delivery_name_col].astype(str).str.strip()
        )
        df_delivery['Delivery_Qty_Clean'] = pd.to_numeric(
            df_delivery[delivery_qty_col], errors='coerce'
        ).fillna(0)

        if delivery_code_col != "— Няма —":
            df_delivery['Delivery_Code_Clean'] = (
                df_delivery[delivery_code_col]
                .astype(str)
                .str.strip()
                .str.upper()
                .str.replace('.0', '', regex=False)
            )
        else:
            df_delivery['Delivery_Code_Clean'] = ""

        if delivery_article_col != "— Няма —":
            df_delivery['Delivery_Article_Clean'] = (
                df_delivery[delivery_article_col].astype(str).str.strip().str.upper()
                .str.replace(r'\.0$', '', regex=True)
            )
        else:
            df_delivery['Delivery_Article_Clean'] = ""

        if delivery_warehouse_col != "— Всички складове —":
            df_delivery['Delivery_Warehouse_Clean'] = df_delivery[delivery_warehouse_col].apply(clean_warehouse_name)
        else:
            df_delivery['Delivery_Warehouse_Clean'] = "Всички складове"

        if delivery_date_col != "— Няма дата —":
            df_delivery['Delivery_Date_Clean'] = pd.to_datetime(
                df_delivery[delivery_date_col],
                errors='coerce',
                dayfirst=True
            )

            valid_dates = df_delivery['Delivery_Date_Clean'].dropna()

            if len(valid_dates) > 0:
                min_date = valid_dates.min().date()
                max_date = valid_dates.max().date()

                st.write("### 📅 Период на доставките")

                period_col1, period_col2 = st.columns(2)

                with period_col1:
                    delivery_period_start = st.date_input(
                        "От дата:",
                        value=min_date,
                        min_value=min_date,
                        max_value=max_date,
                        key="delivery_period_start"
                    )

                with period_col2:
                    delivery_period_end = st.date_input(
                        "До дата:",
                        value=max_date,
                        min_value=min_date,
                        max_value=max_date,
                        key="delivery_period_end"
                    )

                if delivery_period_start > delivery_period_end:
                    st.error("❌ Началната дата не може да бъде след крайната дата.")
                    delivery_period_start = min_date
                    delivery_period_end = max_date

                delivery_filtered = df_delivery[
                    (df_delivery['Delivery_Date_Clean'].dt.date >= delivery_period_start) &
                    (df_delivery['Delivery_Date_Clean'].dt.date <= delivery_period_end)
                ].copy()

                st.caption(
                    f"Показани доставки: {delivery_period_start.strftime('%d.%m.%Y')} "
                    f"– {delivery_period_end.strftime('%d.%m.%Y')}"
                )
            else:
                delivery_filtered = df_delivery.copy()
                st.warning(
                    "⚠️ Колоната за дата е избрана, но не успях да разпозная валидни дати. "
                    "Ще бъдат използвани всички доставки от файла."
                )
        else:
            delivery_filtered = df_delivery.copy()
            st.info(
                "ℹ️ Във файла няма използвана колона за дата. "
                "Ще бъдат използвани всички доставки от файла."
            )

        selected_delivery_warehouse = "Всички складове"
        if delivery_warehouse_col != "— Всички складове —":
            warehouse_values = sorted(
                df_delivery['Delivery_Warehouse_Clean'].dropna().astype(str).unique().tolist()
            )
            selected_delivery_warehouse = st.selectbox(
                "Филтрирай доставките по склад:",
                ["Всички складове"] + warehouse_values,
                key="delivery_warehouse_filter"
            )
            if selected_delivery_warehouse != "Всички складове":
                delivery_filtered = delivery_filtered[
                    delivery_filtered['Delivery_Warehouse_Clean'] == selected_delivery_warehouse
                ].copy()

        if 'final_df' in locals():
            sales_compare = final_df.copy()

            if delivery_warehouse_col != "— Всички складове —" and selected_delivery_warehouse != "Всички складове":
                sales_compare = sales_compare[
                    sales_compare['Warehouse_Clean'] == selected_delivery_warehouse
                ].copy()

            sales_compare['Sales_Name_Clean'] = (
                sales_compare['Cable_Name_Clean'].astype(str).str.strip()
            )
            sales_compare['Sales_Qty_Clean'] = pd.to_numeric(
                sales_compare['Quantity_m'], errors='coerce'
            ).fillna(0)

            # --- СЪПОСТАВКА ПО ИМЕ / АРТИКУЛЕН КОД ---
            if delivery_article_col != "— Няма —":
                delivery_summary = delivery_filtered.groupby(
                    ['Delivery_Article_Clean', 'Delivery_Name_Clean'],
                    dropna=False
                )['Delivery_Qty_Clean'].sum().reset_index()

                delivery_summary = delivery_summary.rename(
                    columns={
                        'Delivery_Article_Clean': 'Compare_Article',
                        'Delivery_Name_Clean': 'Име',
                        'Delivery_Qty_Clean': 'Доставено'
                    }
                )

                # Продажбите се свързват по ИМЕ на кабела
                sales_by_name = sales_compare.groupby('Sales_Name_Clean')['Sales_Qty_Clean'].sum().to_dict()
                delivery_summary['Sold_Qty'] = delivery_summary['Име'].map(sales_by_name).fillna(0)
                delivery_summary['Compare_Code'] = delivery_summary['Compare_Article']

            elif delivery_code_col != "— Няма —":
                delivery_summary = delivery_filtered.groupby(
                    ['Delivery_Code_Clean', 'Delivery_Name_Clean'],
                    dropna=False
                )['Delivery_Qty_Clean'].sum().reset_index()

                delivery_summary = delivery_summary.rename(
                    columns={
                        'Delivery_Code_Clean': 'Compare_Code',
                        'Delivery_Name_Clean': 'Име',
                        'Delivery_Qty_Clean': 'Доставено'
                    }
                )

                sales_by_code = sales_compare.groupby('Clean_Material')['Sales_Qty_Clean'].sum().reset_index()
                sales_by_code.columns = ['Compare_Code', 'Sold_Qty']

                delivery_summary = delivery_summary.merge(
                    sales_by_code,
                    on='Compare_Code',
                    how='left'
                )
                delivery_summary['Sold_Qty'] = delivery_summary['Sold_Qty'].fillna(0)

            else:
                delivery_summary = delivery_filtered.groupby(
                    'Delivery_Name_Clean',
                    dropna=False
                )['Delivery_Qty_Clean'].sum().reset_index()

                delivery_summary = delivery_summary.rename(
                    columns={
                        'Delivery_Name_Clean': 'Име',
                        'Delivery_Qty_Clean': 'Доставено'
                    }
                )

                sales_by_name = sales_compare.groupby('Sales_Name_Clean')['Sales_Qty_Clean'].sum().reset_index()
                sales_by_name.columns = ['Име', 'Sold_Qty']

                delivery_summary = delivery_summary.merge(
                    sales_by_name,
                    on='Име',
                    how='left'
                )

            delivery_summary['Sold_Qty'] = delivery_summary['Sold_Qty'].fillna(0)
            delivery_summary['Доставено'] = pd.to_numeric(
                delivery_summary['Доставено'], errors='coerce'
            ).fillna(0)

            delivery_summary['Остатък'] = (
                delivery_summary['Доставено'] - delivery_summary['Sold_Qty']
            )

            # -----------------------------------------------------
            # 🔍 ТЪРСЕНЕ ПО АРТИКУЛЕН КОД ИЛИ ИМЕ
            # -----------------------------------------------------
            st.write("---")
            st.write("### 🔎 Търсене на конкретен кабел по Артикулен код или име")
            search_query = st.text_input("Въведете Артикулен код или част от името на кабела:", "").strip().upper()

            if search_query:
                mask_code = delivery_summary['Compare_Code'].astype(str).str.upper().str.contains(search_query, na=False) if 'Compare_Code' in delivery_summary.columns else False
                mask_name = delivery_summary['Име'].astype(str).str.upper().str.contains(search_query, na=False)
                search_results = delivery_summary[mask_code | mask_name]

                if not search_results.empty:
                    st.success(f"Намерени {len(search_results)} съвпадения за '{search_query}':")
                    st.dataframe(search_results, use_container_width=True, hide_index=True)
                else:
                    st.warning(f"⚠️ Не са намерени резултати за '{search_query}'.")

            # -----------------------------------------------------
            # ГЛАВНА ТАБЛИЦА С ДАННИ
            # -----------------------------------------------------
            wh_label = f"за склад '{selected_delivery_warehouse}'" if selected_delivery_warehouse != "Всички складове" else "за всички складове"
            st.write(f"### 📊 Сравнение: Доставени vs Продадени количества ({wh_label})")

            col_del_kpi1, col_del_kpi2, col_del_kpi3 = st.columns(3)
            tot_del = delivery_summary['Доставено'].sum()
            tot_sold_comp = delivery_summary['Sold_Qty'].sum()
            tot_diff = tot_del - tot_sold_comp

            col_del_kpi1.metric("Общо доставени (м)", f"{tot_del:,.0f}")
            col_del_kpi2.metric("Общо продадени (м)", f"{tot_sold_comp:,.0f}")
            col_del_kpi3.metric("Разлика / Остатък (м)", f"{tot_diff:,.0f}")

            formatted_del_summary = pd.DataFrame()
            if 'Compare_Code' in delivery_summary.columns:
                formatted_del_summary['Артикулен код'] = delivery_summary['Compare_Code']
            formatted_del_summary['Наименование на кабела'] = delivery_summary['Име']
            formatted_del_summary['Доставено (Метри)'] = delivery_summary['Доставено'].map('{:,.0f}'.format)
            formatted_del_summary['Продадено (Метри)'] = delivery_summary['Sold_Qty'].map('{:,.0f}'.format)
            formatted_del_summary['Остатък / Баланс (Метри)'] = delivery_summary['Остатък'].map('{:,.0f}'.format)

            st.dataframe(formatted_del_summary, use_container_width=True, hide_index=True)

            del_csv = delivery_summary.to_csv(index=False).encode('utf-8-sig')
            st.download_button(
                label="📥 Изтегли съпоставката на доставките (CSV)",
                data=del_csv,
                file_name=f"Доставки_vs_Продажби_{selected_delivery_warehouse}.csv",
                mime="text/csv",
            )

            # -----------------------------------------------------
            # 🏢 ПОДРОБНА МАТРИЧНА СПРАВКА ПО ВСИЧКИ СКЛАДОВЕ
            # (Доставките са по Артикулен код, Продажбите по Име на кабела)
            # -----------------------------------------------------
            if delivery_warehouse_col != "— Всички складове —":
                st.write("---")
                st.write("### 🏢 Подробна матрична справка по Всички Складове (по Артикулен код)")

                art_key = 'Delivery_Article_Clean' if delivery_article_col != "— Няма —" else ('Delivery_Code_Clean' if delivery_code_col != "— Няма —" else 'Delivery_Name_Clean')

                # 1. Доставки по Артикулен код + Име + Склад
                del_by_wh = df_delivery.groupby([art_key, 'Delivery_Name_Clean', 'Delivery_Warehouse_Clean'])['Delivery_Qty_Clean'].sum().reset_index()
                del_by_wh.columns = ['Артикулен код', 'Наименование', 'Warehouse', 'Доставено']

                # 2. Продажби по Име + Склад (тъй като в продажбите са по ЕК/САП код, ползваме името за мост)
                sales_by_name_wh = final_df.groupby(['Cable_Name_Clean', 'Warehouse_Clean'])['Quantity_m'].sum().reset_index()
                sales_by_name_wh.columns = ['Наименование', 'Warehouse', 'Продадено']

                # 3. Обединяваме доставките с продажбите по Име и Склад
                merged_wh = pd.merge(del_by_wh, sales_by_name_wh, on=['Наименование', 'Warehouse'], how='left').fillna(0)
                merged_wh['Остатък'] = merged_wh['Доставено'] - merged_wh['Продадено']

                # 4. Изграждаме Pivot таблиците
                pivot_del = merged_wh.pivot_table(index=['Артикулен код', 'Наименование'], columns='Warehouse', values='Доставено', aggfunc='sum', fill_value=0)
                pivot_sales = merged_wh.pivot_table(index=['Артикулен код', 'Наименование'], columns='Warehouse', values='Продадено', aggfunc='sum', fill_value=0)
                pivot_bal = merged_wh.pivot_table(index=['Артикулен код', 'Наименование'], columns='Warehouse', values='Остатък', aggfunc='sum', fill_value=0)

                pivot_del.columns = [f"Доставено ({c})" for c in pivot_del.columns]
                pivot_sales.columns = [f"Продадено ({c})" for c in pivot_sales.columns]
                pivot_bal.columns = [f"Остатък ({c})" for c in pivot_bal.columns]

                # 5. Крайна сглобка
                multi_wh_df = pd.concat([pivot_del, pivot_sales, pivot_bal], axis=1).fillna(0).reset_index()
                st.dataframe(multi_wh_df, use_container_width=True)

        else:
            st.info("ℹ️ За да видите сравнението между доставено и продадено, моля качете и месечния файл с продажби от точка 1.")

    except Exception as e:
        st.error(f"Грешка при обработката на доставките: {e}")
