import sys
from datetime import datetime
from pathlib import Path

import httpx
from PySide6.QtCore import QThreadPool, Qt
from PySide6.QtGui import QTextCharFormat
from PySide6.QtWidgets import QApplication, QMainWindow, QStyleFactory, QFileDialog, QProgressBar

from helpmedownload.ParserAndDownload import CivitalUrlParserRunner, CivitaImageDownloadRunner
from helpmedownload.ShowHistoryWindow import HistoryWindow
from helpmedownload.untitled_main import Ui_MainWindow


class MainWindow(QMainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.ui.ready_to_go_push_button.setEnabled(False)

        self.pool = QThreadPool.globalInstance()
        self.httpx_client = httpx.Client()

        self.model_name = ''
        self.model_and_version_id = ()
        self.model_version_info_dict = {}
        self.save_dir = ''
        self.progress_bar_alive_list = []
        self.progress_bar_info = {}
        self.download_history_list = []
        self.download_failed_urls_dict = {}

        self.ui.actionShowHistory.triggered.connect(lambda: self.trigger_show_action(self.download_history_list))
        self.ui.actionShowFailUrl.triggered.connect(lambda: self.trigger_show_action(
            self.convert_failed_urls_dict_to_list(self.download_failed_urls_dict)
        ))
        self.ui.choose_folder_button.clicked.connect(self.click_choose_folder_button)
        self.ui.parser_push_button.clicked.connect(self.click_parse_button)
        self.ui.ready_to_go_push_button.clicked.connect(self.click_ready_to_go_button)

        # When url_line_edit is modified, request a re-parsing
        self.ui.url_line_edit.textChanged.connect(lambda: self.ui.ready_to_go_push_button.setEnabled(False))

    def trigger_show_action(self, history: list) -> None:
        """
        Pop up a QDialog window for show history
        :return: 
        """""
        history_window = HistoryWindow(history=history, parent=self)
        # Only after this QDialog is closed, the main window can be used again
        history_window.setWindowModality(Qt.ApplicationModal)
        history_window.show()

    def click_choose_folder_button(self) -> None:
        """
        Set the path for saving the image
        :return:
        """
        options = QFileDialog.Options()
        options |= QFileDialog.ShowDirsOnly
        folder = QFileDialog.getExistingDirectory(self, "Select Folder", options=options)
        self.ui.folder_line_edit.setText(folder)
        self.save_dir = Path(folder)

    def click_parse_button(self) -> None:
        """
        Parse the URL using QThreadPool
        :return:
        """
        url = self.ui.url_line_edit.text()
        civital_url_parser = CivitalUrlParserRunner(url)
        civital_url_parser.signals.UrlParser_started_signal.connect(self.handle_parser_started_signal)
        civital_url_parser.signals.UrlParser_status_signal.connect(self.handle_parser_status_signal)
        civital_url_parser.signals.UrlParser_completed_signal.connect(self.handle_parser_completed_signal)

        self.pool.start(civital_url_parser)

    def handle_parser_started_signal(self, started_message: str):
        self.ui.parser_text_browser.append(started_message)

    def handle_parser_status_signal(self, model_and_version_and_status: tuple):
        """
        enable 'ready_to_go' button
        """
        status = model_and_version_and_status[-1]
        self.model_and_version_id = model_and_version_and_status[:-1]

        match status:
            case None:
                self.text_browser_insert_html(
                    f'<span style="color: green;">Test mode: {self.model_and_version_id= }</span>'
                )
            case False:
                if self.model_and_version_id == (None, None):
                    self.text_browser_insert_html('<span style="color: pink;">Url parser fail</span>')
                else:
                    self.ui.parser_text_browser.append(str(self.model_and_version_id))
                    self.ui.statusbar.showMessage('Connect to url fail.', 3000)
            case _:
                self.ui.parser_text_browser.append(str(self.model_and_version_id))

    def handle_parser_completed_signal(self, info: tuple):
        self.model_name, self.model_version_info_dict = info
        self.ui.parser_text_browser.append('Parser ok, click "Ready to go" to download')
        if self.save_dir:
            self.ui.ready_to_go_push_button.setEnabled(True)
        else:
            self.ui.result_text_browser.append('need to set folder before parser')

    def click_ready_to_go_button(self):
        """
        need: self.model_version_info_dict is correct
        Start to download all images
        :return:
        """
        self.ui.url_line_edit.setEnabled(False)
        self.ui.parser_push_button.setEnabled(False)
        self.ui.choose_folder_button.setEnabled(False)
        self.ui.ready_to_go_push_button.setEnabled(False)
        self.clear_progress_bar()

        for version_id, info in self.model_version_info_dict.items():
            version_name = info['name']
            image_urls = info['image_url']
            # Avoid recognizing the name as a folder during path concatenation when it contains / or \ in its name
            fixed_model_name = self.model_name.replace('/', '_').replace('\\', '_')
            path = self.save_dir / fixed_model_name / version_name
            path.mkdir(parents=True, exist_ok=True)

            self.add_progress_bar(version_id, len(image_urls))

            for url in image_urls:
                image_path = path / url.split('/')[-1]
                downloader = CivitaImageDownloadRunner(version_id, url, image_path, self.httpx_client)
                downloader.signals.image_download_started_signal.connect(self.handle_image_download_started_signal)
                downloader.signals.image_download_fail_signal.connect(self.handle_image_download_fail_signal)
                downloader.signals.image_download_completed_signal.connect(self.handle_image_download_completed_signal)
                self.pool.start(downloader)

    def add_progress_bar(self, version_id: str, image_count: int):
        self.progress_bar_alive_list.append(version_id)
        # about progress_bar_info:
        # {version_id: [ProgressBar widget object, downloaded, executed, Quantity of all images], ... }
        self.progress_bar_info[version_id] = [QProgressBar(maximum=image_count), 0, 0, image_count]
        self.ui.verticalLayout.addWidget(self.progress_bar_info[version_id][0])

    def handle_image_download_started_signal(self, started_message: str):
        self.download_history_list.append(f'{datetime.now().strftime("%m-%d %H:%M:%S")} : {started_message}')

    def handle_image_download_fail_signal(self, fail_info: tuple):
        version_id, fail_message = fail_info
        self.progress_bar_info[version_id][2] += 1  # executed count

        download_fail_url = fail_message.split(':')[-1].strip()
        if version_id not in self.download_failed_urls_dict:
            self.download_failed_urls_dict[version_id] = []
        self.download_failed_urls_dict[version_id].append(download_fail_url)
        self.download_history_list.append(f'{datetime.now().strftime("%m-%d %H:%M:%S")} : {fail_message}')

        self.handle_download_task(version_id)

    def handle_image_download_completed_signal(self, completed_info: tuple):
        version_id, completed_message = completed_info
        self.progress_bar_info[version_id][2] += 1  # executed count

        downloaded_count = self.progress_bar_info[version_id][1] + 1
        self.progress_bar_info[version_id][1] = downloaded_count
        self.progress_bar_info[version_id][0].setValue(downloaded_count)
        self.download_history_list.append(f'{datetime.now().strftime("%m-%d %H:%M:%S")} : {completed_message}')

        self.handle_download_task(version_id)

    def handle_download_task(self, version_id: str):
        version_progress_bar_info = self.progress_bar_info[version_id]
        if version_progress_bar_info[2] == version_progress_bar_info[3]:
            self.progress_bar_alive_list.remove(version_id)

        if not self.progress_bar_alive_list:
            self.ui.url_line_edit.setEnabled(True)
            self.ui.parser_push_button.setEnabled(True)
            self.ui.choose_folder_button.setEnabled(True)

            self.ui.result_text_browser.append(f'Download task for "{self.model_name}" has been completed')
            self.ui.result_text_browser.append(
                'If the progress bar is not at 100%, it means there are URLs that failed to download. Please go to '
                'Help > Show Failed URLs to view them.'
            )

    def text_browser_insert_html(self, html_string: str):
        self.ui.parser_text_browser.append('')
        self.ui.parser_text_browser.insertHtml(html_string)
        self.ui.parser_text_browser.setCurrentCharFormat(QTextCharFormat())

    @staticmethod
    def convert_failed_urls_dict_to_list(download_fail_url_dict: dict) -> list:
        download_failed_urls_list = []
        for version_id,  fail_urls in download_fail_url_dict.items():
            download_failed_urls_list.append(f'{version_id}:')
            download_failed_urls_list.extend(iter(fail_urls))
        return download_failed_urls_list

    def clear_progress_bar(self):
        """
        Clear all progress bars
        :return:
        """
        if self.progress_bar_info:
            for value in self.progress_bar_info.values():
                widget = value[0]
                self.ui.verticalLayout.removeWidget(widget)
                widget.setParent(None)
            self.progress_bar_info.clear()

    def clear_threadpool(self):
        self.pool.clear()


if __name__ == "__main__":
    app = QApplication([])
    window = MainWindow()
    if sys.platform == 'darwin' and 'Fusion' in QStyleFactory.keys():
        app.setStyle(QStyleFactory.create('Fusion'))
    window.show()
    app.aboutToQuit.connect(window.clear_threadpool)
    sys.exit(app.exec())
