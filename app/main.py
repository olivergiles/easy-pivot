import sys
import pandas as pd
from datetime import datetime
from pathlib import Path
from PySide6 import QtGui, QtWidgets, QtCore
from PySide6.QtCore import Qt, Signal, QThreadPool, QAbstractTableModel
from PySide6.QtGui import QIcon, QAction
from PySide6.QtWidgets import QProgressBar, QStackedLayout, QStyledItemDelegate, QMainWindow, QTableView, QVBoxLayout,\
    QWidget, QMenu, QComboBox, QDialog, QMessageBox, QPushButton
from app.utils.column_filters import filter_number, filter_name
import numpy as np
import uuid


class TableModel(QAbstractTableModel):
    def __init__(self, data):
        super().__init__()
        self._data = data

    def data(self, index, role):
        if role == Qt.DisplayRole:
            value = self._data.iloc[index.row()][index.column()]
            if isinstance(value, float):
                return str("%.10f" % value)
            if isinstance(value, int):
                return str("%.10f" % value)
            if isinstance(value, datetime):
                return value.strftime("%Y-%m-%d")
            if isinstance(value, str):
                return '"%s"' % value
            return str(value)

    def rowCount(self, index):
        return self._data.shape[0]

    def columnCount(self, index):
        return self._data.shape[1]

    def headerData(self, section, orientation, role):
        if role == Qt.DisplayRole:
            if orientation == Qt.Horizontal:
                return str(self._data.columns[section])
            if orientation == Qt.Vertical:
                return str(self._data.index[section])


class FloatDelegate(QStyledItemDelegate):
    def __init__(self, decimals, parent=None):
        super(FloatDelegate, self).__init__(parent=parent)
        self.nDecimals = decimals

    def displayText(self, value, locale):
        try:
            number = float(value)
        except ValueError:
            return super(FloatDelegate, self).displayText(value, locale)
        else:
            if number <= 0.0001 :
                scientific_notation = "{:.9e}".format(number)
                return scientific_notation
            else:
                number_str = "{0:.12f}".format(number)
                return number_str


class NonCloseMenu(QMenu):
    def actionEvent(self, event):
        super().actionEvent(event)
        self.show()


