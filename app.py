import streamlit as st
import pandas as pd
import io

st.set_page_config(page_title="Гъвкаво Търсене в Таблици", layout="wide", page_icon="🔄")

st.title("🔄 Гъвкаво свързване на таблици по ваш критерий")
st.write("Качете вашите файлове и изберете ръчно коя колона от коя таблица да се търси и свързва.")

# 1. Страничен панел за качване на файлове
st.sidebar.header("1. Зареждане на файлове")
uploaded_files = st.sidebar.file_uploader(
    "Качете Excel файлове (.xlsx, .xls)", 
    type=["xlsx", "xls"], 
    accept_multiple_files=True
)

dataframes = {}

if uploaded_files:
    for uploaded_file in uploaded_files:
        try:
            # Четем всичко като текст, за да запазим точния вид на кодовете и данните
            df = pd.read_excel(uploaded_file, dtype=str)
            df.columns = [str(c).strip() for c in df.columns]
            dataframes[uploaded_file.name] = df
        except Exception as e:
            st.sidebar.error(f"Грешка при четене на {uploaded_file.name}: {e}")

    if len(dataframes) >= 2:
        file_list = list(dataframes.keys())
        
        st.subheader("🛠️ Настройка на критериите за търсене")
        
        # Разделяме екрана на две колони за избор на Източник и Референция
        col_left, col_right = st.columns(2)
        
        with col_left:
            st.markdown("### 📄 ТАБЛИЦА 1 (Основна)")
            main_f = st.selectbox("Изберете основната таблица:", file_list, key="main_file")
            # Динамично взимаме колоните от избрания първи файл
            main_cols = dataframes[main_f].columns.tolist()
            main_search_col = st.selectbox("Търси стойностите от колона:", main_cols, key="main_col")
            
        with col_right:
            st.markdown("### 📄 ТАБЛИЦА 2 (Данни за проверка)")
            ref_f = st.selectbox("Изберете таблицата, в която ще се търси:", file_list, key="ref_file")
            # Динамично взимаме колоните от втория файл
            ref_cols = dataframes[ref_f].columns.tolist()
            ref_search_col = st.selectbox("Сравни ги със стойностите в колона:", ref_cols, key="ref_col")

        st.divider()

        # Проверка за еднакви файлове (предупреждение)
        if main_f == ref_f:
            st.warning("⚠️ Избрали сте един и същ файл за Таблица 1 и Таблица 2. Уверете се, че това е вашето желание.")

        try:
            df_main = dataframes[main_f].copy()
            df_ref = dataframes[ref_f].copy()

            # Правим свързването (LEFT JOIN) по избраните от потребителя колони
            # suffixes помага да се разграничат еднакви колони, ако има такива
            merged_df = pd.merge(
                df_main, 
                df_ref, 
                left_on=main_search_col, 
                right_on=ref_search_col, 
                how='left', 
                suffixes=('_табл1', '_табл2')
            )
            
            st.subheader("🎯 Всички намерени резултати")
            st.info("💡 Можете да редактирате всяка клетка директно в таблицата долу, ако се налага!")
            
            # Показваме интерактивната таблица за преглед и редакция
            edited_df = st.data_editor(merged_df, use_container_width=True, num_rows="dynamic")

            st.divider()
            st.subheader("💾 Експорт на резултатите")
            
            # Подготовка за изтегляне на новата таблица
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                edited_df.to_excel(writer, index=False)
            
            st.download_button(
                label="📥 Изтегли резултатите в нов Excel файл",
                data=buffer.getvalue(),
                file_name="Резултати_Свързване.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
            
        except Exception as e:
            st.error(f"Възникна грешка при свързването на данните: {e}")
            
    else:
        st.info("💡 За да започнете, качете **поне 2 Excel файла** от страничното меню вляво.")
else:
    st.info("👋 Качете вашите Excel таблици от менюто вляво, за да изберете критериите за търсене.")
