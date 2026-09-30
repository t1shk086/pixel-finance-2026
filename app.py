import streamlit as st
import pandas as pd
import io
from difflib import SequenceMatcher

st.set_page_config(page_title="Умно Свързване", layout="wide", page_icon="🤖")

st.title("🤖 Умно свързване на таблици с приблизително търсене (Fuzzy Match)")
st.write("Свържете две таблици дори когато имената не съвпадат напълно (поради правописни грешки или съкращения).")

# Функция за изчисляване на сходство между два текста (връща стойност от 0.0 до 1.0)
def get_similarity(str1, str2):
    if pd.isna(str1) or pd.isna(str2):
        return 0.0
    return SequenceMatcher(None, str(str1).strip().lower(), str(str2).strip().lower()).ratio()

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
            main_search_col = st.selectbox("Вземи колона за търсене от Таблица 1:", main_cols, key="main_col")
            
        with col_right:
            ref_f = st.selectbox("Таблица с данни за извличане (Таблица 2):", file_list, key="ref_file")
            ref_cols = dataframes[ref_f].columns.tolist()
            ref_search_col = st.selectbox("Сравни я с колона от Таблица 2:", ref_cols, key="ref_col")

        st.divider()

        # Настройки за приблизителното търсене
        st.subheader("🎛️ Стъпка 2: Настройки за интелигентно търсене")
        
        use_fuzzy = st.checkbox("✅ Включи приблизително търсене (ако няма 100% точно съвпадение)", value=True)
        
        threshold = 0.60
        if use_fuzzy:
            threshold = st.slider(
                "Минимален процент на сходство за близки имена:", 
                min_value=0.10, max_value=1.00, value=0.60, step=0.05,
                help="0.60 означава 60% сходство. Колкото по-ниско е числото, толкова по-далечни имена ще свързва."
            )

        # Избор на колони за извличане
        available_cols_to_pull = [c for c in ref_cols if c != ref_search_col]
        selected_cols_to_pull = st.multiselect(
            "Кои колони искате да извлечете от Таблица 2?",
            options=available_cols_to_pull,
            default=[available_cols_to_pull[0]] if available_cols_to_pull else []
        )
        
        if not selected_cols_to_pull:
            st.info("💡 Моля, изберете поне една колона за извличане от списъка по-горе.")
        else:
            if st.button("🚀 Изпълни умно търсене и свързване"):
                with st.spinner("Програмата сканира редовете за близки съвпадения... Моля, изчакайте."):
                    try:
                        df_main = dataframes[main_f].copy()
                        df_ref = dataframes[ref_f].copy()

                        # Подготвяме празни колони в Таблица 1 за новите данни
                        for col in selected_cols_to_pull:
                            df_main[col] = ""
                        df_main["Процент_Сходство"] = ""

                        # Алгоритъм за търсене ред по ред
                        for idx_main, row_main in df_main.iterrows():
                            val_main = str(row_main[main_search_col]).strip()
                            
                            best_match_idx = None
                            best_score = 0.0
                            
                            # 1. Първо пробваме за Точно съвпадение
                            exact_matches = df_ref[df_ref[ref_search_col].str.strip().str.lower() == val_main.lower()]
                            
                            if not exact_matches.empty:
                                best_match_idx = exact_matches.index[0]
                                best_score = 1.0
                            elif use_fuzzy:
                                # 2. Ако няма точно съвпадение, търсим най-близкото по алгоритъм
                                for idx_ref, row_ref in df_ref.iterrows():
                                    val_ref = str(row_ref[ref_search_col]).strip()
                                    score = get_similarity(val_main, val_ref)
                                    
                                    if score > best_score and score >= threshold:
                                        best_score = score
                                        best_match_idx = idx_ref
                            
                            # Ако сме намерили съвпадение (точно или близко), прехвърляме данните
                            if best_match_idx is not None:
                                for col in selected_cols_to_pull:
                                    df_main.at[idx_main, col] = df_ref.at[best_match_idx, col]
                                df_main.at[idx_main, "Процент_Сходство"] = f"{int(best_score * 100)}%"
                            else:
                                df_main.at[idx_main, "Процент_Сходство"] = "Няма съвпадение"

                        st.divider()
                        st.subheader("🎯 Резултат от умното свързване")
                        st.caption("В колона 'Процент_Сходство' виждате колко сигурна е програмата в съвпадението. Можете да коригирате всичко ръчно.")
                        
                        # Показваме интерактивната таблица
                        edited_df = st.data_editor(df_main, use_container_width=True, num_rows="dynamic")

                        # Подготовка за изтегляне
                        buffer = io.BytesIO()
                        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                            edited_df.to_excel(writer, index=False)
                        
                        st.download_button(
                            label="📥 Изтегли готовия файл",
                            data=buffer.getvalue(),
                            file_name="Умно_Свързани_Продукти.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        )
                        
                    except Exception as e:
                        st.error(f"Грешка по време на обработката: {e}")
    else:
        st.info("💡 Моля, качете поне 2 Excel файла от менюто вляво.")
else:
    st.info("👋 Качете вашите ценоразписи и бази данни от менюто вляво, за да започнете.")
