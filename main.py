import re
import sys
from pathlib import Path

import httpx
from PySide6.QtCore import QObject, Signal, QThread, QRunnable, Slot, QThreadPool
from PySide6.QtGui import QTextCharFormat
from PySide6.QtWidgets import QApplication, QMainWindow, QStyleFactory, QFileDialog, QProgressBar

from helpmedownload.untitled_main import Ui_MainWindow


class CivitalUrlParserWorker(QObject):
    """
    Parse the URL to obtain the model name and its related information. (self.model_name, self.model_version_info_dict)
    """
    UrlParser_progress_signal = Signal(str)
    UrlParser_status_signal = Signal(tuple)
    UrlParser_completed_signal = Signal(tuple)

    def __init__(self, url: str, test_mode=False):
        """
        :param url:
        :param test_mode: set to True, only the URL will be parsed without attempting to connect and obtain information
        """
        super().__init__()
        self.civitai_models_api_url = r'https://civitai.com/api/v1/models/'
        self.civitai_image_api_url = r'https://civitai.com/api/v1/images'

        self.httpx_client = httpx.Client()

        self.url = url
        self.test_mode = test_mode

        self.model_name = ''
        self.model_version_info_dict = {}

    def parser(self):
        self.UrlParser_progress_signal.emit(f'Start to parser {self.url}')
        if parser_result := self.get_model_and_version_and_status(self.url, self.test_mode):
            # test_mode, parser failed, connection failed, none of them continue
            if parser_result[-1]:
                self.get_model_version_info(*parser_result[:-1])
                self.UrlParser_completed_signal.emit((self.model_name, self.model_version_info_dict))

    def get_model_and_version_and_status(self, url: str = '', test_mode: bool = False) -> tuple | bool:
        """
        Get the analysis result and connection status of the URL, and emit the information ( M_ID, V_ID, status)
        :param url:
        :param test_mode: set to True, only the URL will be parsed without attempting to connect and obtain information
        :return:
        """
        if test_mode:
            status = None
        else:
            try:
                status = self.httpx_client.get(url).status_code == httpx.codes.OK
            except (httpx.TimeoutException, httpx.RequestError) as e:
                status = False

        if match := re.search(r'models/(?P<model_id>\d{4,5})[?]modelVersionId=(?P<model_version_id>\d{5})', url):
            m_id, v_id = match['model_id'], match['model_version_id']
            self.UrlParser_status_signal.emit((m_id, v_id, status))
            return m_id, v_id, status
        elif match := re.search(r'models/(?P<model_id>\d{4,5})/', url):
            m_id = match['model_id']
            self.UrlParser_status_signal.emit((m_id, None, status))
            return m_id, None, status
        else:
            self.UrlParser_status_signal.emit((None, None, False))  # the url parser fails, set the status to false
            return False

    def get_model_version_info(self, model_id: str = '', model_version_id: str = '') -> None:
        """
        Get the information {version id: {version name, creator name, image url}} contained in the model.
        {'version_id': {'name': version_name, 'creator': creator_name, 'image_url': ['url1', 'url2', ..]}, ... }
        :param model_id:
        :param model_version_id:
        :return:
        """
        response = self.httpx_client.get(self.civitai_models_api_url + model_id)

        if response.status_code == httpx.codes.OK:
            models_json_data = response.json()
            self.model_name = models_json_data['name']
            creator_name = models_json_data['creator']['username']

            for version in models_json_data.get('modelVersions'):
                version_id = str(version['id'])
                version_name = version['name']

                # for only downloading a specific version
                if model_version_id:
                    if version_id != model_version_id:
                        continue
                    self.construct_model_version_info_dict(version_id, version_name, creator_name)
                    return

                self.construct_model_version_info_dict(version_id, version_name, creator_name)

    def construct_model_version_info_dict(self, version_id, version_name, creator_name) -> None:
        """
        Construct model_version_info_dict
        :param version_id:
        :param version_name:
        :param creator_name:
        :return:
        """
        self.model_version_info_dict[version_id] = {
            'name': version_name,
            'creator': creator_name,
            'image_url': [],
        }
        self.get_image_url(version_id, creator_name)

    def get_image_url(self, version_id: str, username: str) -> None:
        """
        Get the URL of the example image provided by the creator and write it to
        self.model_version_info_dict[version_id]['image_url']
        :return:
        """
        params = {
            'modelVersionId': version_id,
            'username': username,
        }

        response = self.httpx_client.get(self.civitai_image_api_url, params=params)

        if response.status_code == 200:
            image_json_data = response.json()
            for image_info in image_json_data.get('items'):
                image_url = image_info.get('url')
                self.model_version_info_dict[version_id]['image_url'].append(image_url)


class CivitaImageDownloadRunnerSignals(QObject):
    """
    Signals for CivitaImageDownloadRunner class
    """
    image_download_started_signal = Signal(str)
    image_download_fail_signal = Signal(str)
    image_download_completed_signal = Signal(tuple)


class CivitaImageDownloadRunner(QRunnable):
    """
    Download images with support for QThreadPool
    """
    def __init__(self, version_id: str, image_url: str, save_path: Path, client: httpx.Client):
        super().__init__()
        self.version_id = version_id
        self.url = image_url
        self.save_path = save_path
        self.httpx_client = client
        self.signals = CivitaImageDownloadRunnerSignals()

    @Slot()
    def run(self) -> None:
        self.signals.image_download_started_signal.emit(f'Start to download {self.url}')

        try:
            response = self.httpx_client.get(self.url, follow_redirects=True)
            response.raise_for_status()

            if response.status_code == httpx.codes.OK:
                with open(f'{self.save_path}', 'wb') as f:
                    for data in response.iter_bytes():
                        f.write(data)
                self.signals.image_download_completed_signal.emit((self.version_id, f'{self.url} downloaded'))
            elif response.status_code == httpx.codes.FOUND:
                self.url = response.headers.get('Location')
                return self.run()
            else:
                raise ValueError(f"Unexpected status code {response.status_code}")

        except httpx.HTTPStatusError as e:
            print(f'Failed to download image from {self.url}. Reason: {str(e)}')
            self.signals.image_download_fail_signal.emit(f'{self.url} fail')


