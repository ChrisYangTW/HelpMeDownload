import re
from pathlib import Path
from dataclasses import dataclass, field

import httpx
from PySide6.QtCore import QObject, Signal, QRunnable, Slot


@dataclass(slots=True)
class VersionInfoData:
    name: str
    creator: str
    image_urls: list = field(default_factory=list)
    file_info: dict = field(default_factory=dict)


class CivitalUrlParserRunnerSignals(QObject):
    """
    Signals for CivitalUrlParserRunner class
    """
    UrlParser_Start_Signal = Signal(str)
    UrlParser_preliminary_signal = Signal(tuple)
    UrlParser_Fail_Signal = Signal(tuple)
    UrlParser_Complete_Signal = Signal(tuple)


class CivitalUrlParserRunner(QRunnable):
    """
    Parse the URL to obtain the model name and its related information. (self.model_name, self.model_version_info)
    """
    def __init__(self, url: str, httpx_client: httpx.Client, test_mode=False):
        """
        :param url:
        :param httpx_client:
        :param test_mode: set to True, only the URL will be parsed without attempting to connect and obtain information
        """
        super().__init__()
        self.civitai_models_api_url: str = r'https://civitai.com/api/v1/models/'
        self.civitai_images_api_url: str = r'https://civitai.com/api/v1/images'

        self.url: str = url
        self.httpx_client: httpx.Client = httpx_client
        self.test_mode: bool = test_mode

        self.signals = CivitalUrlParserRunnerSignals()

        self.model_name = ''
        self.model_version_info: dict = {}

    @Slot()
    def run(self) -> None:
        self.signals.UrlParser_Start_Signal.emit(f'{self.url} | Start to parse ...')
        parser_result = self.get_model_id_and_version_id_and_status(test_mode=self.test_mode)
        # test mode, parse failed, connection failed, none of them continue
        if parser_result[-1]:
            self.get_model_version_info(*parser_result[:-1])

    def get_model_id_and_version_id_and_status(self, test_mode: bool = False) -> tuple:
        """
        Get the analysis result and connection status of the URL, and emit the information (M_ID, V_ID, status)
        to main thread
        :param test_mode: set to True, only the URL will be parsed without attempting to connect and obtain information
        :return:
        """
        error_message = ''

        if test_mode:
            status = None
        else:
            try:
                status = self.httpx_client.get(self.url).status_code == httpx.codes.OK
            except (httpx.TimeoutException, httpx.RequestError, httpx.ReadTimeout) as e:
                error_message = e
                status = False

        if match := re.search(r'models/(?P<model_id>\d{4,6})[?]modelVersionId=(?P<model_version_id>\d{4,6})', self.url):
            m_id, v_id = match['model_id'], match['model_version_id']
            self.signals.UrlParser_preliminary_signal.emit(
                (m_id, v_id, status, error_message, self.url)
            )
            return m_id, v_id, status
        elif match := re.search(r'models/(?P<model_id>\d{4,6})/?', self.url):
            m_id = match['model_id']
            self.signals.UrlParser_preliminary_signal.emit(
                (m_id, None, status, error_message, self.url)
            )
            return m_id, None, status
        else:
            # parse fails, set the status to false
            self.signals.UrlParser_preliminary_signal.emit(
                (None, None, False, error_message, self.url)
            )
            return None, None, False

    def get_model_version_info(self, model_id: str = '', model_version_id: str = '') -> None:
        """
        Get the information {version id: {version name, creator name, image url}} contained in the model.
        finally, emit (self.model_name, self.model_version_info) to UrlParser_Complete_Signal.
        :param model_id:
        :param model_version_id:
        :return:
        """
        try:
            response = self.httpx_client.get(self.civitai_models_api_url + model_id)
        except (httpx.TimeoutException, httpx.RequestError, httpx.ReadTimeout) as e:
            print(e)
            self.signals.UrlParser_Fail_Signal.emit(
                (f'{self.url} | Connection to the API failed. Try again later.', self.url)
            )
            return

        if response.status_code == httpx.codes.OK:
            models_json_data = response.json()
            self.model_name = models_json_data['name']
            creator_name = models_json_data['creator']['username']

            for version in models_json_data.get('modelVersions'):
                version_id = str(version['id'])
                version_name = version['name']
                # todo: The file download feature is not implemented 1
                # file_info_dict = self.get_version_file_info_dict(version)

                # for only downloading a specific version
                if model_version_id:
                    if version_id != model_version_id:
                        continue
                    self.construct_model_version_info_dict(version_id, version_name, creator_name, file_info_dict=None)
                    break

                self.construct_model_version_info_dict(version_id, version_name, creator_name, file_info_dict=None)

        self.signals.UrlParser_Complete_Signal.emit(
            (self.model_name, self.model_version_info, self.url)
        )
        """
        about self.model_version_info
        {'version_id': {'name': 'version_name',
                        'creator': 'creator_name',
                        'image_url': ['url1',
                                      'url2',
                                      ...
                                     ],
                        todo: The file download feature is not implemented 4 
                        'file': {'file_id': {'name': 'file_name',
                                             'info': 'like (fp16-full-PickleTensor)',
                                             'url': 'file_download_url',
                                             'size': file_size(float),
                                             'is_default': True|False(bool),
                                             },
                                  ...
                                 }
                        },
         ...
        }
        """

    # todo: The file download feature is not implemented 2
    def get_version_file_info_dict(self, version_info_data: dict) -> dict:
        """
        :param version_info_data:
        :return:
        """
        file_info_dict = {}
        for file in version_info_data['files']:
            file_id = str(file['id'])
            file_data = {
                'name': file['name'],
                'info': '-'.join(str(file['metadata'].values())),
                'url': file['downloadUrl'],
                'size': file['sizeKB'],
                'is_default': file.get('primary', False),
            }
            file_info_dict[file_id] = file_data

        return file_info_dict

    def construct_model_version_info_dict(self, version_id, version_name, creator_name, file_info_dict) -> None:
        """
        Construct self.model_version_info
        :param version_id:
        :param version_name:
        :param creator_name:
        :param file_info_dict: ****The file download feature is not implemented****
        :return:
        """
        # self.model_version_info[version_id] = {
        #     'name': version_name,
        #     'creator': creator_name,
        #     'image_url': [],
        #     # 'file': file_info_dict,  todo: The file download feature is not implemented 3
        # }
        self.model_version_info[version_id] = VersionInfoData(name=version_name, creator=creator_name)
        self.get_image_url(version_id, creator_name)

    def get_image_url(self, version_id: str, username: str) -> None:
        """
        Get the URL of the example image provided by the creator and write it to
        self.model_version_info[version_id]['image_url']
        :return:
        """
        params = {
            'modelVersionId': version_id,
            'username': username,
        }
        try:
            response = self.httpx_client.get(self.civitai_images_api_url, params=params)
        except (httpx.TimeoutException, httpx.RequestError, httpx.ReadTimeout) as e:
            print(e)
            self.signals.UrlParser_Fail_Signal.emit(
                (f'{self.url} | Failed to retrieve image links. Try again later.', self.url)
            )
            return

        if response.status_code == 200:
            image_json_data = response.json()
            for image_info in image_json_data.get('items'):
                url = image_info.get('url')
                self.model_version_info[version_id].image_urls.append(url)


