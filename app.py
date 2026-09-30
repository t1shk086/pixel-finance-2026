import sys, os
import pandas as pd
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QFileDialog, QTableWidget, 
                             QTableWidgetItem, QLineEdit, QLabel, QMessageBox, 
                             QHeaderView, QRadioButton, QButtonGroup, QGroupBox, QComboBox)
from PyQt6.QtCore import Qt

class ProductSearchApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Продуктов Мениджър")
        self.setGeometry(100, 100, 1100, 700)
        self.uploaded_files = {}
        self.initUI()
        
    def initUI(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QHBoxLayout(main_widget)
        left_panel = QVBoxLayout()
        
        file_group = QGroupBox("1. Зареждане на Excel таблици")
        file_layout = QVBoxLayout()
        self.btn_upload = QPushButton("📁 Добави Excel файлове")
        self.btn_upload.clicked.connect(self.upload_files)
        self.lbl_files = QLabel("Няма заредени файлове.")
        file_layout.addWidget(self.btn_upload)
        file_layout.addWidget(self.lbl_files)
        file_group.setLayout(file_layout)
        left_panel.addWidget(file_group)
        
        func_group = QGroupBox("3. Допълнителни функции (Свързване)")
        func_layout = QVBoxLayout()
        func_layout.addWidget(QLabel("Основна таблица (без имена):"))
        self.combo_main = QComboBox()
        func_layout.addWidget(self.combo_main)
        func_layout.addWidget(QLabel("Референтна таблица (с имена):"))
        self.combo_ref = QComboBox()
        func_layout.addWidget(self.combo_ref)
        func_layout.addWidget(QLabel("Име на колоната с Код:"))
        self.txt_join_col = QLineEdit()
        self.txt_join_col.setPlaceholderText("напр. Код")
        func_layout.addWidget(self.txt_join_col)
        self.btn_merge = QPushButton("🔗 Обедини и Експортирай")
        self.btn_merge.clicked.connect(self.merge_and_export)
        self.btn_merge.setStyleSheet("background-color: #2ecc71; color: white; font-weight: bold;")
        func_layout.addWidget(self.btn_merge)
        func_group.setLayout(func_layout)
        left_panel.addWidget(func_group)
        left_panel.addStretch()
        
        right_panel = QVBoxLayout()
        search_group = QGroupBox("2. Бързо търсене")
        search_layout = QVBoxLayout()
        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("Въведи код или близко име...")
        self.search_bar.textChanged.connect(self.search_data)
        search_layout.addWidget(self.search_bar)
        
        radio_layout = QHBoxLayout()
        self.radio_partial = QRadioButton("Частично съвпадение")
        self.radio_exact = QRadioButton("Точно съвпадение")
        self.radio_partial.setChecked(True)
        self.radio_partial.toggled.connect(self.search_data)
        self.radio_exact.toggled.connect(self.search_data)
        radio_layout.addWidget(self.radio_partial)
        radio_layout.addWidget(self.radio_exact)
        search_layout.addLayout(radio_layout)
        search_group.setLayout(search_layout)
        right_panel.addWidget(search_group)
        
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["Файл", "Ред", "Колона", "Стойност", "Други данни от реда"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        right_panel.addWidget(self.table)
        
        main_layout.addLayout(left_panel, 1)
        main_layout.addLayout(right_panel, 3)

    def upload_files(self):
        files, _ = QFileDialog.getOpenFileNames(self, "Изберете Excel файлове", "", "Excel Files (*.xlsx *.xls)")
        if files:
            for f_path in files:
                try:
                    f_name = os.path.basename(f_path)
                    df = pd.read_excel(f_path, dtype=str)
                    df.columns = [str(c).strip() for c in df.columns]
                    self.uploaded_files[f_name] = df
                except Exception as e:
                    QMessageBox.critical(self, "Грешка", f"Грешка при четене на {f_name}: {str(e)}")
            self.lbl_files.setText("Заредени:\n" + "\n".join(self.uploaded_files.keys()))
            self.combo_main.clear(); self.combo_ref.clear()
            self.combo_main.addItems(self.uploaded_files.keys())
            self.combo_ref.addItems(self.uploaded_files.keys())
            self.search_data()

    def search_data(self):
        query = self.search_bar.text().strip().lower()
        self.table.setRowCount(0)
        if not query or not self.uploaded_files: return
        exact = self.radio_exact.isChecked()
        results_list = []
        for file_name, df in self.uploaded_files.items():
            for idx, row in df.iterrows():
                for col in df.columns:
                    val = str(row[col]).strip()
                    if (val.lower() == query) if exact else (query in val.lower()):
                        all_row = ", ".join([f"{c}: {row[c]}" for c in df.columns if c != col])
                        results_list.append((file_name, idx + 2, col, val, all_row))
                        break
        self.table.setRowCount(len(results_list))
        for r_idx, data in enumerate(results_list):
            for c_idx, item in enumerate(data):
                cell = QTableWidgetItem(str(item))
                cell.setFlags(cell.flags() ^ Qt.ItemFlag.ItemIsEditable)
                self.table.setItem(r_idx, c_idx, cell)

    def merge_and_export(self):
        main_f = self.combo_main.currentText()
        ref_f = self.combo_ref.currentText()
        join_col = self.txt_join_col.text().strip()
        if not main_f or not ref_f or not join_col:
            QMessageBox.warning(self, "Внимание", "Попълнете всички полета в Секция 3!")
            return
        df_main = self.uploaded_files[main_f].copy()
        df_ref = self.uploaded_files[ref_f].copy()
        if join_col not in df_main.columns or join_col not in df_ref.columns:
            QMessageBox.critical(self, "Грешка", f"Колоната '{join_col}' не съществува в някой от файловете!")
            return
        try:
            merged_df = pd.merge(df_main, df_ref, on=join_col, how='left', suffixes=('_1', '_2'))
            save_path, _ = QFileDialog.getSaveFileName(self, "Запази", "Обединен_Файл.xlsx", "Excel Files (*.xlsx)")
            if save_path:
                merged_df.to_excel(save_path, index=False)
                QMessageBox.information(self, "Успех", f"Записан в:\n{save_path}")
        except Exception as e:
            QMessageBox.critical(self, "Грешка", str(e))

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ProductSearchApp()
    window.show()
    sys.exit(app.exec())
