import streamlit as st
import pandas as pd
import io

st.set_page_config(page_title="Продуктов Мениджър", layout="wide", page_icon="📦")

st.title("📦 Интелигентна Търсачка и Мениджър на Продукти")
st.write("Качете вашите Excel таблици (за кодове, реални имена и вътрешни имена), за да ги свържете лесно.")

# 1. Зареждане на файлове
st.sidebar.header("1. Зареждане на таблици")
uploaded_files = st.sidebar.file_uploader(
    "Изберете Excel файлове (.xlsx, .xls)", 
    type=["xlsx", "xls"], 
    accept_multiple_files=True
)

dataframes = {}

if uploaded_files:
    for uploaded_file in uploaded_files:
        try:
            # Четем всичко като текст, за да не се губят водещи нули в кодовете
            df = pd.read_excel(uploaded_file, dtype=str)
            df.columns = [str(c).strip() for c in df.columns]
            dataframes[uploaded_file.name] = df
        except Exception as e:
            st.sidebar.error(f"Грешка при четене на {uploaded_file.name}: {e}")

    # Показване на заредените файлове в страничния панел
    if dataframes:
        st.sidebar.success(f"Успешно заредени файлове: {len(dataframes)}")
        for name in dataframes.keys():
            st.sidebar.text(f"📄 {name}")

    # СЪЗДАВАНЕ НА ДВЕ КОЛОНИ В ОСНОВНИЯ ЕКРАН
    col_left, col_right = st.columns([1, 2])

    # ЛЯВА КОЛОНА: Допълнителни функции (Свързване на таблици)
    with col_left:
        st.subheader("🔗 Допълнителни функции (Свързване)")
        file_list = list(dataframes.keys())
        
        main_f = st.selectbox("Основна таблица (без имена):", file_list, key="main")
        ref_f = st.selectbox("Референтна таблица (с имена):", file_list, key="ref")
        join_col = st.text_input("Име на общата колона с Код:", value="Код").strip()
        
        if st.button("🔗 Автоматично сглобяване и Експорт"):
            if main_f and ref_f and join_col:
                df_main = dataframes[main_f].copy()
                df_ref = dataframes[ref_f].copy()
                
                if join_col not in df_main.columns or join_col not in df_ref.columns:
                    st.error(f"Колоната '{join_col}' не съществува в някой от файловете!")
                else:
                    try:
                        # Свързване тип VLOOKUP / LEFT JOIN
                        merged_df = pd.merge(df_main, df_ref, on=join_col, how='left', suffixes=('_основна', '_референция'))
                        
                        # Генериране на Excel файл в паметта
                        buffer = io.BytesIO()
                        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                            merged_df.to_excel(writer, index=False)
                        
                        st.success("Таблиците бяха сглобени успешно!")
                        st.download_button(
                            label="📥 Изтегли обединения Excel файл",
                            data=buffer.getvalue(),
                            file_name="Обединен_Файл_Продукти.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        )
                    except Exception as e:
                        st.error(f"Грешка при сглобяването: {e}")
            else:
                st.warning("Моля, попълнете всички полета за свързване.")

    # ДЯСНА КОЛОНА: Бързо търсене (Кръстосана проверка)
    with col_right:
        st.subheader("🔍 Бързо търсене на код или близко име")
        search_value = st.text_input("Въведете търсен код (напр. 123) или име:").strip()
        
        match_type = st.radio(
            "Тип търсене:",
            ("Частично съвпадение (Близки имена)", "Точно съвпадение (по код)"),
            horizontal=True
        )

        if search_value:
            found_any = False
            exact = (match_type == "Точно съвпадение (по код)")
            
            # Търсене във всички таблици едновременно
            for file_name, df in dataframes.items():
                mask = pd.Series(False, index=df.index)
                
                for col in df.columns:
                    col_series = df[col].astype(str).str.strip()
                    if exact:
                        mask |= (col_series.str.lower() == search_value.lower())
                    else:
                        mask |= (col_series.str.contains(search_value, case=False, na=False))
                
                results = df[mask]
                
                if not results.empty:
                    found_any = True
                    st.info(f"Съвпадения във файл: **{file_name}**")
                    st.dataframe(results, use_container_width=True)
            
            if not found_any:
                st.warning("Няма намерени съвпадения в нито една таблица.")
else:
    st.info("💡 За да започнете, качете вашите Excel файлове от страничното меню вляво.")
