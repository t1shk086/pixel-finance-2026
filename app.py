import streamlit as st
import pandas as pd
import io

st.set_page_config(page_title="Актуализация на Ценоразпис", layout="wide", page_icon="💰")

st.title("💰 Мениджър за Промяна на Ценоразписи")
st.write("Свържете кодовете с реалните имена на продуктите и редактирайте цените директно на екрана.")

# 1. Зареждане на файловете в страничния панел
st.sidebar.header("1. Зареждане на таблици")
uploaded_files = st.sidebar.file_uploader(
    "Качете двата файла (.xlsx, .xls)", 
    type=["xlsx", "xls"], 
    accept_multiple_files=True
)

dataframes = {}

if uploaded_files:
    for uploaded_file in uploaded_files:
        try:
            # Четем всичко като текст за безопасност на кодовете
            df = pd.read_excel(uploaded_file, dtype=str)
            df.columns = [str(c).strip() for c in df.columns]
            dataframes[uploaded_file.name] = df
        except Exception as e:
            st.sidebar.error(f"Грешка при четене на {uploaded_file.name}: {e}")

    if len(dataframes) >= 2:
        file_list = list(dataframes.keys())
        
        st.subheader("🔗 Настройка на връзката между таблиците")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            price_file = st.selectbox("Избери файла с ЦЕНИТЕ (без имена):", file_list, index=0)
        with col2:
            names_file = st.selectbox("Избери файла с ИМЕНАТА (база данни):", file_list, index=1 if len(file_list)>1 else 0)
        with col3:
            join_col = st.text_input("Име на общата колона с Код (трябва да я има и в двата файла):", value="Код").strip()

        # Изпълнение на автоматичното свързване
        df_price = dataframes[price_file].copy()
        df_names = dataframes[names_file].copy()

        if join_col not in df_price.columns or join_col not in df_names.columns:
            st.error(f"❌ Колоната '{join_col}' не беше намерена в някой от файловете! Проверете главните/малките букви.")
        else:
            # Свързваме по код (LEFT JOIN) - взимаме всичко от ценоразписа и прикачаме името от базата
            # Суфиксите помагат ако има дублиращи се колони
            merged_df = pd.merge(df_price, df_names, on=join_col, how='left', suffixes=('_цени', '_имена'))
            
            st.divider()
            st.subheader("📝 Свързан ценоразпис (С възможност за промяна)")
            st.info("💡 Можете да кликнете два пъти върху ВСЯКА клетка (цена, име или код) в таблицата по-долу и да я промените ръчно!")
            
            # Настройваме колоните за по-добра подредба (слагаме Код и Име най-отпред)
            cols = list(merged_df.columns)
            if join_col in cols:
                cols.insert(0, cols.pop(cols.index(join_col)))
            merged_df = merged_df[cols]

            # МНОГО ВАЖНО: st.data_editor позволява редакция в реално време!
            edited_df = st.data_editor(merged_df, use_container_width=True, num_rows="dynamic")

            st.divider()
            st.subheader("💾 Запис на готовия ценоразпис")
            
            # Генериране на новия редактиран файл в паметта
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                edited_df.to_excel(writer, index=False)
            
            st.success("Всички промени са отразени! Можете да изтеглите финалния файл от бутона долу:")
            st.download_button(
                label="📥 Изтегли АКТУАЛИЗИРАНИЯ Excel файл",
                data=buffer.getvalue(),
                file_name="Обновен_Ценоразпис_Финал.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
    else:
        st.info("💡 Моля, качете **поне 2 файла** в страничното меню, за да сглобим ценоразписа.")
else:
    st.info("👋 Добре дошли! Качете вашите файлове от менюто вляво (бутона 📁 Добави Excel файлове).")
