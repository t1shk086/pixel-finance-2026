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

        # Автоматично разпознаване на възможни колони
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

        delivery_date_default = find_column(
            df_delivery.columns,
            ['Дата', 'Дата на доставка', 'Дата документ', 'Дата на документа',
             'Posting Date', 'Document Date', 'Delivery Date']
        )

        st.write("### 🔍 Настройка на колоните от файла с доставки")

        dcol1, dcol2, dcol3, dcol4 = st.columns(4)

        with dcol1:
            delivery_name_col = st.selectbox(
                "Колона с име на продукта:",
                df_delivery.columns,
                index=int(df_delivery.columns.get_loc(delivery_name_default)),
                key="delivery_name_col"
            )

        with dcol2:
            delivery_code_col = st.selectbox(
                "Колона със САП код:",
                ["— Няма —"] + list(df_delivery.columns),
                index=(list(df_delivery.columns).index(delivery_code_default) + 1)
                if delivery_code_default in df_delivery.columns else 0,
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

        # Подготовка на доставките
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

        # Период на доставките
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

        # =====================================================
        # Продажбите от точка 1
        # =====================================================
        if 'final_df' in locals():
            sales_compare = final_df.copy()
            sales_compare['Sales_Name_Clean'] = (
                sales_compare['Cable_Name_Clean'].astype(str).str.strip()
            )
            sales_compare['Sales_Qty_Clean'] = pd.to_numeric(
                sales_compare['Quantity_m'], errors='coerce'
            ).fillna(0)

            # Основна връзка по САП код, ако има такъв и в двата файла.
            # Ако няма код в доставките, използваме името.
            delivery_has_codes = (
                delivery_code_col != "— Няма —" and
                delivery_filtered['Delivery_Code_Clean'].astype(str).str.strip().ne('').any()
            )

            # Продажби по код
            sales_by_code = sales_compare.groupby(
                'Clean_Material', dropna=False
            )['Sales_Qty_Clean'].sum().reset_index()
            sales_by_code = sales_by_code.rename(
                columns={
                    'Clean_Material': 'Compare_Code',
                    'Sales_Qty_Clean': 'Sold_Qty'
                }
            )

            # Продажби по име
            sales_by_name = sales_compare.groupby(
                'Sales_Name_Clean', dropna=False
            )['Sales_Qty_Clean'].sum().reset_index()
            sales_by_name = sales_by_name.rename(
                columns={
                    'Sales_Name_Clean': 'Compare_Name',
                    'Sales_Qty_Clean': 'Sold_Qty'
                }
            )

            if delivery_has_codes:
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

                delivery_summary = delivery_summary.merge(
                    sales_by_code,
                    on='Compare_Code',
                    how='left'
                )

                # Ако кодът не е намерен в продажбите, пробваме по име.
                delivery_summary['Sold_Qty'] = delivery_summary['Sold_Qty'].fillna(0)

                sales_name_lookup = sales_by_name.set_index('Compare_Name')['Sold_Qty'].to_dict()

                missing_sales_mask = delivery_summary['Sold_Qty'] == 0
                delivery_summary.loc[missing_sales_mask, 'Sold_Qty'] = (
                    delivery_summary.loc[missing_sales_mask, 'Име']
                    .map(sales_name_lookup)
                    .fillna(0)
                )

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

                delivery_summary = delivery_summary.merge(
                    sales_by_name.rename(columns={'Compare_Name': 'Име'}),
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

            # Ако има продажби на продукт, за който няма доставка в качения файл,
            # добавяме го, за да може потребителят да види и отрицателен остатък.
            if delivery_has_codes:
                delivered_codes = set(
                    delivery_summary['Compare_Code'].astype(str)
                )

                sales_extra = sales_by_code[
                    ~sales_by_code['Compare_Code'].astype(str).isin(delivered_codes)
                ].copy()

                if not sales_extra.empty:
                    sales_extra['Име'] = (
                        sales_extra['Compare_Code']
                        .map(
                            sales_compare.drop_duplicates('Clean_Material')
                            .set_index('Clean_Material')['Cable_Name_Clean']
                            .to_dict()
                        )
                        .fillna(sales_extra['Compare_Code'])
                    )
                    sales_extra['Доставено'] = 0
                    sales_extra['Остатък'] = -sales_extra['Sold_Qty']
                    sales_extra = sales_extra[
                        ['Compare_Code', 'Име', 'Доставено', 'Sold_Qty', 'Остатък']
                    ]
                    delivery_summary = pd.concat(
                        [delivery_summary, sales_extra],
                        ignore_index=True
                    )
            else:
                delivered_names = set(delivery_summary['Име'].astype(str))
                sales_extra = sales_by_name[
                    ~sales_by_name['Compare_Name'].astype(str).isin(delivered_names)
                ].copy()

                if not sales_extra.empty:
                    sales_extra['Име'] = sales_extra['Compare_Name']
                    sales_extra['Доставено'] = 0
                    sales_extra['Остатък'] = -sales_extra['Sold_Qty']
                    sales_extra = sales_extra[
                        ['Име', 'Доставено', 'Sold_Qty', 'Остатък']
                    ]
                    delivery_summary = pd.concat(
                        [delivery_summary, sales_extra],
                        ignore_index=True
                    )

            # Подреждане и форматиране
            delivery_summary['Продадено'] = delivery_summary['Sold_Qty']

            # Запазваме ЕК/САП кода за търсене, когато е наличен.
            # Ако файлът с доставки няма код, оставяме колоната празна.
            if 'Compare_Code' in delivery_summary.columns:
                delivery_summary['ЕК код'] = (
                    delivery_summary['Compare_Code'].astype(str).str.strip()
                )
            else:
                delivery_summary['ЕК код'] = ""

            display_columns = ['ЕК код', 'Име', 'Доставено', 'Продадено', 'Остатък']
            delivery_display = delivery_summary[display_columns].copy()

            delivery_display = delivery_display.sort_values(
                by='Доставено',
                ascending=False
            ).reset_index(drop=True)

            # KPI
            total_delivered = delivery_display['Доставено'].sum()
            total_sold = delivery_display['Продадено'].sum()
            total_remaining = delivery_display['Остатък'].sum()

            st.write("### 📊 Доставки срещу продажби")
            k1, k2, k3 = st.columns(3)

            k1.metric(
                "Общо доставено",
                f"{total_delivered:,.0f}"
            )
            k2.metric(
                "Общо продадено",
                f"{total_sold:,.0f}"
            )
            k3.metric(
                "Остатък",
                f"{total_remaining:,.0f}"
            )

            st.write("### 📦 Справка по име")
            st.caption(
                "Доставено = доставеното количество за избрания период. "
                "Продадено = количеството от точка 1. "
                "Остатък = Доставено − Продадено."
            )

            formatted_delivery = delivery_display.copy()
            formatted_delivery['Доставено'] = formatted_delivery['Доставено'].map(
                '{:,.0f}'.format
            )
            formatted_delivery['Продадено'] = formatted_delivery['Продадено'].map(
                '{:,.0f}'.format
            )
            formatted_delivery['Остатък'] = delivery_display['Остатък'].map(
                '{:,.0f}'.format
            )

            st.dataframe(
                formatted_delivery,
                use_container_width=True,
                hide_index=True
            )

            # Търсене на продукт по ЕК код
            st.write("### 🔎 Проверка на конкретен продукт")
            search_ek_code = st.text_input(
                "Въведи ЕК код:",
                placeholder="Например: 123456",
                key="delivery_ek_code_search"
            ).strip().upper()

            if search_ek_code:
                code_values = delivery_display['ЕК код'].astype(str).str.strip().str.upper()
                selected_row = delivery_display[code_values == search_ek_code]

                # Ако файлът с доставки няма кодове, търсим кода в продажбите
                # и използваме намереното име, за да намерим реда в справката.
                if selected_row.empty and not delivery_has_codes and 'final_df' in locals():
                    sales_code_rows = sales_compare[
                        sales_compare['Clean_Material'].astype(str).str.strip().str.upper()
                        == search_ek_code
                    ]
                    if not sales_code_rows.empty:
                        matching_names = sales_code_rows['Sales_Name_Clean'].dropna().astype(str).unique()
                        selected_row = delivery_display[
                            delivery_display['Име'].astype(str).isin(matching_names)
                        ]

                if selected_row.empty:
                    st.info(
                        "Не е намерен продукт с този ЕК код. Проверете кода или дали "
                        "файлът с доставките съдържа правилната колона за код."
                    )
                else:
                    # Ако има няколко реда за един код, показваме общите количества.
                    row = selected_row[['Доставено', 'Продадено', 'Остатък']].sum()
                    st.write(f"**Продукт:** {', '.join(selected_row['Име'].astype(str).unique())}")
                    pc1, pc2, pc3 = st.columns(3)

                    pc1.metric(
                        "Доставено за периода",
                        f"{row['Доставено']:,.0f}"
                    )
                    pc2.metric(
                        "Продадено от т.1",
                        f"{row['Продадено']:,.0f}"
                    )
                    pc3.metric(
                        "Остатък",
                        f"{row['Остатък']:,.0f}"
                    )
            else:
                st.caption("Въведи ЕК кода в полето, за да видиш доставено, продадено и остатък.")

            @st.cache_data
            def convert_delivery_df(df):
                return df.to_csv(index=False).encode('utf-8-sig')

            st.download_button(
                label="📥 Изтегли справката за доставки (CSV)",
                data=convert_delivery_df(delivery_display),
                file_name="Справка_Доставки_Продажби.csv",
                mime="text/csv",
                key="download_delivery_report"
            )

        else:
            st.warning(
                "⚠️ За да се сравнят доставките с продажбите, първо трябва "
                "да бъде качен файлът с продажби от точка 1."
            )

    except Exception as e:
        st.error(f"Грешка при обработката на файла с доставки: {e}")
