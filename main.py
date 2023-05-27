import sys
from datetime import datetime
from pathlib import Path

import httpx
from PySide6.QtCore import QThreadPool, Qt
from PySide6.QtGui import QTextCharFormat
from PySide6.QtWidgets import QApplication, QMainWindow, QStyleFactory, QFileDialog, QProgressBar, QHBoxLayout, QLabel, \
    QCheckBox, QMessageBox

from helpmedownload.ParserAndDownload import CivitalUrlParserRunner, CivitaImageDownloadRunner
from helpmedownload.ShowHistoryWindow import HistoryWindow
from helpmedownload.BatchUrlsWindow import LoadingBatchUrlsWindow
from helpmedownload.untitled_main import Ui_MainWindow


class MainWindow(QMainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        self.pool = QThreadPool.globalInstance()
        self.httpx_client = httpx.Client()

        self.batch_url_list = []

        self.model_name = ''
        self.model_and_version_id = ()
        self.model_version_info_dict = {}
        self.save_dir = ''
        self.progress_bar_alive_list = []
        self.progress_bar_info = {}
        self.download_failed_count_each_model = 0
        self.download_history_list = []
        self.download_failed_urls_dict = {}

        self.ui.actionShowHistory.triggered.connect(lambda: self.trigger_show_action(self.download_history_list))
        self.ui.actionShowFailUrl.triggered.connect(lambda: self.trigger_show_action(
            history=self.convert_failed_urls_dict_to_list(self.download_failed_urls_dict),
            special=True
        ))
        self.ui.choose_folder_button.clicked.connect(self.click_choose_folder_button)
        self.ui.batch_push_button.clicked.connect(self.chick_batch_button)
        self.ui.go_push_button.clicked.connect(self.click_go_button)

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
        if folder := QFileDialog.getExistingDirectory(self, "Select Folder", options=options):
            self.ui.folder_line_edit.setText(folder)
            self.save_dir = Path(folder)

    def chick_batch_button(self):
        """
        Pop up a QDialog window for handling bulk urls
        :return:
        """
        if not self.save_dir:
            QMessageBox.warning(self, 'Warning', 'Please set up save folder first.')
            return

        load_urls_window = LoadingBatchUrlsWindow(batch_url_list=self.batch_url_list, parent=self)
        load_urls_window.loading_batch_urls_signal.connect(self.handle_loading_batch_urls_signal)
        load_urls_window.setWindowModality(Qt.ApplicationModal)
        load_urls_window.show()

    def handle_loading_batch_urls_signal(self, url_list: list):
        self.batch_url_list = url_list
        for url in self.batch_url_list:
            self.click_go_button(url_from_batch=url)


    def click_go_button(self, url_from_batch: str = '') -> None:
        """
        Parse the URL and using QThreadPool
        :return:
        """
        if not self.save_dir:
            QMessageBox.warning(self, 'Warning', 'Please set up save folder first.')
            return

        self.able_buttons_and_edit(enable=False)
        url = url_from_batch or self.ui.url_line_edit.text()

        civital_url_parser = CivitalUrlParserRunner(url, self.httpx_client)
        civital_url_parser.signals.UrlParser_started_signal.connect(self.handle_parser_started_signal)
        civital_url_parser.signals.UrlParser_preliminary_signal.connect(self.handle_parser_preliminary_signal)
        civital_url_parser.signals.UrlParser_connect_to_api_failed_signal.connect(
            self.handle_parser_connect_to_api_failed_signal)
        civital_url_parser.signals.UrlParser_completed_signal.connect(self.handle_parser_completed_signal)

        self.pool.start(civital_url_parser)

    def handle_parser_started_signal(self, started_message: str) -> None:
        """
        Display the string message received from UrlParser_started_signal in the operation_text_browser
        :param started_message:
        :return:
        """
        self.ui.operation_text_browser.append(started_message)

    def handle_parser_preliminary_signal(self, model_id_and_version_id_and_status: tuple) -> None:
        """
        Display the corresponding content based on the contents of "model_and_version_and_status"
        in the operation_text_browser
        :param model_id_and_version_id_and_status:
        :return:
        """
        self.model_and_version_id = model_id_and_version_id_and_status[:2]
        status, error_message, url = model_id_and_version_id_and_status[2:]

        match status:
            case None:  # parser test mode
                self.operation_browser_insert_html(
                    f'<span style="color: green;">Test mode: {self.model_and_version_id= }</span><br>'
                )
                self.able_buttons_and_edit()
            case False:  # parse failed or connection failed
                if self.model_and_version_id == (None, None):
                    self.operation_browser_insert_html(
                        f'<span style="color: pink;">{url} | parse failed. {error_message}</span><br>'
                    )
                else:
                    self.ui.operation_text_browser.append(
                        f'{url} parse success [{str(self.model_and_version_id)}], '
                        f'but connect to URL fail. {error_message}'
                    )
                    self.ui.operation_text_browser.append('')
                    self.ui.statusbar.showMessage('Connect to URL fail.', 3000)
                self.operation_browser_insert_html(
                    '<span style="color: pink;">Confirm the url and try again.</span><br>', newline_first=False
                )
                self.able_buttons_and_edit()
            case _:
                self.ui.operation_text_browser.append(f'{url} | parse success [{str(self.model_and_version_id)}]')

    def handle_parser_connect_to_api_failed_signal(self, failed_message: str) -> None:
        """
        Display the string message received from UrlParser_connect_to_api_failed_signal in the operation_text_browser
        :param failed_message:
        :return:
        """
        self.operation_browser_insert_html(
            f'<span style="color: pink;">{failed_message}</span><br>'
        )
        self.able_buttons_and_edit()

    def handle_parser_completed_signal(self, info: tuple) -> None:
        """
        Receive the parser_completed_signal information(the complete analysis is finished)
        and call the start_to_download function
        :param info:
        :return:
        """
        self.model_name, self.model_version_info_dict, url = info

        if not self.model_version_info_dict:
            self.operation_browser_insert_html(
                f'<span style="color: pink;">{url} | Unable to retrieve content from the API. '
                f'Please check the URL.</span><br>'
            )
            self.able_buttons_and_edit()
            return

        self.ui.operation_text_browser.append(f'{url} | Preparation complete. Start to download')
        self.ui.operation_text_browser.append('')

        self.start_to_download()
        # self.add_checkbox_option()  #  not implemented

    def add_checkbox_option(self):
        # test function,  not implemented
        checkbox = QCheckBox('box')
        self.ui.gridLayout_for_checkbox.addWidget(checkbox, self.ui.gridLayout_for_checkbox.count(), 0)

    def start_to_download(self) -> None:
        """
        Start to download all images
        :return:
        """
        self.clear_progress_bar()
        self.download_failed_count_each_model = 0

        for version_id, info in self.model_version_info_dict.items():
            version_name = info['name']
            image_urls = info['image_url']
            # Skip versions that no longer have images available
            if not image_urls:
                continue

            # Avoid recognizing the name as a folder during path concatenation when it contains / or \ in its name
            fixed_model_name = self.model_name.replace('/', '_').replace('\\', '_')
            dir_path = self.save_dir / Path(fixed_model_name) / Path(version_name)
            dir_path.mkdir(parents=True, exist_ok=True)

            self.add_progress_bar(version_id, version_name, len(image_urls))

            for url in image_urls:
                image_path = dir_path / url.split('/')[-1]
                downloader = CivitaImageDownloadRunner(version_id, version_name, url, image_path, self.httpx_client)
                downloader.signals.Image_download_started_signal.connect(self.handle_image_download_started_signal)
                downloader.signals.Image_download_fail_signal.connect(self.handle_image_download_failed_signal)
                downloader.signals.Image_download_completed_signal.connect(self.handle_image_download_completed_signal)
                self.pool.start(downloader)

    def add_progress_bar(self, version_id: str, version_name: str, image_count: int) -> None:
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
        # {version_id: [ProgressBar widget, Downloaded, Executed, Quantity of all images, ProgressBar Layout], ... }
        self.progress_bar_info[version_id] = [progress_bar, 0, 0, image_count, progress_layout]
        self.ui.verticalLayout.addLayout(progress_layout)

    def handle_image_download_started_signal(self, started_message: str):
        self.download_history_list.append(f'{datetime.now().strftime("%m-%d %H:%M:%S")} : {started_message}')

    def handle_image_download_failed_signal(self, fail_info: tuple):
        version_id, fail_message = fail_info
        self.progress_bar_info[version_id][2] += 1  # executed count
        self.download_failed_count_each_model += 1

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

    def handle_download_task(self, version_id: str) -> None:
        """
        Detect and handle the download progress of individual version images
        :param version_id:
        :return:
        """
        version_progress_bar_info = self.progress_bar_info[version_id]
        if version_progress_bar_info[2] == version_progress_bar_info[3]:
            self.progress_bar_alive_list.remove(version_id)

        if not self.progress_bar_alive_list:
            self.ui.result_text_browser.append(
                f'{datetime.now().strftime("%m-%d %H:%M:%S")} '
                f'Download task for "{self.model_name}" has been completed.<br>'
            )
            if self.download_failed_count_each_model:
                self.ui.result_text_browser.insertHtml(
                    '<span style="color: red;">'
                    f'{self.model_name}: {self.download_failed_count_each_model} images failed to downloaded. '
                    'Go to Help &gt; Show Failed URLs to view them.</span><br>'
                )
            self.able_buttons_and_edit()

    def operation_browser_insert_html(self, html_string: str, newline_first: bool = True):
        if newline_first:
            self.ui.operation_text_browser.append('')
        self.ui.operation_text_browser.insertHtml(html_string)
        self.ui.operation_text_browser.setCurrentCharFormat(QTextCharFormat())

    @staticmethod
    def convert_failed_urls_dict_to_list(download_fail_url_dict: dict) -> list:
        download_failed_urls_list = []
        for version_id,  fail_urls in download_fail_url_dict.items():
            download_failed_urls_list.append(f'Version ID: {version_id}')
            download_failed_urls_list.extend(iter(fail_urls))
        return download_failed_urls_list

    def able_buttons_and_edit(self, enable: bool = True) -> None:
        """
        Enable/Disable buttons and url editor
        :param enable:
        :return:
        """
        self.ui.choose_folder_button.setEnabled(enable)
        self.ui.batch_push_button.setEnabled(enable)
        self.ui.url_line_edit.setEnabled(enable)
        self.ui.go_push_button.setEnabled(enable)

    def clear_progress_bar(self) -> None:
        """
        Clear all progress bar layout
        :return:
        """
        if self.progress_bar_info:
            for value in self.progress_bar_info.values():
                layout = value[4]
                self.clear_layout_widgets(layout)
            self.progress_bar_info.clear()

    def clear_layout_widgets(self, layout) -> None:
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
