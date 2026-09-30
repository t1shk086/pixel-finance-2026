import sys
import os
import pandas as pd
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QFileDialog, QTableWidget, 
                             QTableWidgetItem, QLineEdit, QLabel, QMessageBox, 
                             QHeaderView, QRadioButton, QButtonGroup, QGroupBox, QComboBox)
from PyQt6.QtCore import Qt

class ProductSearchApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Интелигентна Продуктова Търсачка & Мениджър")
        self.setGeometry(100, 100, 1100, 700)
        
        self.uploaded_files = {} # Запазва данните: { "име_файл": dataframe }
        self.initUI()
        
    def initUI(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QHBoxLayout(main_widget)
        
        # --- ЛЯВ ПАНЕЛ: Управление на файлове и функции ---
        left_panel = QVBoxLayout()
        
        # Група за файлове
        file_group = QGroupBox("1. Зареждане на Excel таблици")
        file_layout = QVBoxLayout()
        self.btn_upload = QPushButton("📁 Добави Excel файлове")
        self.btn_upload.clicked.connect(self.upload_files)
        self.lbl_files = QLabel("Няма заредени файлове.")
        self.lbl_files.setWordWrap(True)
        file_layout.addWidget(self.btn_upload)
        file_layout.addWidget(self.lbl_files)
        file_group.setLayout(file_layout)
        left_panel.addWidget(file_group)
        
        # Група за ДОПЪЛНИТЕЛНИ ФУНКЦИИ (Трети файлове / Трансформации)
        func_group = QGroupBox("3. Допълнителни функции & Операции")
        func_layout = QVBoxLayout()
        
        func_layout.addWidget(QLabel("Избери основна таблица (без имена):"))
        self.combo_main = QComboBox()
        func_layout.addWidget(self.combo_main)
        
        func_layout.addWidget(QLabel("Избери референтна таблица (с имена):"))
        self.combo_ref = QComboBox()
        func_layout.addWidget(self.combo_ref)
        
        func_layout.addWidget(QLabel("Име на колоната за връзка (Код):"))
        self.txt_join_col = QLineEdit()
        self.txt_join_col.setPlaceholder Balancer = "напр. Код"
        func_layout.addWidget(self.txt_join_col)
        
        self.btn_merge = QPushButton("🔗 Автоматично сглобяване (JOIN) и Експорт")
        self.btn_merge.clicked.connect(self.merge_and_export)
        self.btn_merge.setStyleSheet("background-color: #2ecc71; color: white; font-weight: bold;")
        func_layout.addWidget(self.btn_merge)
        
        func_group.setLayout(func_layout)
        left_panel.addWidget(func_group)
        left_panel.addStretch()
        
        # --- ДЕСЕН ПАНЕЛ: Търсене и Резултати ---
        right_panel = QVBoxLayout()
        
        search_group = QGroupBox("2. Бързо търсене на код / близко име")
        search_layout = QVBoxLayout()
        
        search_input_layout = QHBoxLayout()
        search_input_layout.addWidget(QLabel("Търсене за:"))
        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("Въведи код (напр. 123) или име на продукт...")
        self.search_bar.textChanged.connect(self.search_data)
        search_input_layout.addWidget(self.search_bar)
        search_layout.addLayout(search_input_layout)
        
        # Опции за съвпадение
        radio_layout = QHBoxLayout()
        self.radio_partial = QRadioButton("Частично съвпадение (Близки имена)")
        self.radio_exact = QRadioButton("Точно съвпадение (по код)")
        self.radio_partial.setChecked(True)
        self.radio_partial.toggled.connect(self.search_data)
        self.radio_exact.toggled.connect(self.search_data)
        
        self.radio_group = QButtonGroup()
        self.radio_group.addButton(self.radio_partial)
        self.radio_group.addButton(self.radio_exact)
        
        radio_layout.addWidget(self.radio_partial)
        radio_layout.addWidget(self.radio_exact)
        search_layout.addLayout(radio_layout)
        search_group.setLayout(search_layout)
        right_panel.addWidget(search_group)
        
        # Таблица с резултати
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["Източник (Файл)", "Ред", "Намерено в колона", "Стойност", "Останали данни от реда"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        right_panel.addWidget(self.table)
        
        # Сглобяване на основния прозорец
        main_layout.addLayout(left_panel, 1)
        main_layout.addLayout(right_panel, 3)

    def upload_files(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "Изберете Excel файлове", "", "Excel Files (*.xlsx *.xls)"
        )
        if files:
            for f_path in files:
                try:
                    f_name = os.path.basename(f_path)
                    # Четем всичко като текст, за да запазим водещи нули в кодовете
                    df = pd.read_excel(f_path, dtype=str)
                    df.columns = [str(c).strip() for c in df.columns]
                    self.uploaded_files[f_name] = df
                except Exception as e:
                    QMessageBox.critical(self, "Грешка", f"Грешка при четене на {os.path.basename(f_path)}: {str(e)}")
            
            # Обновяване на списъка и падащите менюта
            self.lbl_files.setText(" Заредени файлове:\n" + "\n".join(self.uploaded_files.keys()))
            self.combo_main.clear()
            self.combo_ref.clear()
            self.combo_main.addItems(self.uploaded_files.keys())
            self.combo_ref.addItems(self.uploaded_files.keys())
            
            QMessageBox.information(self, "Успех", f"Успешно заредени {len(files)} файла!")
            self.search_data()

    def search_data(self):
        query = self.search_bar.text().strip().lower()
        self.table.setRowCount(0)
        
        if not query or not self.uploaded_files:
            return
            
        exact = self.radio_exact.isChecked()
        results_list = []
        
        for file_name, df in self.uploaded_files.items():
            for idx, row in df.iterrows():
                for col in df.columns:
                    val = str(row[col]).strip()
                    match = (val.lower() == query) if exact else (query in val.lower())
                    
                    if match:
                        all_row_data = ", ".join([f"{c}: {row[c]}" for c in df.columns if c != col])
                        results_list.append((file_name, idx + 2, col, val, all_row_data))
                        break
                        
        self.table.setRowCount(len(results_list))
        for row_idx, data in enumerate(results_list):
            for col_idx, item in enumerate(data):
                cell = QTableWidgetItem(str(item))
                cell.setFlags(cell.flags() ^ Qt.ItemFlag.ItemIsEditable)
                self.table.setItem(row_idx, col_idx, cell)

    def merge_and_export(self):
        main_f = self.combo_main.currentText()
        ref_f = self.combo_ref.currentText()
        join_col = self.txt_join_col.text().strip()
        
        if not main_f or not ref_f or not join_col:
            QMessageBox.warning(self, "Внимание", "Моля, изберете файлове и въведете име на общата колона с кодовете!")
            return
            
        df_main = self.uploaded_files[main_f].copy()
        df_ref = self.uploaded_files[ref_f].copy()
        
        if join_col not in df_main.columns or join_col not in df_ref.columns:
            QMessageBox.critical(self, "Грешка", f"Колоната '{join_col}' не беше намерена в някой от файловете!\nПроверете главните букви.")
            return
            
        try:
            # Автоматично VLOOKUP обединяване (LEFT JOIN)
            merged_df = pd.merge(df_main, df_ref, on=join_col, how='left', suffixes=('_основен', '_референция'))
            
            save_path, _ = QFileDialog.getSaveFileName(self, "Запази обединения файл", "Обединен_Продукти.xlsx", "Excel Files (*.xlsx)")
            if save_path:
                merged_df.to_excel(save_path, index=False)
                QMessageBox.information(self, "Успех!", f"Файлът е сглобен успешно и записан в:\n{save_path}")
        except Exception as e:
            QMessageBox.critical(self, "Грешка при сглобяване", f"Възникна техническа грешка: {str(e)}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ProductSearchApp()
    window.show()
    sys.exit(app.exec())