class MainWindow(QMainWindow, NonCloseMenu):
    def __init__(self):
        super().__init__()
        # Getting the data
        self.table = QTableView()
        path, header_there = self.open_file()
        path = path[0]
        data_read = pd.read_csv(path, low_memory=False)
        num_col = len(data_read.columns)
        if header_there is None:
            header_names = self.ask_for_headers(num_col)
            data_read = pd.read_csv(path, names =header_names, low_memory=False)
            print(header_names)
        self.original_data = data_read
        self.header_names = data_read.columns.values.tolist()
        self.pivot_options_dict = {'data': self.original_data}
        self.current_data = data_read
        self.model = TableModel(data_read)

        # Setting up the window
        self.layout = QStackedLayout()
        layout1 = QWidget()
        layout1_int = QVBoxLayout(layout1)
        self.layout.addWidget(self.table)
        self.layout.addWidget(layout1)
        self.layout.setCurrentIndex(0)
        self.table.setModel(self.model)
        self.table.setItemDelegate(FloatDelegate(8))
        for i in range(num_col):
            self.table.setColumnWidth(i, 150)
        self.setCentralWidget(self.table)
        self.resize(150*num_col, 700)
        self.center()
        self.setIcon()
        self.setWindowTitle("Easy Pivot")

        # Setting up menu
        menu = self.menuBar()
        file_menu = menu.addMenu("&File")

        table_menu = menu.addMenu("&Data")
        reset_table_act = QAction("Reset table", self)
        reset_table_act.setStatusTip("Reset table back to original")
        reset_table_act.triggered.connect(self.reset_table)
        table_menu.addAction(reset_table_act)

        change_table_act = QAction("Change table", self)
        change_table_act.setStatusTip("Change the table")
        change_table_act.triggered.connect(self.change_table)
        table_menu.addAction(change_table_act)

        self.pivot_menu = menu.addMenu("&Pivot")

        pivot_table_act = QAction("Pivot table", self)
        pivot_table_act.setStatusTip("Pivot the table")
        pivot_table_act.triggered.connect(self.pivot_table)
        self.pivot_menu.addAction(pivot_table_act)

        self.checked_values = []
        self.checked_index = []
        self.checked_columns = []
        self.values_menu = self.pivot_menu.addMenu("&Values")
        self.d_val_select = {}

        for name in self.header_names:
            self.d_val_select["Value {0}".format(name)] = QAction(name, self)
            self.d_val_select["Value {0}".format(name)].setCheckable(True)
            self.d_val_select["Value {0}".format(name)].setWhatsThis(name)
            self.d_val_select["Value {0}".format(name)].triggered.connect(self.selection_value_pivot_action)
            self.values_menu.addAction(self.d_val_select["Value {0}".format(name)])

        self.index_menu = self.pivot_menu.addMenu("&Index")
        self.d_index_select = {}
        for name in self.header_names:
            self.d_index_select["Index {0}".format(name)] = QAction(name, self)
            self.d_index_select["Index {0}".format(name)].setCheckable(True)
            self.d_index_select["Index {0}".format(name)].setWhatsThis(name)
            self.d_index_select["Index {0}".format(name)].triggered.connect(self.selection_index_pivot_action)
            self.index_menu.addAction(self.d_index_select["Index {0}".format(name)])

        self.column_menu = self.pivot_menu.addMenu("&Columns")
        self.d_column_select = {}
        for name in self.header_names:
            self.d_column_select["Column {0}".format(name)] = QAction(name, self)
            self.d_column_select["Column {0}".format(name)].setCheckable(True)
            self.d_column_select["Column {0}".format(name)].setWhatsThis(name)
            self.d_column_select["Column {0}".format(name)].triggered.connect(self.selection_column_pivot_action)
            self.column_menu.addAction(self.d_column_select["Column {0}".format(name)])

        self.function_menu = self.pivot_menu.addMenu("&Aggregate Functions")
        self.function_names = ["mean", "sum", "size", "count", "std", "var", "sem", "describe",
                               "first", "last", "min", "max"]
        self.d_function_select = {}
        for name in self.function_names:
            self.d_function_select["Function {0}".format(name)] = QAction(name, self)
            self.d_function_select["Function {0}".format(name)].setCheckable(True)
            self.d_function_select["Function {0}".format(name)].setWhatsThis(name)
            self.d_function_select["Function {0}".format(name)].triggered.connect(self.selection_function_pivot_action)
            self.function_menu.addAction(self.d_function_select["Function {0}".format(name)])

        self.pivot_table_margins_act = QAction("Margins", self)
        self.pivot_table_margins_act.setStatusTip("Should subtotals be added?")
        self.pivot_table_margins_act.setCheckable(True)
        self.pivot_table_margins_act.setChecked(True)
        self.pivot_table_margins_act.triggered.connect(self.pivot_table_margins_action)
        self.pivot_menu.addAction(self.pivot_table_margins_act)

        self.add_filter = QAction("Add new filter", self)
        self.add_filter.setStatusTip("Pivot the table")
        self.add_filter.triggered.connect(self.add_filter_func)
        self.pivot_menu.addAction(self.add_filter)

        self.filter_menu = self.pivot_menu.addMenu("&Remove Filter")
        self.filters = []

    def setIcon(self):
        app_icon = QIcon("assets/main_logo.png")
        self.setWindowIcon(app_icon)

    def center(self):
        screensize = QtGui.QScreen.availableGeometry(QtWidgets.QApplication.primaryScreen())
        center_x = (screensize.width() - self.width())/2
        center_y = (screensize.height() - self.height())/2
        self.move(int(center_x), int(center_y))

    def open_file(self):
        home_dir = str(Path.home())
        dialog = QtWidgets.QFileDialog(self)
        dialog.setDirectory(home_dir)
        dialog.setFileMode(QtWidgets.QFileDialog.ExistingFile)
        dialog.setNameFilter("Data (*.csv)")
        dialog.setViewMode(QtWidgets.QFileDialog.Detail)
        if dialog.exec():
            filePath = dialog.selectedFiles()
        are_headers = AreHeadersWindow(self)
        if are_headers.exec():
            headers = "Done"
        else:
            headers = None
        return filePath, headers

    def ask_for_headers(self, columns):
        ask = HeadersNameWindow(self)
        ask.header_nums_enter(columns)
        if ask.exec():
            header_names_final = ask.retrieve_headers()
            print("Asked")
            return header_names_final

    def reset_table(self):
        self.model = TableModel(self.original_data)
        self.table.setModel(self.model)

    def change_table(self):
        new_df = pd.DataFrame({"A": ["foo", "foo", "foo", "foo", "foo",

                 "bar", "bar", "bar", "bar"],

             "B": ["one", "one", "one", "two", "two",

                 "one", "one", "two", "two"],

             "C": ["small", "large", "large", "small",

                 "small", "large", "small", "small",

                 "large"],

             "D": [1, 2, 2, 3, 3, 4, 5, 6, 7],

             "E": [2, 4, 5, 5, 6, 6, 8, 9, 9]})
        self.current_data = new_df
        model = TableModel(new_df)
        self.table.setModel(model)

    def pivot_table(self):
        checked_function = []
        for name in self.function_names:
            if self.d_function_select["Function {0}".format(name)].isChecked():
                checked_function.append(name)
        if len(checked_function) < 0:
            checked_function = 0
        margins_option = True
        if not self.pivot_table_margins_act.isChecked():
            margins_option = False
        if len(self.checked_values) > 0:
            vals = self.checked_values
        else:
            vals = None
        if len(self.checked_columns) > 0:
            cols = self.checked_columns
        else:
            cols = 0
        if len(self.checked_index) > 0:
            indx = self.checked_index
        else:
            indx = None
        pivoted_table = pd.pivot_table(self.current_data, values=vals, index=indx,
                                       columns=cols, aggfunc=checked_function, margins=margins_option)
        self.model = TableModel(pivoted_table)
        self.table.setModel(self.model)

    def add_filter_func(self):
        new_filter = FilterWindow(self,  data = [self.header_names, self.current_data])

    def pivot_table_margins_action(self):
        self.pivot_menu.show()

    def selection_value_pivot_action(self):
        checked_values = []
        for name in self.header_names:
            if self.d_val_select["Value {0}".format(name)].isChecked():
                checked_values.append(name)
        self.checked_values = checked_values
        self.pivot_menu.show()
        self.values_menu.show()

    def selection_index_pivot_action(self):
        checked_index = []
        for name in self.header_names:
            if self.d_index_select["Index {0}".format(name)].isChecked():
                checked_index.append(name)
        self.checked_index = checked_index
        self.pivot_menu.show()
        self.index_menu.show()

    def selection_column_pivot_action(self):
        checked_columns = []
        for name in self.header_names:
            if self.d_column_select["Column {0}".format(name)].isChecked():
                checked_columns.append(name)
        self.checked_columns = checked_columns
        self.pivot_menu.show()
        self.column_menu.show()

    def selection_function_pivot_action(self):
        self.pivot_menu.show()
        self.function_menu.show()

    def fetch_current_selections(self):
        return self.checked_values, self.checked_columns, self.checked_index


