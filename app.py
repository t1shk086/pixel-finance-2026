# -----------------------------------------------------
            # 🏢 СПРАВКА ПО ВСИЧКИ СКЛАДОВЕ (ПО АРТИКУЛЕН КОД / САП КОД)
            # -----------------------------------------------------
            if delivery_warehouse_col != "— Всички складове —":
                st.write("---")
                st.write("### 🏢 Подробна матрична справка по Всички Складове (по Артикулен / САП код)")

                # Определяме водещата колона за артикул/код от доставките
                if delivery_article_col != "— Няма —":
                    code_col_del = 'Delivery_Article_Clean'
                elif delivery_code_col != "— Няма —":
                    code_col_del = 'Delivery_Code_Clean'
                else:
                    code_col_del = 'Delivery_Name_Clean'

                # 1. Агрегиране на доставките по Артикулен Код + Склад
                del_by_wh = df_delivery.groupby([code_col_del, 'Delivery_Warehouse_Clean'])['Delivery_Qty_Clean'].sum().reset_index()
                del_by_wh.columns = ['Code', 'Warehouse', 'Доставено']

                # 2. Агрегиране на продажбите по Артикулен Код + Склад
                sales_by_wh = final_df.groupby(['Clean_Material', 'Warehouse_Clean'])['Quantity_m'].sum().reset_index()
                sales_by_wh.columns = ['Code', 'Warehouse', 'Продадено']

                # 3. Обединяване на доставките и продажбите по Артикулен Код и Склад
                merged_wh = pd.merge(del_by_wh, sales_by_wh, on=['Code', 'Warehouse'], how='outer').fillna(0)
                merged_wh['Остатък'] = merged_wh['Доставено'] - merged_wh['Продадено']

                # 4. Добавяне на наименование на кабела за всеки артикулен код
                name_lookup_sales = final_df.drop_duplicates('Clean_Material').set_index('Clean_Material')['Cable_Name_Clean'].to_dict()
                name_lookup_del = df_delivery.drop_duplicates(code_col_del).set_index(code_col_del)['Delivery_Name_Clean'].to_dict()
                
                merged_wh['Име на кабела'] = merged_wh['Code'].map(name_lookup_sales).fillna(merged_wh['Code'].map(name_lookup_del)).fillna(merged_wh['Code'])

                # 5. Изграждане на Pivot таблици за Доставено, Продадено и Остатък за всеки склад
                pivot_del = merged_wh.pivot_table(index=['Code', 'Име на кабела'], columns='Warehouse', values='Доставено', aggfunc='sum', fill_value=0)
                pivot_sales = merged_wh.pivot_table(index=['Code', 'Име на кабела'], columns='Warehouse', values='Продадено', aggfunc='sum', fill_value=0)
                pivot_bal = merged_wh.pivot_table(index=['Code', 'Име на кабела'], columns='Warehouse', values='Остатък', aggfunc='sum', fill_value=0)

                pivot_del.columns = [f"Доставено ({c})" for c in pivot_del.columns]
                pivot_sales.columns = [f"Продадено ({c})" for c in pivot_sales.columns]
                pivot_bal.columns = [f"Остатък ({c})" for c in pivot_bal.columns]

                # 6. Сглобяване на финалната матрична таблица
                multi_wh_df = pd.concat([pivot_del, pivot_sales, pivot_bal], axis=1).fillna(0).reset_index()
                
                st.dataframe(multi_wh_df, use_container_width=True)