class CivitaImageDownloadRunnerSignals(QObject):
    """
    Signals for CivitaImageDownloadRunner class
    """
    Image_download_started_signal = Signal(str)
    Image_download_fail_signal = Signal(tuple)
    Image_download_completed_signal = Signal(tuple)


class CivitaImageDownloadRunner(QRunnable):
    """
    Download images with support for QThreadPool
    """
    def __init__(self, version_id: str, version_name: str, image_url: str, save_path: Path, client: httpx.Client):
        super().__init__()
        self.version_id = version_id
        self.version_name = version_name
        self.url = image_url
        self.save_path = save_path
        self.httpx_client = client
        self.signals = CivitaImageDownloadRunnerSignals()

    @Slot()
    def run(self) -> None:
        self.signals.Image_download_started_signal.emit(f'Start to: {self.url}')

        try:
            response = self.httpx_client.get(self.url, follow_redirects=True)
            response.raise_for_status()

            if response.status_code == httpx.codes.OK:
                with open(f'{self.save_path}', 'wb') as f:
                    for data in response.iter_bytes():
                        f.write(data)
                self.signals.Image_download_completed_signal.emit((self.version_id, f'Finished: {self.url}'))
            elif response.status_code == httpx.codes.FOUND:
                print('\033[33m' + f'do 304 for {self.url}' + '\033[0m')
                self.url = response.headers.get('Location')
                return self.run()
            else:
                raise ValueError(f"Unexpected status code {response.status_code}")

        except httpx.HTTPStatusError as e:
            print('\033[33m' + f'HTTPStatusError: {self.url}. Reason: {str(e)}' + '\033[0m')
            self.signals.Image_download_fail_signal.emit((self.version_id, f'Failed_HTTPStatusError:: {self.url}'))
        except httpx.ReadTimeout as e:
            print('\033[33m' + f'ReadTimeout: {self.url}. Reason: {str(e)}' + '\033[0m')
            self.signals.Image_download_fail_signal.emit((self.version_id, f'Failed_ReadTimeout:: {self.url}'))
        except Exception as e:
            print('\033[33m' + f'Exception: {self.url}. Reason: {str(e)}' + '\033[0m')
            self.signals.Image_download_fail_signal.emit((self.version_id, f'Failed_Exception:: {self.url}'))