class MainWindow(QMainWindow):
    Signal_to_CivitalUrlParserWorker = Signal()

    def __init__(self):
        super(MainWindow, self).__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        self.pool = QThreadPool.globalInstance()
        self.httpx_client = httpx.Client()

        self.ui.ready_to_go_push_button.setEnabled(False)

        self.model_name = ''
        self.model_and_version_id = ()
        self.model_version_info_dict = {}
        self.save_dir = ''
        self.progress_bar_list = []
        self.progress_bar_info = {}

        self.civital_url_parser_worker = None
        self.civital_url_parser_worker_thread = None

        self.ui.url_line_edit.textChanged.connect(lambda: self.ui.ready_to_go_push_button.setEnabled(False))

        self.ui.parser_push_button.clicked.connect(self.click_parser_button)
        self.ui.choose_folder_button.clicked.connect(self.click_choose_folder_button)
        self.ui.ready_to_go_push_button.clicked.connect(self.click_ready_to_go_button)

    def click_parser_button(self):
        """
        # todo: ...
        :return:
        """
        url = self.ui.url_line_edit.text()
        self.civital_url_parser_worker = CivitalUrlParserWorker(url)
        self.civital_url_parser_worker_thread = QThread()

        self.civital_url_parser_worker.UrlParser_progress_signal.connect(self.handle_parser_progress_signal)
        self.civital_url_parser_worker.UrlParser_status_signal.connect(self.handle_parser_status_signal)
        self.civital_url_parser_worker.UrlParser_completed_signal.connect(self.handle_parser_completed_signal)

        self.Signal_to_CivitalUrlParserWorker.connect(self.civital_url_parser_worker.parser)

        self.civital_url_parser_worker.moveToThread(self.civital_url_parser_worker_thread)

        self.Signal_to_CivitalUrlParserWorker.emit()

        self.civital_url_parser_worker_thread.start()

    def handle_parser_progress_signal(self, string: str):
        self.ui.parser_text_browser.append(string)

    def handle_parser_status_signal(self, model_and_version_and_status: tuple):
        """
        enable 'ready_to_go' button
        """
        status = model_and_version_and_status[-1]
        self.model_and_version_id = model_and_version_and_status[:-1]

        match status:
            case None:
                self.ui.parser_text_browser.append('')
                self.ui.parser_text_browser.insertHtml(
                    f'<span style="color: green;">Test mode: {self.model_and_version_id= }</span>')
                self.ui.parser_text_browser.setCurrentCharFormat(QTextCharFormat())
                self.reset_parser_thread()
            case False:
                if self.model_and_version_id == (None, None):
                    self.ui.statusbar.showMessage('Url parser fail.', 3000)
                else:
                    self.ui.parser_text_browser.append(str(self.model_and_version_id))
                    self.ui.statusbar.showMessage('Connect to url fail.', 3000)
                self.reset_parser_thread()
            case _:
                self.ui.parser_text_browser.append(str(self.model_and_version_id))

    def handle_parser_completed_signal(self, info: tuple):
        self.model_name, self.model_version_info_dict = info
        self.reset_parser_thread()
        self.ui.result_text_browser.append('get model_version_info')
        if self.save_dir:
            self.ui.ready_to_go_push_button.setEnabled(True)
        else:
            self.ui.result_text_browser.append('need to set folder before parser')

        print(f'{self.model_version_info_dict=}')
        print(f'{len(self.model_version_info_dict)=}')

    def reset_parser_thread(self):
        self.civital_url_parser_worker_thread.quit()
        self.civital_url_parser_worker_thread.wait()
        self.civital_url_parser_worker_thread = None

    def click_choose_folder_button(self):
        options = QFileDialog.Options()
        options |= QFileDialog.ShowDirsOnly
        folder = QFileDialog.getExistingDirectory(self, "Select Folder", options=options)
        self.ui.folder_line_edit.setText(folder)
        self.save_dir = Path(folder)

    def click_ready_to_go_button(self):
        """
        need: self.model_version_info_dict is correct
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
            path = self.save_dir / self.model_name / version_name
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
        self.progress_bar_list.append(version_id)
        self.progress_bar_info[version_id] = [QProgressBar(maximum=image_count), 0, image_count]
        self.progress_bar_info[version_id][0].valueChanged.connect(
            lambda value: self.handle_progress_bar_value_changed(value, version_id, image_count))
        self.ui.verticalLayout.addWidget(self.progress_bar_info[version_id][0])

    def handle_image_download_started_signal(self, string: str):
        self.ui.result_text_browser.append(string)

    def handle_image_download_fail_signal(self, string: str):
        self.ui.result_text_browser.append(string)

    def handle_image_download_completed_signal(self, info: tuple):
        version_id, string = info
        count = self.progress_bar_info[version_id][1] + 1
        self.progress_bar_info[version_id][1] = count
        self.progress_bar_info[version_id][0].setValue(count)
        self.ui.result_text_browser.append(string)

        if not self.progress_bar_list:
            self.ui.url_line_edit.setEnabled(True)
            self.ui.parser_push_button.setEnabled(True)
            self.ui.choose_folder_button.setEnabled(True)

    def handle_progress_bar_value_changed(self, value, version_id, image_count):
        if value == image_count:
            self.progress_bar_list.remove(version_id)

    def clear_progress_bar(self):
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