class FilterWindow(QMainWindow):
    def __init__(self, parent, data):
        super().__init__(parent)
        self.setWindowTitle("New Filter")
        self.center()
        self.data = data
        print(self.data[1])
        self.filter = {}

        filter_layout = QWidget()
        self.filter_layout = QStackedLayout(filter_layout)
        filter_layout1 = QWidget()
        self.filter_layout1_int = QVBoxLayout(filter_layout1)
        self.column_selector = QComboBox()
        self.column_selector.addItems(self.data[0])
        self.next1 = QPushButton("Next")
        self.next1.setCheckable(False)
        self.next1.clicked.connect(self.next1f)
        self.filter_layout1_int.addWidget(self.column_selector)
        self.filter_layout1_int.addWidget(self.next1)

        filter_layout2 = QWidget()
        self.filter_layout2_int = QVBoxLayout(filter_layout2)
        self.next2 = QPushButton("Next")
        self.next2.setCheckable(False)
        self.next2.clicked.connect(self.next2f)
        self.filter_layout2_int.addWidget(self.next2)

        filter_layout3 = QWidget()
        self.filter_layout3_int = QVBoxLayout(filter_layout3)
        self.next3 = QPushButton("Next")
        self.next3.setCheckable(False)
        self.next3.clicked.connect(self.next3f)
        self.filter_layout3_int.addWidget(self.next3)

        self.filter_layout.addWidget(filter_layout1)
        self.filter_layout.addWidget(filter_layout2)
        self.filter_layout.addWidget(filter_layout3)
        checked_values, checked_columns, checked_index = window.fetch_current_selections()
        print(checked_values, checked_columns, checked_index)
        if (checked_values + checked_columns + checked_index) is []:
            button = QMessageBox.critical(self, "Error!",
                                          "In order to add a filter you need to select "
                                          "either a value, index or column!")
            if button == QMessageBox.Ok:
                self.accept()
        self.setCentralWidget(filter_layout)
        self.show()

    def center(self):
        screensize = QtGui.QScreen.availableGeometry(QtWidgets.QApplication.primaryScreen())
        center_x = (screensize.width() - self.width())/2
        center_y = (screensize.height() - self.height())/2
        self.move(int(center_x), int(center_y))

    def next1f(self):
        self.filter["column"] = self.column_selector.currentData()
        self.filter["dtype"] = self.data[1]
        self.filter_layout.setCurrentIndex(1)
        return

    def next2f(self):
        self.filter_layout.setCurrentIndex(2)
        return

    def next3f(self):
        self.close()

    def return_filter(self):
        return self.filter


