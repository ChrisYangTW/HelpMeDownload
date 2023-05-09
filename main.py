import sys
import time

from PySide6.QtCore import QObject, Signal, QThread, QCoreApplication
from PySide6.QtWidgets import QApplication, QMainWindow, QStyleFactory

from helpmedownload.untitled_main import Ui_MainWindow
from helpmedownload.image_url_paser import CivitaiImageDownloader, get_model_and_version_and_status


class DownloadWorker(QObject):
    progress = Signal(str)
    completed = Signal(bool)

    def __init__(self, model_and_version_id: tuple):
        super().__init__()
        self.downloader = CivitaiImageDownloader(model_and_version_id)

    def start(self):
        self.progress.emit('start to download')
        self.downloader.start()
        self.completed.emit(True)


class MainWindow(QMainWindow):
    start_to = Signal()

    def __init__(self):
        super(MainWindow, self).__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        self.model_and_version_id = ()

        self.download_worker = None
        self.download_worker_thread = QThread()

        self.ui.ready_to_go_push_button.setEnabled(False)
        self.ui.parser_push_button.clicked.connect(self.parser)
        self.ui.ready_to_go_push_button.clicked.connect(self.start_download)


    def parser(self):
        url = self.ui.lineEdit.text()
        if model_and_version_and_status := get_model_and_version_and_status(url=url, for_test=True):
            if model_and_version_and_status[2]:
                self.model_and_version_id = model_and_version_and_status[:2]
                self.ui.text_browser.append('parser ok')
                self.ui.ready_to_go_push_button.setEnabled(True)
                print(self.model_and_version_id)
            else:
                self.ui.ready_to_go_push_button.setEnabled(False)
                self.ui.statusbar.setStyleSheet('color: red')
                self.ui.statusbar.showMessage('Connect to url fail.', 3000)
                return
        else:
            self.ui.ready_to_go_push_button.setEnabled(False)
            self.ui.statusbar.setStyleSheet('color: red')
            self.ui.statusbar.showMessage('Url parser fail.', 3000)

    def start_download(self):
        self.ui.parser_push_button.setEnabled(False)
        self.ui.ready_to_go_push_button.setEnabled(False)

        self.download_worker = DownloadWorker(self.model_and_version_id)
        self.start_to.connect(self.download_worker.start)
        self.download_worker.progress.connect(self.handle_progress)
        self.download_worker.completed.connect(self.handle_completed)
        self.download_worker.moveToThread(self.download_worker_thread)
        self.download_worker_thread.start()
        self.start_to.emit()

        self.ui.parser_push_button.setEnabled(True)

    def handle_progress(self, string):
        print(string)

    def handle_completed(self, done):
        if done and self.download_worker_thread.isRunning():
            self.download_worker_thread.quit()
            self.download_worker_thread.wait()
            print('close download_worker_thread')


if __name__ == "__main__":
    app = QApplication([])
    window = MainWindow()
    if sys.platform == 'darwin' and 'Fusion' in QStyleFactory.keys():
        app.setStyle(QStyleFactory.create('Fusion'))
    window.show()
    sys.exit(app.exec())
