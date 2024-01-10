from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import httpx
from PySide6.QtCore import QThreadPool, Qt
from PySide6.QtGui import QTextCharFormat, QMouseEvent
from PySide6.QtWidgets import QMainWindow, QFileDialog, QProgressBar, QHBoxLayout, QLabel, QCheckBox, QMessageBox

from helpmedownload.ParserAndDownload import CivitaiUrlParserRunner, CivitaiImageDownloadRunner, VersionInfoData
from helpmedownload.ShowHistoryWindow import HistoryWindow
from helpmedownload.BatchUrlsWindow import LoadingBatchUrlsWindow
from helpmedownload.HelpMeDownlaod_UI import Ui_MainWindow


@dataclass(slots=True)
class ProgressBarData:
    progress_layout: QHBoxLayout
    progress_bar_widget: QProgressBar
    completed: int
    executed: int
    quantity: int


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super(MainWindow, self).__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        self.pool: QThreadPool = QThreadPool.globalInstance()
        self.httpx_client: httpx.Client = httpx.Client()

        self.batch_mode: bool = False
        self.batch_url: list = []
        self.processing_batch_url_list: list = []
        self.connect_failed_batch_url_list: list = []

        self.url: str = ''
        self.model_and_version_id: tuple = ()
        self.save_dir: Path | None = None
        self.progress_bar_alive_list: list = []
        self.progress_bar_info: dict = {}
        self.download_failed_count_each_model: int = 0
        self.download_history_list: list = []
        self.download_failed_urls_dict: dict = {}

        self.ui.actionShowHistory.triggered.connect(lambda: self.trigger_show_action(self.download_history_list))
        self.ui.actionShowFailUrl.triggered.connect(lambda: self.trigger_show_action(
            history=self.convert_failed_urls_dict_to_list(self.download_failed_urls_dict),
            special=True
        ))
        # self.ui.choose_folder_button.clicked.connect(self.select_storage_folder)
        self.ui.folder_line_edit.mousePressEvent = self.select_storage_folder
        self.ui.batch_push_button.clicked.connect(self.click_batch_button)
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

    def select_storage_folder(self, event: QMouseEvent) -> None:
        """
        Set the path of a folder for saving images
        :return:
        """
        if event.button() == Qt.LeftButton:
            if folder_path := QFileDialog.getExistingDirectory(self, "Select Folder", options=QFileDialog.ShowDirsOnly):
                self.ui.folder_line_edit.setText(folder_path)
                self.save_dir = Path(folder_path)

    def click_batch_button(self):
        """
        Pop up a QDialog window for handling batch urls
        :return:
        """
        if not self.save_dir:
            QMessageBox.warning(self, 'Warning', 'Set the storage folder first')
            return

        load_urls_window = LoadingBatchUrlsWindow(batch_url_list=self.batch_url, parent=self)
        load_urls_window.loading_batch_urls_signal.connect(self.handle_loading_batch_urls_signal)
        load_urls_window.setWindowModality(Qt.ApplicationModal)
        load_urls_window.show()

    def handle_loading_batch_urls_signal(self, url_list: list):
        self.batch_url = self.processing_batch_url_list = url_list
        self.batch_mode = True
        self.download_from_batch_url()

    def download_from_batch_url(self):
        try:
            url = self.processing_batch_url_list.pop(0)
            self.click_go_button(url_from_batch=url)
        except IndexError:
            self.batch_mode = False
            self.batch_url = self.connect_failed_batch_url_list
            self.connect_failed_batch_url_list.clear()
            self.enable_buttons_and_edit()
            return

    def click_go_button(self, url_from_batch: str = '') -> None:
        """
        Parse the URL (using QThreadPool)
        :param url_from_batch:
        :return:
        """
        if not self.save_dir:
            QMessageBox.warning(self, 'Warning', 'Set the storage folder first')
            return

        self.enable_buttons_and_edit(enable=False)
        self.url = url_from_batch or self.ui.url_line_edit.text().strip()

        if not self.url:
            self.operation_browser_insert_html(
                '<span style="color: red;">*** No URL ***</span>'
            )
            self.enable_buttons_and_edit()
            return

        civitai_url_parser = CivitaiUrlParserRunner(self.url, self.httpx_client)
        civitai_url_parser.signals.UrlParser_Start_Signal.connect(self.handle_parser_started_signal)
        civitai_url_parser.signals.UrlParser_preliminary_signal.connect(self.handle_parser_preliminary_signal)
        civitai_url_parser.signals.UrlParser_Fail_Signal.connect(self.handle_parser_connect_to_api_failed_signal)
        civitai_url_parser.signals.UrlParser_Complete_Signal.connect(self.handle_parser_completed_signal)

        self.pool.start(civitai_url_parser)

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
        assert url == self.url

        match status:
            case None:  # parser test mode
                self.operation_browser_insert_html(
                    f'<span style="color: green;">Test mode: {self.model_and_version_id= }</span><br>'
                )
                self.enable_buttons_and_edit()
            case False:  # parse failed or connection failed
                if self.model_and_version_id == (None, None):
                    self.operation_browser_insert_html(
                        f'<span style="color: pink;">{url} | Parse failed. {error_message}</span><br>'
                    )
                else:
                    self.ui.operation_text_browser.append(
                        f'{url} | Parse success [{str(self.model_and_version_id)}], '
                        f'but connection to the URL failed. {error_message}'
                    )
                    self.ui.statusbar.showMessage('Connection to the URL failed.', 3000)
                self.operation_browser_insert_html(
                    '<span style="color: pink;">Confirm the URL. '
                    'If there are no errors, it may be due to a connection issue. Try again later</span>'
                )
                if not self.batch_mode:
                    self.enable_buttons_and_edit()
                else:
                    self.connect_failed_batch_url_list.append(url)
                    self.download_from_batch_url()
            case _:
                self.ui.operation_text_browser.append(f'{url} | Parse success [{str(self.model_and_version_id)}]')

    def handle_parser_connect_to_api_failed_signal(self, failed_message: tuple) -> None:
        """
        Display the string message received from UrlParser_connect_to_api_failed_signal in the operation_text_browser
        :param failed_message:
        :return:
        """
        message, url = failed_message
        assert url == self.url

        self.operation_browser_insert_html(
            f'<span style="color: pink;">{message}</span><br>'
        )
        if not self.batch_mode:
            self.enable_buttons_and_edit()
        else:
            self.connect_failed_batch_url_list.append(url)
            self.download_from_batch_url()

    def handle_parser_completed_signal(self, completed_message: tuple) -> None:
        """
        Receive the parser_completed_signal information(the complete analysis is finished)
        and call the start_to_download function
        :param completed_message:
        :return:
        """
        model_name, model_version_info, url = completed_message
        assert url == self.url

        if not model_version_info:
            self.operation_browser_insert_html(
                f'<span style="color: pink;">{url} | Unable to retrieve content from the API. '
                f'Please check the URL.</span>'
            )
            if not self.batch_mode:
                self.enable_buttons_and_edit()
            else:
                self.connect_failed_batch_url_list.append(url)
                self.download_from_batch_url()
            return

        self.ui.operation_text_browser.append(f'{url} | Preparation complete. Start to download')
        self.start_to_download(model_name, model_version_info)
        # self.add_checkbox_option()  #  not implemented

    def add_checkbox_option(self):
        # test function,  not implemented
        checkbox = QCheckBox('box')
        self.ui.gridLayout_for_checkbox.addWidget(checkbox, self.ui.gridLayout_for_checkbox.count(), 0)

    def start_to_download(self, model_name: str, model_version_info: dict) -> None:
        """
        Start to download all images
        :return:
        """
        self.clear_progress_bar()
        self.download_failed_count_each_model = 0

        for version_id, version_info in model_version_info.items():
            version_info: VersionInfoData
            version_name = version_info.name
            image_urls = version_info.image_urls
            # Skip versions that no longer have images available
            if not image_urls:
                continue

            # Avoid recognizing the name as a folder during path concatenation when it contains / or \ in its name
            fixed_model_name = model_name.replace('/', '_').replace('\\', '_')
            dir_path = self.save_dir / Path(fixed_model_name) / Path(version_name)
            dir_path.mkdir(parents=True, exist_ok=True)

            self.add_progress_bar(version_id, version_name, len(image_urls))

            for url in image_urls:
                image_path = dir_path / url.split('/')[-1]
                downloader = CivitaiImageDownloadRunner(version_id, version_name, url, image_path, self.httpx_client)
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

        self.progress_bar_info[version_id] = ProgressBarData(progress_layout=progress_layout,
                                                             progress_bar_widget=progress_bar,
                                                             completed=0,
                                                             executed=0,
                                                             quantity=image_count)
        self.ui.verticalLayout.addLayout(progress_layout)

    def handle_image_download_started_signal(self, started_message: str):
        self.download_history_list.append(f'{datetime.now().strftime("%m-%d %H:%M:%S")} : {started_message}')

    def handle_image_download_failed_signal(self, fail_info: tuple):
        version_id, fail_message = fail_info
        bar_data: ProgressBarData = self.progress_bar_info[version_id]
        bar_data.executed += 1  # executed count
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
        bar_data: ProgressBarData = self.progress_bar_info[version_id]
        bar_data.executed += 1  # executed count

        downloaded_count = bar_data.completed + 1
        bar_data.completed = downloaded_count
        bar_data.progress_bar_widget.setValue(downloaded_count)
        self.download_history_list.append(f'{datetime.now().strftime("%m-%d %H:%M:%S")} : {completed_message}')

        self.handle_download_task(version_id)

    def handle_download_task(self, version_id: str) -> None:
        """
        Detect and handle the download progress of individual version images
        :param version_id:
        :return:
        """
        bar_data: ProgressBarData = self.progress_bar_info[version_id]
        if bar_data.executed == bar_data.quantity:
            self.progress_bar_alive_list.remove(version_id)

        if not self.progress_bar_alive_list:
            self.ui.result_text_browser.append(
                f'{datetime.now().strftime("%m-%d %H:%M:%S")} '
                f'Download task for "{self.url}" has been completed.<br>'
            )
            if self.download_failed_count_each_model:
                self.ui.result_text_browser.insertHtml(
                    '<span style="color: red;">'
                    f'{self.url}: {self.download_failed_count_each_model} images failed to downloaded. '
                    'Go to Help &gt; Show Failed URLs to view them.</span><br>'
                )
            if not self.batch_mode:
                self.enable_buttons_and_edit()
            else:
                self.download_from_batch_url()

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

    def enable_buttons_and_edit(self, enable: bool = True) -> None:
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
                value: ProgressBarData
                layout = value.progress_layout
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