class AreHeadersWindow(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Column headers")
        buttons = QtWidgets.QDialogButtonBox.No | QtWidgets.QDialogButtonBox.Yes
        self.buttonBox = QtWidgets.QDialogButtonBox(buttons)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)
        self.layout = QtWidgets.QVBoxLayout()
        message = QtWidgets.QLabel("Does your data have headers?")
        self.layout.addWidget(message)
        self.layout.addWidget(self.buttonBox)
        self.center()
        self.setLayout(self.layout)

    def center(self):
        screensize = QtGui.QScreen.availableGeometry(QtWidgets.QApplication.primaryScreen())
        center_x = (screensize.width() - self.width())/2
        center_y = (screensize.height() - self.height())/2
        self.move(int(center_x), int(center_y))


class HeadersNameWindow(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.columns = 0
        self.d = {}
        self.header_names_list = []
        self.setWindowTitle("Column headers")
        self.layout = QtWidgets.QVBoxLayout()
        message = QtWidgets.QLabel("Please enter your desired headers")
        self.layout.addWidget(message)
        self.center()

    def header_nums_enter(self, columns):   
        for i in range(columns):
            self.d["widget{0}".format(i)] = QtWidgets.QLineEdit()
            self.d["widget{0}".format(i)].setMaxLength(15)
            self.d["widget{0}".format(i)].setPlaceholderText("Enter your header")
            self.d["widget{0}".format(i)].returnPressed.connect(self.return_pressed)
            if i == columns-1:
                self.d["widget{0}".format(i)].returnPressed.connect(self.set_headers)
            self.layout.addWidget(self.d["widget{0}".format(i)])
        button = QtWidgets.QPushButton("Set headers")
        button.setCheckable(True)
        button.setAutoDefault(False)
        button.clicked.connect(self.set_headers)
        self.columns = columns
        self.layout.addWidget(button)
        self.setLayout(self.layout)

    def return_pressed(self):
        print("Return pressed!")
        self.focusNextPrevChild(True)

    def set_headers(self):
        self.header_names_list = []
        for i in range(self.columns):
            name = self.d["widget{0}".format(i)].text()
            self.header_names_list.append(name)
        print("Headers set!")
        self.accept()

    def retrieve_headers(self):
        return self.header_names_list

    def center(self):
        screensize = QtGui.QScreen.availableGeometry(QtWidgets.QApplication.primaryScreen())
        center_x = (screensize.width() - self.width())/2
        center_y = (screensize.height() - self.height())/2
        center_y += -200
        self.move(int(center_x), int(center_y))


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    window.show()
    app.exec()
