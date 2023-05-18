import sys
from datetime import datetime
from pathlib import Path

import httpx
from PySide6.QtCore import QThreadPool, Qt
from PySide6.QtGui import QTextCharFormat
from PySide6.QtWidgets import QApplication, QMainWindow, QStyleFactory, QFileDialog, QProgressBar, QHBoxLayout, QLabel

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
            history=self.convert_failed_urls_dict_to_list(self.download_failed_urls_dict),
            special=True
        ))
        self.ui.choose_folder_button.clicked.connect(self.click_choose_folder_button)
        self.ui.parse_push_button.clicked.connect(self.click_parse_button)
        self.ui.ready_to_go_push_button.clicked.connect(self.click_ready_to_go_button)

        # When url_line_edit or folder_line_edit is modified, request a re-parsing
        self.ui.url_line_edit.textChanged.connect(lambda: self.ui.ready_to_go_push_button.setEnabled(False))
        self.ui.folder_line_edit.textChanged.connect(lambda: self.ui.ready_to_go_push_button.setEnabled(False))

    def trigger_show_action(self, history: list, special: bool = False) -> None:
        """
        Pop up a QDialog window for show history
        :param history:
        :param special: special for display failed urls
        :return:
        """
        history_window = HistoryWindow(history=history, special=special, parent=self)
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
        self.ui.parse_push_button.setEnabled(False)
        self.ui.choose_folder_button.setEnabled(False)
        url = self.ui.url_line_edit.text()

        civital_url_parser = CivitalUrlParserRunner(url, self.httpx_client)
        civital_url_parser.signals.UrlParser_started_signal.connect(self.handle_parser_started_signal)
        civital_url_parser.signals.UrlParser_status_signal.connect(self.handle_parser_status_signal)
        civital_url_parser.signals.UrlParser_connect_failed_signal.connect(self.handle_parser_connect_failed_signal)
        civital_url_parser.signals.UrlParser_completed_signal.connect(self.handle_parser_completed_signal)

        self.pool.start(civital_url_parser)

    def handle_parser_started_signal(self, started_message: str):
        self.ui.parser_text_browser.append(started_message)

    def handle_parser_status_signal(self, model_and_version_and_status: tuple):
        """
        Display the corresponding content based on the contents of "model_and_version_and_status"
        """
        status, error_message = model_and_version_and_status[-2:]
        self.model_and_version_id = model_and_version_and_status[:-2]

        match status:
            case None:
                self.text_browser_insert_html(
                    f'<span style="color: green;">Test mode: {self.model_and_version_id= }</span><br>'
                )
                self.ui.parse_push_button.setEnabled(True)
                self.ui.choose_folder_button.setEnabled(True)
            case False:
                if self.model_and_version_id == (None, None):
                    self.text_browser_insert_html(
                        f'<span style="color: pink;">URL parse failed. {error_message}</span><br>'
                    )
                else:
                    self.ui.parser_text_browser.append(
                        f'URL parse success [{str(self.model_and_version_id)}], but connect to URL fail. {error_message}'
                    )
                    self.ui.parser_text_browser.append('')
                    self.ui.statusbar.showMessage('Connect to URL fail.', 3000)
                self.ui.parse_push_button.setEnabled(True)
                self.ui.choose_folder_button.setEnabled(True)
            case _:
                self.ui.parser_text_browser.append(f'URL parse success [{str(self.model_and_version_id)}]')

    def handle_parser_connect_failed_signal(self, failed_message: str):
        self.ui.parser_text_browser.insertHtml(
            f'<br><span style="color: pink;">{failed_message}</span><br>'
        )
        self.ui.parse_push_button.setEnabled(True)
        self.ui.choose_folder_button.setEnabled(True)

    def handle_parser_completed_signal(self, info: tuple):
        """
        If the complete analysis is finished, enable the "ready_to_go" button
        :param info:
        :return:
        """
        if self.save_dir:
            self.model_name, self.model_version_info_dict = info
            self.ui.parser_text_browser.append('Preparation complete. Click "Ready to go" to start the download')
            self.ui.parser_text_browser.append('')
            self.ui.ready_to_go_push_button.setEnabled(True)
        else:
            self.ui.parser_text_browser.insertHtml(
                '<br><span style="color: green;">Storage path is not set. Please configure it before parsing the URL again.</span><br>'
            )

        self.ui.parse_push_button.setEnabled(True)
        self.ui.choose_folder_button.setEnabled(True)

    def click_ready_to_go_button(self):
        """
        Start to download all images
        :return:
        """
        self.ui.url_line_edit.setEnabled(False)
        self.ui.parse_push_button.setEnabled(False)
        self.ui.choose_folder_button.setEnabled(False)
        self.ui.ready_to_go_push_button.setEnabled(False)
        self.clear_progress_bar()

        for version_id, info in self.model_version_info_dict.items():
            image_urls = info['image_url']
            # Skip versions that  no longer have images available
            if not image_urls:
                continue
            version_name = info['name']
            # Avoid recognizing the name as a folder during path concatenation when it contains / or \ in its name
            fixed_model_name = self.model_name.replace('/', '_').replace('\\', '_')
            path = self.save_dir / Path(fixed_model_name) / Path(version_name)
            path.mkdir(parents=True, exist_ok=True)

            self.add_progress_bar(version_id, version_name, len(image_urls))

            for url in image_urls:
                image_path = path / url.split('/')[-1]
                downloader = CivitaImageDownloadRunner(version_id, version_name, url, image_path, self.httpx_client)
                downloader.signals.Image_download_started_signal.connect(self.handle_image_download_started_signal)
                downloader.signals.Image_download_fail_signal.connect(self.handle_image_download_failed_signal)
                downloader.signals.Image_download_completed_signal.connect(self.handle_image_download_completed_signal)
                self.pool.start(downloader)

    def add_progress_bar(self, version_id: str, version_name: str, image_count: int):
        """
        Create a QLabel and QProgressBar (both within a QHBoxLayout)
        :param version_id:
        :param version_name:
        :param image_count:
        :return:
        """
        self.progress_bar_alive_list.append(version_id)

        progress_layout = QHBoxLayout()
        progress_label = QLabel(version_name)
        progress_bar = QProgressBar(maximum=image_count)
        progress_layout.addWidget(progress_label)
        progress_layout.addWidget(progress_bar)
        progress_layout.setStretch(0, 1)
        progress_layout.setStretch(1, 5)

        # about progress_bar_info:
        # {version_id: [ProgressBar widget object, Downloaded, Executed, Quantity of all images, ProgressBar Layout], ... }
        self.progress_bar_info[version_id] = [progress_bar, 0, 0, image_count, progress_layout]
        self.ui.verticalLayout.addLayout(self.progress_bar_info[version_id][4])

    def handle_image_download_started_signal(self, started_message: str):
        self.download_history_list.append(f'{datetime.now().strftime("%m-%d %H:%M:%S")} : {started_message}')

    def handle_image_download_failed_signal(self, fail_info: tuple):
        version_id, fail_message = fail_info
        self.progress_bar_info[version_id][2] += 1  # executed count

        # initialize self.download_failed_urls_dict
        if version_id not in self.download_failed_urls_dict:
            self.download_failed_urls_dict[version_id] = []

        download_failed_url = fail_message.split('::')[-1].strip()
        self.download_failed_urls_dict[version_id].append(download_failed_url)
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
            self.ui.parse_push_button.setEnabled(True)
            self.ui.choose_folder_button.setEnabled(True)

            self.ui.result_text_browser.append(
                f'Download task for "{self.model_name}" has been completed. {datetime.now().strftime("%m-%d %H:%M:%S")}'
            )
            self.ui.result_text_browser.insertHtml(
                '<br><span style="color: blue;">If the progress bar is not at 100%, it means there are URLs that '
                'failed to download. Please go to Help &gt; Show Failed URLs to view them.</span><br>'
            )

    def text_browser_insert_html(self, html_string: str):
        self.ui.parser_text_browser.append('')
        self.ui.parser_text_browser.insertHtml(html_string)
        self.ui.parser_text_browser.setCurrentCharFormat(QTextCharFormat())

    @staticmethod
    def convert_failed_urls_dict_to_list(download_fail_url_dict: dict) -> list:
        download_failed_urls_list = []
        for version_id,  fail_urls in download_fail_url_dict.items():
            download_failed_urls_list.append(f'Version ID: {version_id}')
            download_failed_urls_list.extend(iter(fail_urls))
        return download_failed_urls_list

    def clear_progress_bar(self):
        """
        Clear all progress bar layout
        :return:
        """
        if self.progress_bar_info:
            for value in self.progress_bar_info.values():
                layout = value[4]
                self.clear_layout_widgets(layout)
            self.progress_bar_info.clear()

    def clear_layout_widgets(self, layout):
        """
        Clears all widgets within a layout, including sub-layouts.
        :param layout:
        :return:
        """
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                self.clear_layout_widgets(item.layout())

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
