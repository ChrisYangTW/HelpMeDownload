import re

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QPushButton, QWidget, QTextBrowser,
                               QHBoxLayout, QTextEdit, QSizePolicy, QMessageBox, QFileDialog)


class LoadingBatchUrlsWindow(QDialog):
    """
    QDialog window for loading batch Urls
    """
    loading_batch_urls_signal = Signal(list)

    def __init__(self, batch_url_list: list = None, parent=None):
        super().__init__(parent)
        self.batch_url_list = batch_url_list
        self.initUI()

    def initUI(self):
        self.setWindowTitle('Load Model Urls')
        self.setGeometry(100, 100, 600, 400)

        self.v_layout = QVBoxLayout(self)
        self.urls_editor = QTextEdit(self)
        for url in self.batch_url_list:
            self.urls_editor.append(url)
        self.v_layout.addWidget(self.urls_editor)

        self.check_message = QTextBrowser()
        sizePolicy1 = QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Ignored)
        sizePolicy1.setHorizontalStretch(0)
        sizePolicy1.setVerticalStretch(0)
        sizePolicy1.setHeightForWidth(self.check_message.sizePolicy().hasHeightForWidth())
        self.check_message.setSizePolicy(sizePolicy1)
        self.v_layout.addWidget(self.check_message)

        h_button_layout = QHBoxLayout()
        self.cancel_button = QPushButton('Cancel', self)
        self.cancel_button.setAutoDefault(False)
        self.cancel_button.setStyleSheet("background-color: rgb(195, 50, 50)")
        self.load_button = QPushButton('Load', self)
        self.load_button.setStyleSheet("background-color: rgb(50, 195, 50)")
        self.load_button.setAutoDefault(False)
        self.confirm_button = QPushButton('Confirm', self)
        self.confirm_button.setStyleSheet("background-color: rgb(50, 50, 195)")
        self.confirm_button.setAutoDefault(False)

        self.cancel_button.clicked.connect(self.reject)
        self.load_button.clicked.connect(self.click_load_button)
        self.confirm_button.clicked.connect(self.click_confirm_button)

        h_button_layout.addWidget(self.cancel_button)
        h_button_layout.addWidget(self.load_button)
        h_button_layout.addWidget(self.confirm_button)

        self.v_layout.addLayout(h_button_layout)
        self.v_layout.setStretch(0, 10)
        self.v_layout.setStretch(1, 1)
        self.v_layout.setStretch(2, 1)

        # Move the QDialog window to the center of the main window
        if self.parentWidget():
            center_point = self.parentWidget().geometry().center()
            self.move(center_point.x() - self.width() / 2, center_point.y() - self.height() / 2)

    # Overrides the reject() to allow users to cancel the dialog using the ESC key
    def reject(self, call_from_confirm_button: bool = False):
        if call_from_confirm_button:
            self.done(0)
            return

        if text := self.urls_editor.toPlainText():
            result = QMessageBox.question(self, 'Confirmation', 'Are you sure to cancel ?',
                                          QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if result == QMessageBox.Yes:
                self.done(0)
        else:
            self.done(0)

    def click_load_button(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Open TXT", '', "Text Files (*.txt)")
        if not _:
            return

        with open(file_path, 'r', encoding='utf-8') as f:
            urls_list = [line.strip() for line in f]

        for url in urls_list:
            self.urls_editor.append(url)

    def click_confirm_button(self):
        url_list = self.urls_editor.toPlainText().strip().split()

        # pattern = re.compile(r'https://civitai[.]com/models/\d{4,5}(?:/.*)?|(?:[?]modelVersionId=\d{4,5})')
        pattern = re.compile(r'https://civitai\.com/models/\d+(\/[\w-]+)?(\?modelVersionId=\d+)?$')
        match_error_url_list = [url for url in url_list if not pattern.match(url)]

        if not match_error_url_list:
            self.loading_batch_urls_signal.emit(url_list)
            self.reject(call_from_confirm_button=True)
            return

        self.check_message.clear()
        for error_url in match_error_url_list:
            self.check_message.append(f'{error_url}')


if __name__ == '__main__':
    from PySide6.QtWidgets import QMainWindow, QApplication
    from PySide6.QtGui import Qt

    class MainWindow(QMainWindow):
        def __init__(self):
            super().__init__()
            self.initUI()

        def initUI(self):
            self.setWindowTitle('Button Window')
            self.resize(800, 600)
            widget = QWidget()
            self.v_layout = QVBoxLayout()
            widget.setLayout(self.v_layout)
            self.setCentralWidget(widget)

            self.button = QPushButton('Open Window', self)
            self.button.clicked.connect(self.show_window)
            self.v_layout.addWidget(self.button)

        def show_window(self):
            history_window = LoadingBatchUrlsWindow(parent=self)
            history_window.setWindowModality(Qt.ApplicationModal)
            history_window.show()


    app = QApplication([])
    main_window = MainWindow()
    main_window.show()
    app.exec()
