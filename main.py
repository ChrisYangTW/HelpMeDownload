import sys

from PySide6.QtWidgets import QApplication, QStyleFactory

from helpmedownload.HelpMeDownloadMainWindow import MainWindow


if __name__ == "__main__":
    app = QApplication([])
    window = MainWindow()
    if sys.platform == 'darwin' and 'Fusion' in QStyleFactory.keys():
        app.setStyle(QStyleFactory.create('Fusion'))
    window.show()
    app.aboutToQuit.connect(window.clear_threadpool)
    app.aboutToQuit.connect(app.quit)
    sys.exit(app.exec())
