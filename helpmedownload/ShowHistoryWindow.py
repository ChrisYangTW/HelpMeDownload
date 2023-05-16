from PySide6.QtWidgets import QDialog, QVBoxLayout, QPushButton, QWidget, QTextBrowser


class HistoryWindow(QDialog):
    """
    QDialog window for show history
    """
    def __init__(self, history: list = None, special: bool = False,parent=None):
        super().__init__(parent)
        self.setWindowTitle('History')
        self.setGeometry(100, 100, 600, 400)

        v_layout = QVBoxLayout(self)
        self.display_text_browser = QTextBrowser(self)
        v_layout.addWidget(self.display_text_browser)

        # Move the QDialog window to the center of the main window
        if self.parentWidget():
            center_point = self.parentWidget().geometry().center()
            self.move(center_point.x() - self.width() / 2, center_point.y() - self.height() / 2)

        self.history = history
        if special:
            self.show_history_to_text_browser_for_failed_urls()
        else:
            self.show_history_to_text_browser()

    def show_history_to_text_browser_for_failed_urls(self):
        """
        Append the historical records to TextBrowser (Using HTML syntax to make URLs clickable for users)
        :return:
        """
        self.display_text_browser.setOpenExternalLinks(True)
        for history in self.history:
            if 'Version' in history:
                self.display_text_browser.insertHtml(f'<span>{history}</span><br>')
            else:
                self.display_text_browser.insertHtml(f'<a href="{history}">{history}</a><br>')

    def show_history_to_text_browser(self):
        """
        Append the historical records to TextBrowser
        :return:
        """
        for history in self.history:
            self.display_text_browser.append(history)

    # Overrides the reject() to allow users to cancel the dialog using the ESC key
    def reject(self):
        self.done(0)


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
            v_layout = QVBoxLayout()
            widget.setLayout(v_layout)
            self.setCentralWidget(widget)

            self.button = QPushButton('Open History Window', self)
            self.button.clicked.connect(self.show_editable_window)
            v_layout.addWidget(self.button)

        def show_editable_window(self):
            history_window = HistoryWindow(history=['abc', 'def'], parent=self)
            history_window.setWindowModality(Qt.ApplicationModal)
            history_window.show()


    app = QApplication([])
    main_window = MainWindow()
    main_window.show()
    app.exec()
