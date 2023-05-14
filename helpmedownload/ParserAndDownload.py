import re
from pathlib import Path

import httpx
from PySide6.QtCore import QObject, Signal, QRunnable, Slot


class CivitalUrlParserRunnerSignals(QObject):
    UrlParser_progress_signal = Signal(str)
    UrlParser_status_signal = Signal(tuple)
    UrlParser_completed_signal = Signal(tuple)


class CivitalUrlParserRunner(QRunnable):
    """
    Parse the URL to obtain the model name and its related information. (self.model_name, self.model_version_info_dict)
    """
    def __init__(self, url: str, test_mode=False):
        """
        :param url:
        :param test_mode: set to True, only the URL will be parsed without attempting to connect and obtain information
        """
        super().__init__()
        self.civitai_models_api_url = r'https://civitai.com/api/v1/models/'
        self.civitai_image_api_url = r'https://civitai.com/api/v1/images'

        self.httpx_client = httpx.Client()
        self.signals = CivitalUrlParserRunnerSignals()

        self.url = url
        self.test_mode = test_mode

        self.model_name = ''
        self.model_version_info_dict = {}

    @Slot()
    def run(self) -> None:
        self.signals.UrlParser_progress_signal.emit(f'Start to parser {self.url}')
        if parser_result := self.get_model_and_version_and_status(self.url, self.test_mode):
            # test_mode, parser failed, connection failed, none of them continue
            if parser_result[-1]:
                self.get_model_version_info(*parser_result[:-1])
                self.signals.UrlParser_completed_signal.emit((self.model_name, self.model_version_info_dict))

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
            self.signals.UrlParser_status_signal.emit((m_id, v_id, status))
            return m_id, v_id, status
        elif match := re.search(r'models/(?P<model_id>\d{4,5})/', url):
            m_id = match['model_id']
            self.signals.UrlParser_status_signal.emit((m_id, None, status))
            return m_id, None, status
        else:
            self.signals.UrlParser_status_signal.emit((None, None, False))  # parser fails, set the status to false
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
        self.signals.image_download_started_signal.emit(f'Start to: {self.url}')

        try:
            response = self.httpx_client.get(self.url, follow_redirects=True)
            response.raise_for_status()

            if response.status_code == httpx.codes.OK:
                with open(f'{self.save_path}', 'wb') as f:
                    for data in response.iter_bytes():
                        f.write(data)
                self.signals.image_download_completed_signal.emit((self.version_id, f'Finished: {self.url}'))
            elif response.status_code == httpx.codes.FOUND:
                self.url = response.headers.get('Location')
                return self.run()
            else:
                raise ValueError(f"Unexpected status code {response.status_code}")

        except httpx.HTTPStatusError as e:
            print(f'Failed to download image from {self.url}. Reason: {str(e)}')
            self.signals.image_download_fail_signal.emit(f'Warning:: download fail: {self.url}')
        except httpx.ReadTimeout as e:
            print(f'ReadTimeout: {self.url}')
        except Exception as e:
            print(f'{e= }, {self.url}')
        # todo: handle exception, need to control "handle_progress_bar_value_changed" (main.py)
        # todo: Handle incomplete download (need to enable some buttons)
