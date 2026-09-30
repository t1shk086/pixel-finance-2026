import streamlit as st
import pandas as pd
import io

st.set_page_config(page_title="Прецизно Свързване", layout="wide", page_icon="🎯")

st.title("🎯 Прецизно извличане на данни между Excel таблици")
st.write("Свържете две таблици по общ критерий и изберете ръчно кои точно колони да вземете от втората таблица.")

# 1. Страничен панел за качване на файлове
st.sidebar.header("1. Зареждане на файлове")
uploaded_files = st.sidebar.file_uploader(
    "Качете вашите Excel файлове:", 
    type=["xlsx", "xls"], 
    accept_multiple_files=True
)

dataframes = {}

if uploaded_files:
    for uploaded_file in uploaded_files:
        try:
            # Четем всичко като текст, за да запазим точния вид на кодовете (водещи нули и т.н.)
            df = pd.read_excel(uploaded_file, dtype=str)
            df.columns = [str(c).strip() for c in df.columns]
            dataframes[uploaded_file.name] = df
        except Exception as e:
            st.sidebar.error(f"Грешка при четене на {uploaded_file.name}: {e}")

    if len(dataframes) >= 2:
        file_list = list(dataframes.keys())
        
        st.subheader("🛠️ Стъпка 1: Настройка на критерия за съвпадение")
        col_left, col_right = st.columns(2)
        
        with col_left:
            main_f = st.selectbox("Основна таблица (Таблица 1):", file_list, key="main_file")
            main_cols = dataframes[main_f].columns.tolist()
            main_search_col = st.selectbox("Вземи стойностите от колона:", main_cols, key="main_col")
            
        with col_right:
            ref_f = st.selectbox("Таблица, от която ще взимаме данни (Таблица 2):", file_list, key="ref_file")
            ref_cols = dataframes[ref_f].columns.tolist()
            ref_search_col = st.selectbox("Търси ги и ги сравни с колона:", ref_cols, key="ref_col")

        st.divider()

        if main_f == ref_f:
            st.warning("⚠️ Избрали сте един и същ файл за Таблица 1 и Таблица 2.")
        
        # --- НОВАТА СЕКЦИЯ ЗА РЪЧЕН ИЗБОР НА КОЛОНИ ---
        st.subheader("📋 Стъпка 2: Избор на данни за извличане")
        
        # Списък с колони от Таблица 2, които потребителят може да избере (без самата колона за връзка)
        available_cols_to_pull = [c for c in ref_cols if c != ref_search_col]
        
        if available_cols_to_pull:
            selected_cols_to_pull = st.multiselect(
                "Кои колони искате да вземете от Таблица 2 и да добавите към Таблица 1?",
                options=available_cols_to_pull,
                default=[available_cols_to_pull[0]] if available_cols_to_pull else []
            )
            
            if not selected_cols_to_pull:
                st.info("💡 Моля, изберете поне една колона от списъка по-горе, за да я извлечете.")
            else:
                try:
                    df_main = dataframes[main_f].copy()
                    df_ref = dataframes[ref_f].copy()

                    # Взимаме от Таблица 2 само колоната за връзка + колоните, които потребителят е избрал
                    cols_to_keep = [ref_search_col] + selected_cols_to_pull
                    df_ref_filtered = df_ref[cols_to_keep]

                    # Премахваме дубликати в Таблица 2 по търсената колона, за да не се размножават редовете в Таблица 1
                    df_ref_filtered = df_ref_filtered.drop_duplicates(subset=[ref_search_col])

                    # Извършваме свързването (VLOOKUP / LEFT JOIN)
                    merged_df = pd.merge(
                        df_main, 
                        df_ref_filtered, 
                        left_on=main_search_col, 
                        right_on=ref_search_col, 
                        how='left'
                    )

                    # Ако името на колоната за връзка в двете таблици е различно, може да премахнем дублиращата се колона от Таблица 2
                    if main_search_col != ref_search_col and ref_search_col in merged_df.columns:
                        merged_df = merged_df.drop(columns=[ref_search_col])

                    st.divider()
                    st.subheader("🎯 Резултат (Таблица 1 + Извлечените данни)")
                    st.caption("Можете да редактирате клетките директно в таблицата, ако се налага промяна в цени или имена.")
                    
                    # Показваме интерактивния редактор
                    edited_df = st.data_editor(merged_df, use_container_width=True, num_rows="dynamic")

                    st.divider()
                    st.subheader("💾 Запис на готовия ценоразпис")
                    
                    # Подготовка за изтегляне
                    buffer = io.BytesIO()
                    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                        edited_df.to_excel(writer, index=False)
                    
                    st.download_button(
                        label="📥 Изтегли актуализирания файл",
                        data=buffer.getvalue(),
                        file_name="Извлечени_Продукти.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
                    
                except Exception as e:
                    st.error(f"Възникна грешка при свързването на данните: {e}")
        else:
            st.error("Таблица 2 няма други колони за извличане освен колоната за връзка.")
            
    else:
        st.info("💡 Моля, качете **поне 2 Excel файла** от страничното меню вляво.")
else:
    st.info("👋 Качете вашите Excel таблици от менюто вляво, за да започнете.")
