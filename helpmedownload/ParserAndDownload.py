import re
from pathlib import Path
from dataclasses import dataclass, field

import httpx
from PySide6.QtCore import QObject, Signal, QRunnable, Slot


@dataclass(slots=True)
class UrlParseResultData:
    model_id: str = ''
    version_id: str = ''
    is_valid: bool | None = None


@dataclass(slots=True)
class FileInfoData:
    name: str
    info: str
    url: str
    size: int
    is_default: bool


@dataclass(slots=True)
class VersionInfoData:
    name: str
    creator: str
    model_id: str
    model_name: str
    image_urls: list = field(default_factory=list)
    file_info: dict[str, FileInfoData] = field(default_factory=dict)


class CivitaiUrlParserRunnerSignals(QObject):
    """
    Signals for CivitaiUrlParserRunner class
    """
    UrlParser_Start_Signal = Signal(str)
    UrlParser_Preliminary_Signal = Signal(tuple)
    UrlParser_Complete_Signal = Signal(tuple)


class CivitaiUrlParserRunner(QRunnable):
    """
    Parse the URL to obtain the model name and its related information. (self.model_name, self.model_version_info)
    """
    Civitai_Models_API: str = r'https://civitai.com/api/v1/models/'
    Civitai_Images_API: str = r'https://civitai.com/api/v1/images'
    
    def __init__(self, url: str, httpx_client: httpx.Client) -> None:
        super().__init__()

        self.url: str = url
        self.httpx_client: httpx.Client = httpx_client

        self.model_version_info: dict[str, VersionInfoData] = {}
        self.signals = CivitaiUrlParserRunnerSignals()

    @Slot()
    def run(self) -> None:
        self.signals.UrlParser_Start_Signal.emit(f'{self.url} | Start to parse ...')
        parse_result = self.get_model_and_version_id()
        # parse failed, connection failed, none of them continue
        if parse_result.is_valid:
            self.get_version_info(parse_result)

    def get_model_and_version_id(self) -> UrlParseResultData:
        """
        Get the analysis result and connection status of the URL, and emit the information (error_message, url)
        to main thread if an exception occurs.
        :return: UrlParseResultData
        """
        try:
            if self.httpx_client.get(self.url).status_code == httpx.codes.OK:
                if match := re.search(r'models/(?P<model_id>\d{4,6})[?]modelVersionId=(?P<version_id>\d{4,6})',
                                      self.url):
                    model_id, version_id = match['model_id'], match['version_id']
                    return UrlParseResultData(model_id=model_id, version_id=version_id, is_valid=True)
                elif match := re.search(r'models/(?P<model_id>\d{4,6})/?', self.url):
                    model_id = match['model_id']
                    return UrlParseResultData(model_id=model_id, is_valid=True)
                else:
                    # Parsing failed, as the link is not a valid civitai.com link
                    error_message = 'Parse failed.(not a valid civitai.com link)'
                    self.signals.UrlParser_Preliminary_Signal.emit((error_message, self.url))
                    return UrlParseResultData(is_valid=False)
        except (httpx.TimeoutException, httpx.RequestError, httpx.ReadTimeout) as e:
            error_message = str(e)
            self.signals.UrlParser_Preliminary_Signal.emit((error_message, self.url))
            return UrlParseResultData(is_valid=False)

    def get_version_info(self, parse_result: UrlParseResultData) -> None:
        """
        Get the information {version id: {version name, creator name, image url}} contained in the model.
        finally, emit (self.model_name, self.model_version_info) to UrlParser_Complete_Signal.
        :param parse_result:
        :return:
        """
        model_id = parse_result.model_id
        specific_version_id = parse_result.version_id
        try:
            response = self.httpx_client.get(self.Civitai_Models_API + model_id)
            assert (response.status_code == httpx.codes.OK), 'Response code is not OK when trying to get version info'
        except (httpx.TimeoutException, httpx.RequestError, httpx.ReadTimeout, AssertionError) as e:
            error_message = str(e)
            self.signals.UrlParser_Preliminary_Signal.emit((error_message, self.url))
            return

        model_data = response.json()
        model_name = model_data['name']
        creator_name = model_data['creator']['username']

        for version_data in model_data.get('modelVersions'):
            version_id = str(version_data['id'])

            # for only downloading a specific version
            if specific_version_id:
                if version_id != specific_version_id:
                    continue
                self.construct_version_info_data(version_id, version_data, model_id, model_name, creator_name)
                break

            self.construct_version_info_data(version_id, version_data, model_id, model_name, creator_name)

        self.signals.UrlParser_Complete_Signal.emit(
            (model_name, self.model_version_info, self.url)
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
    def construct_version_info_data(self, version_id, version_data, model_id, model_name, creator_name) -> None:
        """
        Construct self.model_version_info
        :param version_id:
        :param version_data:
        :param model_id:
        :param model_name:
        :param creator_name:
        :return:
        """
        version_name = version_data['name']
        image_urls = self.get_image_url(version_id, creator_name)
        file_info = self.get_version_file_info(version_data)
        self.model_version_info[version_id] = VersionInfoData(name=version_name,
                                                              creator=creator_name,
                                                              model_id=model_id,
                                                              model_name=model_name,
                                                              image_urls=image_urls,
                                                              file_info=file_info)

    def get_version_file_info(self, version_data: dict) -> dict:
        """
        :param version_data:
        :return:
        """
        file_info: dict[str, FileInfoData] = {}

        for file in version_data['files']:
            file_id = str(file['id'])
            file_info[file_id] = FileInfoData(
                name=file['name'],
                info='-'.join(str(file['metadata'].values())),
                url=file['downloadUrl'],
                size=file['sizeKB'],
                is_default=file.get('primary', False)
            )

        return file_info

    def get_image_url(self, version_id: str, username: str) -> list:
        """
        Get the URL of the example image provided by the creator and write it to
        self.model_version_info[version_id]['image_url']
        :return:
        """
        image_urls: list = []
        params = {
            'modelVersionId': version_id,
            'username': username,
        }

        try:
            response = self.httpx_client.get(self.Civitai_Images_API, params=params)
            assert (response.status_code == httpx.codes.OK), 'Response code is not OK when trying to get image url info'
        except (httpx.TimeoutException, httpx.RequestError, httpx.ReadTimeout, AssertionError) as e:
            error_message = str(e)
            self.signals.UrlParser_Preliminary_Signal.emit((error_message, self.url))
            return image_urls

        image_data = response.json()
        for image_info in image_data.get('items'):
            url = image_info.get('url')
            image_urls.append(url)

        return image_urls


class CivitaiImageDownloadRunnerSignals(QObject):
    """
    Signals for CivitaiImageDownloadRunner class
    """
    Image_download_started_signal = Signal(str)
    Image_download_fail_signal = Signal(tuple)
    Image_download_completed_signal = Signal(tuple)


class CivitaiImageDownloadRunner(QRunnable):
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
        self.signals = CivitaiImageDownloadRunnerSignals()

    @Slot()
    def run(self) -> None:
        self.signals.Image_download_started_signal.emit(f'Start to: {self.url}')

        try:
            response = self.httpx_client.get(self.url, follow_redirects=True)

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
